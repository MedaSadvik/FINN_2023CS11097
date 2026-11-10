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


TRANSIENT = ("429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE", "504", "DEADLINE_EXCEEDED")
GONE = ("no longer available", "NOT_FOUND")  # this model will never answer: skip it, do not retry
LAST_MODEL = None  # which model produced the most recent answer (for audit columns)


def fallback_models() -> list:
    raw = os.getenv("GEMINI_FALLBACK_MODELS", "gemini-3.7-flash,gemini-3.6-flash,gemini-3.5-flash")
    return [m.strip() for m in raw.split(",") if m.strip()]


def generate_json(model: str, system: str, prompt: str, version: str = "v1",
                  call=_gemini_call, retries: int = 2):
    """Return parsed JSON from the model. Cached on disk.

    If `model` is overloaded (503/504), rate-limited (429) or closed (404), retry briefly, then
    fall through GEMINI_FALLBACK_MODELS. Real bugs (bad key, bad request) are raised at once.
    The cache is keyed by the REQUESTED model, so a later run is instant whichever model answered.
    """
    global LAST_MODEL
    key = cache_key(model, system, prompt, version)
    path = CACHE / f"{key}.json"
    if path.exists():
        cached = json.loads(path.read_text())
        LAST_MODEL = cached["model"]
        return cached["data"]
    t0, last_err = time.time(), None
    for m in [model] + [f for f in fallback_models() if f != model]:
        print(f"[llm] {m}: sending {len(prompt):,} characters (waits up to 3 min)...", file=sys.stderr, flush=True)
        for attempt in range(retries + 1):
            try:
                data = extract_json(call(m, system, prompt))
            except Exception as e:
                msg = str(e)
                last_err = e
                if any(g in msg for g in GONE):
                    print(f"[llm] {m} is closed to this key; trying next model", file=sys.stderr, flush=True)
                    break
                if not any(t in msg for t in TRANSIENT):
                    raise
                if attempt == retries:
                    print(f"[llm] {m} still failing ({msg[:50]}...); trying next model", file=sys.stderr, flush=True)
                    break
                wait = 10 * 2 ** attempt  # 10s, 20s
                print(f"[llm] {m} busy ({msg[:50]}...). Retry {attempt + 1}/{retries} in {wait}s",
                      file=sys.stderr, flush=True)
                time.sleep(wait)
            else:
                LAST_MODEL = m
                print(f"[llm] {m} answered in {time.time() - t0:.0f}s", file=sys.stderr, flush=True)
                CACHE.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps({"model": m, "data": data}))
                return data
    raise RuntimeError(f"all models failed; last error: {last_err}") from last_err


if __name__ == "__main__":  # smoke test: python -m pipeline.llm
    for m in [flash_model()] + [f for f in fallback_models() if f != flash_model()]:
        t0 = time.time()
        try:
            out = _gemini_call(m, "Answer in JSON.", 'Return {"ok": true}')
            print(f"OK    {m:22s} {time.time() - t0:5.1f}s  {out.strip()[:30]!r}")
        except Exception as e:
            print(f"FAIL  {m:22s} {time.time() - t0:5.1f}s  {str(e)[:90]!r}")
