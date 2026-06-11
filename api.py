"""FastAPI scaffold for the RCA service."""

from __future__ import annotations

from fastapi import FastAPI

from agent.orchestrator import RCAAgent
from schemas import RCAInput, RCAReport


app = FastAPI(title="Agentic RCA MCP Server")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/rca", response_model=RCAReport)
def create_rca(payload: RCAInput) -> RCAReport:
    agent = RCAAgent()
    return agent.run(
        payload.problem_statement,
        context=payload.context,
        method=payload.method,
    )
