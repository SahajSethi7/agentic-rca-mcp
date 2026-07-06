r"""Fast probe: which switch actually disables qwen3 'thinking' on Ollama /v1.

Run WITHOUT rebuilding, piping into the running container:

    Get-Content tools\probe_think.py | docker compose exec -T app python -

Each variant asks for a tiny JSON object with a small token budget, so it
returns in seconds once the model is warm. We want the variant whose content
is clean JSON with contains<think>=False.
"""
import time

from openai import OpenAI

from config import get_settings

s = get_settings()
c = OpenAI(base_url=s.ollama_base_url, api_key="ollama", timeout=s.request_timeout_seconds)
BASE = ("Return ONLY a JSON object with keys root_cause (a string of at least "
        "20 chars) and confidence (one of low, medium, high).")


def call(tag, prompt_suffix="", extra_body=None):
    print(f"\n===== {tag} =====", flush=True)
    t = time.time()
    try:
        r = c.chat.completions.create(
            model=s.rca_model,
            messages=[{"role": "user", "content": BASE + prompt_suffix}],
            max_tokens=300,
            temperature=0,
            extra_body=extra_body or {},
        )
        m = r.choices[0].message
        content = m.content or ""
        print("elapsed_s       :", round(time.time() - t, 1), flush=True)
        print("finish_reason   :", r.choices[0].finish_reason, flush=True)
        print("content length  :", len(content), flush=True)
        print("contains <think>:", "<think>" in content.lower(), flush=True)
        print("reasoning field :", bool(getattr(m, "reasoning", None)), flush=True)
        print("content[:400]   :", repr(content[:400]), flush=True)
    except Exception as e:  # noqa: BLE001
        print("elapsed_s :", round(time.time() - t, 1), flush=True)
        print("ERROR     :", type(e).__name__, str(e)[:300], flush=True)


call("A default (think:false via extra_body)", extra_body={"think": False})
call("B /no_think soft switch in prompt", prompt_suffix=" /no_think")
call("C chat_template_kwargs enable_thinking:false",
     extra_body={"chat_template_kwargs": {"enable_thinking": False}})
