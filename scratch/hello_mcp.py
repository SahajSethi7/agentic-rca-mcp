"""Day 3: hello-world FastMCP server.

Run from the repo root:
    python scratch/hello_mcp.py
"""

from __future__ import annotations

from fastmcp import FastMCP


mcp = FastMCP("agentic-rca-hello")


@mcp.tool
def echo(text: str) -> str:
    """Return the same text back to the caller."""
    return text


if __name__ == "__main__":
    mcp.run()
