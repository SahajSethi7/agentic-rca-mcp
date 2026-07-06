"""One-shot diagnostic for structured RCA generation.

Runs the real provider path against the configured model and prints exactly
why structured output does or does not validate. Use when every RCA falls back
to the conservative draft.

    docker compose run --rm app python tools/diagnose_generation.py
    # or, against a running stack:
    docker compose exec app python tools/diagnose_generation.py
"""

from __future__ import annotations

import json
import os
import sys

# Allow running as a plain script (docker compose exec ... python tools/diagnose_generation.py):
# ensure the repo root (/app) is importable, not just the tools/ directory.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import get_settings
from prompts import build_messages
from schemas import RCAGenerationReport, RCAInput

PROBLEM = (
    "During our flash sale, checkout kept accepting orders for the smartwatch "
    "bundle for 25 minutes after warehouse stock ran out. We oversold by 600 "
    "orders and sent cancellations to customers."
)
CONTEXT = (
    "The checkout availability service reads stock from a Postgres read replica. "
    "Write load on the primary was 15x normal and replica lag peaked at 3-4 "
    "minutes. Six weeks ago availability reads moved from the primary to the "
    "replicas. We do not alert on replication lag; the pre-sale load test was "
    "read-only."
)


def _hr(title: str) -> None:
    print("\n" + "=" * 8 + f" {title} " + "=" * 8)


def main() -> None:
    settings = get_settings()
    _hr("EFFECTIVE SETTINGS (what is actually running)")
    print("provider          :", settings.provider)
    print("rca_model         :", settings.rca_model)
    print("ollama_base_url   :", settings.ollama_base_url)
    print("max_output_tokens :", settings.max_output_tokens, "   <-- want >= 4096")
    print("max_retries       :", settings.max_retries)
    print("prompt_version    :", settings.prompt_version)
    print("RCAGenerationReport extra policy:", RCAGenerationReport.model_config.get("extra"),
          "   <-- want 'ignore'")

    rca_input = RCAInput(problem_statement=PROBLEM, context=CONTEXT, method="five_why")
    messages = build_messages(rca_input, prompt_version=settings.prompt_version)

    from openai import OpenAI

    client = OpenAI(base_url=settings.ollama_base_url, api_key="ollama",
                    timeout=settings.request_timeout_seconds)

    # --- 1. RAW completion: what does the model literally return? ---------
    _hr("RAW MODEL OUTPUT (response_format=json_object)")
    raw = ""
    try:
        resp = client.chat.completions.create(
            model=settings.rca_model,
            messages=messages,
            response_format={"type": "json_object"},
            max_tokens=settings.max_output_tokens,
            temperature=0,
            extra_body={"think": False},
        )
        raw = resp.choices[0].message.content or ""
        finish = resp.choices[0].finish_reason
        print("finish_reason     :", finish, "   <-- 'length' means TRUNCATED (raise max tokens)")
        print("content length    :", len(raw), "chars")
        print("contains <think>  :", "<think>" in raw.lower())
        print("starts with '{'   :", raw.lstrip()[:1] == "{")
        try:
            json.loads(raw)
            print("json.loads        : OK (valid JSON object)")
        except Exception as je:
            print("json.loads        : FAILED ->", type(je).__name__, str(je)[:120])
        print("\n--- first 600 chars ---\n" + raw[:600])
        print("\n--- last 300 chars ---\n" + raw[-300:])
    except Exception as exc:  # noqa: BLE001
        print("RAW call raised   :", type(exc).__name__, "->", str(exc)[:300])
        print("If this is NotFound/404, the model tag is not pulled in Ollama.")

    # --- 2. STRUCTURED path: reproduce the real Instructor failure --------
    _hr("STRUCTURED (Instructor) PATH")
    import instructor

    iclient = instructor.from_openai(client, mode=instructor.Mode.JSON)
    try:
        draft = iclient.chat.completions.create(
            model=settings.rca_model,
            response_model=RCAGenerationReport,
            max_retries=settings.max_retries,
            max_tokens=settings.max_output_tokens,
            temperature=0,
            extra_body={"think": False},
            messages=messages,
        )
        print("RESULT            : SUCCESS - structured output validated")
        print("root_cause        :", draft.root_cause[:160])
    except Exception as exc:  # noqa: BLE001
        print("RESULT            : FAILED")
        print("exception type    :", type(exc).__name__)
        print("exception message :", str(exc)[:500])
        print("\nInterpretation:")
        name = type(exc).__name__
        if "Incomplete" in name or "length" in str(exc).lower():
            print("  -> TRUNCATION. Raise RCA_MAX_OUTPUT_TOKENS.")
        elif "Retry" in name or "Validation" in name:
            print("  -> Output did not match schema after retries "
                  "(stray keys / missing fields / reasoning pollution).")
        else:
            print("  -> Connectivity / model / mode issue - see message above.")


if __name__ == "__main__":
    main()
