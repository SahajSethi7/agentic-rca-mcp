"""Phase 6 web-UI route + job coverage (provider stubbed, no network)."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import api
import web.jobs as jobs
import web.routes as routes
from config import Settings
from schemas import RCAReport

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
_FIXTURE = json.loads((EXAMPLES / "sample_rca_1.json").read_text())


class StubAgent:
    """Walks the agent stages via on_event and returns a fixture report."""

    def __init__(self, settings=None) -> None:
        self.last_run_stats = {"rounds": 1, "validation_model": None, "sanitizer_findings": []}

    def run(self, problem, context=None, method="five_why", severity=None,
            system_area=None, on_event=None):
        for stage in ("planning", "generating"):
            if on_event:
                on_event(stage, {})
        if on_event:
            on_event("critiquing", {"round": 1})
            on_event("revising", {"round": 1})
        payload = dict(_FIXTURE, method=method, problem=problem)
        if on_event:
            on_event("done", {})
        return RCAReport.model_validate(payload)


class FailAgent:
    def __init__(self, settings=None) -> None:
        self.last_run_stats = {}

    def run(self, problem, **kwargs):
        on_event = kwargs.get("on_event")
        if on_event:
            on_event("planning", {})
        raise ConnectionError("Ollama is not running")


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(
        jobs, "get_settings",
        lambda: Settings(output_dir=tmp_path, validation_enabled=False),
    )
    jobs.manager.set_agent_factory(lambda settings: StubAgent(settings))
    yield TestClient(api.app)
    jobs.manager.set_agent_factory(None)


def _drain(client: TestClient, job_id: str, timeout: float = 8.0) -> list[dict]:
    events: list[dict] = []
    cursor = 0
    deadline = time.time() + timeout
    while time.time() < deadline:
        data = client.get(f"/ui/status/{job_id}?cursor={cursor}").json()
        events += data["events"]
        cursor = data["cursor"]
        if data["done"]:
            break
        time.sleep(0.03)
    return events


def test_index_page_is_served(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert (
        ('id="root"' in resp.text and "/assets/" in resp.text)
        or "RCA Assistant Web UI" in resp.text
    )


def test_meta_lists_methods_and_stages(client, monkeypatch):
    monkeypatch.setattr(
        routes,
        "get_settings",
        lambda: Settings(
            rca_model="demo-writer:1b",
            validation_model="demo-validator:2b",
        ),
    )
    meta = client.get("/ui/meta").json()
    assert meta["methods"] == ["five_why", "fishbone", "fault_tree"]
    assert "critiquing" in meta["stages"]
    assert meta["models"] == {
        "writer": "demo-writer:1b",
        "validator": "demo-validator:2b",
    }
    assert meta["memory"]["enabled"] is True
    assert isinstance(meta["memory"]["record_count"], int)


def test_analyze_streams_stages_and_renders_report(client):
    resp = client.post("/ui/analyze", json={
        "problem_statement": "Checkout requests time out after a database migration",
        "method": "five_why",
    })
    job_id = resp.json()["job_id"]
    events = _drain(client, job_id)
    stages = [e["stage"] for e in events if e["type"] == "stage"]
    for expected in ("planning", "generating", "critiquing", "revising", "rendering"):
        assert expected in stages
    results = [e for e in events if e["type"] == "result"]
    assert len(results) == 1
    report = results[0]["report"]            # full RCAReport JSON for React
    assert report["root_cause"]
    assert len(report["why_chain"]) >= 3
    assert "html" not in results[0]
    assert "json_url" not in results[0]
    assert results[0]["memory_xlsx_url"].endswith("/matching-past-rcas.xlsx")
    saved_job = jobs.manager.get(job_id)
    assert saved_job is not None
    assert saved_job.runs[0].json_path is not None
    assert saved_job.runs[0].json_path.exists()
    # PDF download serves a real file as an attachment.
    pdf = client.get(results[0]["pdf_url"])
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert "attachment" in pdf.headers.get("content-disposition", "")
    assert len(pdf.content) > 800
    json_artifact = client.get(f"/ui/jobs/{job_id}/runs/0/report.json")
    assert json_artifact.status_code == 404
    xlsx = client.get(results[0]["memory_xlsx_url"])
    assert xlsx.status_code == 200
    assert "spreadsheetml.sheet" in xlsx.headers["content-type"]
    assert "attachment" in xlsx.headers.get("content-disposition", "")
    assert len(xlsx.content) > 2000


def test_compare_two_methods_runs_both(client):
    resp = client.post("/ui/analyze", json={
        "problem_statement": "Login API returns HTTP 500 after a deploy",
        "method": "five_why",
        "compare_method": "fishbone",
    })
    body = resp.json()
    assert [r["method"] for r in body["runs"]] == ["five_why", "fishbone"]
    events = _drain(client, body["job_id"])
    results = sorted(e["run"] for e in events if e["type"] == "result")
    assert results == [0, 1]


def test_failure_surfaces_clean_structured_error(client, monkeypatch):
    jobs.manager.set_agent_factory(lambda settings: FailAgent(settings))
    resp = client.post("/ui/analyze", json={
        "problem_statement": "Some incident statement long enough to pass",
        "method": "five_why",
    })
    events = _drain(client, resp.json()["job_id"])
    errors = [e for e in events if e["type"] == "error"]
    assert len(errors) == 1
    assert errors[0]["error"]["error_type"] == "provider_unreachable"
    assert "stack" not in json.dumps(errors[0]).lower()


def test_sse_stream_emits_events(client):
    job_id = client.post("/ui/analyze", json={
        "problem_statement": "Search latency tripled after a cache change",
        "method": "five_why",
    }).json()["job_id"]
    seen = 0
    with client.stream("GET", f"/ui/events/{job_id}") as stream:
        for line in stream.iter_lines():
            if line and line.startswith("data:"):
                seen += 1
            if seen >= 3:
                break
    assert seen >= 3


def test_unknown_job_returns_404(client):
    assert client.get("/ui/status/deadbeef").status_code == 404


def test_agent_construction_failure_does_not_hang_the_job(client):
    """If building the agent raises, the job must still finish with a clean
    error event instead of leaving the worker thread dead and the UI stuck."""
    def boom(settings):
        raise RuntimeError("factory blew up during construction")

    jobs.manager.set_agent_factory(boom)
    resp = client.post("/ui/analyze", json={
        "problem_statement": "An incident statement long enough to pass",
        "method": "five_why",
    })
    job_id = resp.json()["job_id"]
    events = _drain(client, job_id)
    assert any(e["type"] == "error" for e in events)
    assert any(e["type"] == "complete" for e in events)
    assert client.get(f"/ui/status/{job_id}").json()["done"] is True
