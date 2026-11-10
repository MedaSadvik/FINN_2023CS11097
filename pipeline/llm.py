"""One small door to the LLM. Everything that calls a model goes through generate_json().

Why a wrapper: (1) every answer is cached on disk by hash(model + prompts + version),
so a re-run costs nothing; (2) free-tier rate limits get retried with backoff;
(3) tests can pass a fake `call` and never touch the network.

Models are read from the environment because Google renames them often:
    GEMINI_FLASH_MODEL   cheap, bulk extraction        (default gemini-3.8-flash)
    GEMINI_PRO_MODEL     reasoning, run offline only   (default gemini-3.8-flash)
Being LISTED is not the same as being USABLE: gemini-2.5-flash is listed but closed to new
users (404). Run `python scripts/list_models.py` to test which models really answer.
No Pro-tier model is usable on the free key yet, so "pro" falls back to the newest flash.
"""
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "cache" / "llm"


def load_env(path=ROOT / ".env"):
    """Tiny .env reader (KEY=value per line) so beginners need no extra package."""
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.split("#", 1)[0].strip()
            if "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


load_env()


def flash_model() -> str:
    return os.getenv("GEMINI_FLASH_MODEL", "gemini-3.8-flash")


def pro_model() -> str:
    return os.getenv("GEMINI_PRO_MODEL", "gemini-3.8-flash")


def cache_key(model: str, system: str, prompt: str, version: str) -> str:
    return hashlib.sha256("\x1f".join([model, system, prompt, version]).encode()).hexdigest()


def extract_json(text: str):
    """Parse model output as JSON, tolerating ```json fences and chatter around it."""
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        starts = [i for i in (t.find("{"), t.find("[")) if i != -1]
        if not starts:
            raise
        start = min(starts)
        end = max(t.rfind("}"), t.rfind("]"))
        return json.loads(t[start:end + 1])


def _gemini_call(model: str, system: str, prompt: str) -> str:
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"],
                          http_options=types.HttpOptions(timeout=180_000))  # ms; never hang silently
    resp = client.models.generate_content(
        model=model, contents=prompt,
        config=types.GenerateContentConfig(system_instruction=system, temperature=0,
                                           response_mime_type="application/json"))
    return resp.text


def generate_json(model: str, system: str, prompt: str, version: str = "v1",
                  call=_gemini_call, retries: int = 4):
    """Return parsed JSON from the model. Cached on disk; retried on rate limits."""
    key = cache_key(model, system, prompt, version)
    path = CACHE / f"{key}.json"
    if path.exists():
        return json.loads(path.read_text())
    t0 = time.time()
    print(f"[llm] {model}: sending {len(prompt):,} characters (waits up to 3 min)...", file=sys.stderr, flush=True)
    for attempt in range(retries + 1):
        try:
            data = extract_json(call(model, system, prompt))
            break
        except Exception as e:
            transient = any(s in str(e) for s in ("429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE"))
            if attempt == retries or not transient:
                raise
            wait = 10 * 2 ** attempt  # free tier: back off 10s, 20s, 40s, 80s
            print(f"[llm] busy or rate-limited ({str(e)[:60]}...). Retry {attempt + 1}/{retries} in {wait}s",
                  file=sys.stderr, flush=True)
            time.sleep(wait)
    print(f"[llm] done in {time.time() - t0:.0f}s", file=sys.stderr, flush=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))
    return data


if __name__ == "__main__":  # smoke test: python -m pipeline.llm
    t0 = time.time()
    print(_gemini_call(flash_model(), "Answer in JSON.", 'Return {"ok": true}'))
    print(f"model {flash_model()} answered in {time.time() - t0:.1f}s")
