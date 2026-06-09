"""Day 2: minimal Ollama JSON smoke test.

Run from the repo root:
    python scratch/model_test.py
"""

from __future__ import annotations

import json
import os
from typing import Any
from urllib import request


MODEL = os.getenv("RCA_MODEL", "qwen2.5:7b")
OLLAMA_CHAT_URL = os.getenv(
    "OLLAMA_CHAT_URL",
    "http://localhost:11434/v1/chat/completions",
)


def strip_markdown_json(text: str) -> str:
    """Remove common ```json fences from open-model responses."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned


def post_chat_completion(prompt: str) -> dict[str, Any]:
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "stream": False,
        "temperature": 0,
    }
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        OLLAMA_CHAT_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with request.urlopen(req, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def extract_message_content(response: dict[str, Any]) -> str:
    return response["choices"][0]["message"]["content"]


def main() -> None:
    prompt = 'Return only this JSON object: {"ok": true, "source": "ollama"}'
    response = post_chat_completion(prompt)
    content = extract_message_content(response)
    json_text = strip_markdown_json(content)
    parsed = json.loads(json_text)

    print("Raw model content:")
    print(content)
    print("\nParsed JSON:")
    print(json.dumps(parsed, indent=2))


if __name__ == "__main__":
    main()
