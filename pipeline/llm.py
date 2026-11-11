"""One small door to the LLM. Everything that calls a model goes through generate_json().

Why a wrapper: (1) every answer is cached on disk by hash(model + prompts + version),
so a re-run costs nothing; (2) free-tier rate limits get retried with backoff;
(3) tests can pass a fake `call` and never touch the network.

Models are read from the environment because Google renames them often:
    GEMINI_FLASH_MODEL   cheap, bulk extraction        (default gemini-3.5-flash)
    GEMINI_PRO_MODEL     reasoning, run offline only   (default gemini-3.5-flash)
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


def derived(name: str) -> str:
    """Folder name for MODEL-MADE output. Dev-provider runs write to '<name>_dev' so they can never
    overwrite or mix with the Gemini data we ship. Raw downloads (pdf, text, docs) are shared."""
    return name if os.getenv("LLM_PROVIDER", "gemini").lower() == "gemini" else f"{name}_dev"


CACHE = ROOT / "data" / "cache" / derived("llm")


def load_env(path=ROOT / ".env"):
    """Tiny .env reader (KEY=value per line) so beginners need no extra package."""
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.split("#", 1)[0].strip()
            if "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


load_env()


def provider() -> str:
    """'gemini' (default, used for everything we ship) or 'openai_compat' (dev testing only, e.g. Hyde's
    GLM/Kimi models). Set LLM_PROVIDER=openai_compat plus OPENAI_BASE_URL, OPENAI_API_KEY, OPENAI_MODEL."""
    return os.getenv("LLM_PROVIDER", "gemini").lower()


def flash_model() -> str:
    if provider() != "gemini":
        return os.environ["OPENAI_MODEL"]
    return os.getenv("GEMINI_FLASH_MODEL", "gemini-3.5-flash")


def pro_model() -> str:
    if provider() != "gemini":
        return os.environ["OPENAI_MODEL"]
    return os.getenv("GEMINI_PRO_MODEL", "gemini-3.5-flash")


def cache_key(model: str, system: str, prompt: str, version: str) -> str:
    return hashlib.sha256("\x1f".join([model, system, prompt, version]).encode()).hexdigest()


def extract_json(text: str):
    """Parse model output as JSON, tolerating ```json fences and chatter around it."""
    t = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()  # reasoning models show their thinking
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
                          http_options=types.HttpOptions(timeout=90_000))  # ms; a healthy model answers well inside this
    resp = client.models.generate_content(
        model=model, contents=prompt,
        config=types.GenerateContentConfig(system_instruction=system, temperature=0,
                                           response_mime_type="application/json"))
    return resp.text


def _openai_compat_call(model: str, system: str, prompt: str) -> str:
    """Any server that speaks the OpenAI chat-completions format (most hosted GLM/Kimi/Qwen do)."""
    import requests
    base = os.environ["OPENAI_BASE_URL"].rstrip("/")
    r = requests.post(f"{base}/chat/completions", timeout=180,
                      headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
                      json={"model": model, "temperature": 0,
                            "messages": [{"role": "system", "content": system},
                                         {"role": "user", "content": prompt}]})
    if r.status_code != 200:
        raise RuntimeError(f"{r.status_code} {r.text[:400]}")
    choice = r.json()["choices"][0]
    text = (choice.get("message") or {}).get("content")
    if not text or not text.strip():  # reasoning models can spend the whole budget thinking and return null
        raise RuntimeError(f"503 empty reply from model (finish_reason={choice.get('finish_reason')})")
    return text


def _default_call(model: str, system: str, prompt: str) -> str:
    return (_gemini_call if provider() == "gemini" else _openai_compat_call)(model, system, prompt)


class QuotaExhausted(RuntimeError):
    """The free daily request quota is used up. Waiting a few seconds will not help."""


USAGE = ROOT / "data" / "cache" / "llm_usage.json"
DAILY_LIMIT = int(os.getenv("GEMINI_DAILY_LIMIT", "20"))  # free tier at the time of writing; for the message only


def count_call(model: str, path=None) -> int:
    """Tally successful Gemini requests per model per day (Google resets at midnight Pacific, UTC-8).
    Returns today's count for this model. Approximate: the server is the real counter."""
    if provider() != "gemini":
        return 0
    path = path or USAGE
    from datetime import datetime, timedelta, timezone
    day = (datetime.now(timezone.utc) - timedelta(hours=8)).date().isoformat()
    try:
        data = json.loads(path.read_text()) if path.exists() else {}
    except json.JSONDecodeError:
        data = {}
    data = {day: data.get(day, {})}  # keep today only
    data[day][model] = data[day].get(model, 0) + 1
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))
    return data[day][model]


TRANSIENT = ("429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE")  # busy: wait and retry the same model
HANG = ("504", "DEADLINE_EXCEEDED", "timed out", "Timeout")      # model not answering: retrying wastes minutes
GONE = ("no longer available", "NOT_FOUND")  # this model will never answer: skip it, do not retry
LAST_MODEL = None  # which model produced the most recent answer (for audit columns)


def fallback_models() -> list:
    if provider() != "gemini":
        return []  # one dev model, no silent switching
    raw = os.getenv("GEMINI_FALLBACK_MODELS", "gemini-3.6-flash,gemini-3.7-flash")
    return [m.strip() for m in raw.split(",") if m.strip()]


def generate_json(model: str, system: str, prompt: str, version: str = "v1",
                  call=None, retries: int = 2):
    """Return parsed JSON from the model. Cached on disk.

    If `model` is busy (503) or rate-limited (429), retry briefly. If it hangs (504/timeout) or is
    closed (404), go straight to the next model in GEMINI_FALLBACK_MODELS. Real bugs (bad key, bad request) are raised at once.
    The cache is keyed by the REQUESTED model, so a later run is instant whichever model answered.
    """
    global LAST_MODEL
    counting = call is None  # only real requests count against the quota, never test fakes
    call = call or _default_call
    key = cache_key(model, system, prompt, version)
    path = CACHE / f"{key}.json"
    if path.exists():
        cached = json.loads(path.read_text())
        LAST_MODEL = cached["model"]
        return cached["data"]
    t0, last_err, quota_hits, reset_in = time.time(), None, [], None
    for m in [model] + [f for f in fallback_models() if f != model]:
        print(f"[llm] {m}: sending {len(prompt):,} characters (waits up to 90s)...", file=sys.stderr, flush=True)
        for attempt in range(retries + 1):
            try:
                data = extract_json(call(m, system, prompt))
            except Exception as e:
                msg = str(e)
                last_err = e
                if any(g in msg for g in GONE):
                    print(f"[llm] {m} is closed to this key; trying next model", file=sys.stderr, flush=True)
                    break
                if any(h in msg for h in HANG):
                    print(f"[llm] {m} timed out; trying next model", file=sys.stderr, flush=True)
                    break
                if not any(t in msg for t in TRANSIENT):
                    raise
                if attempt == retries:
                    print(f"[llm] {m} still failing ({msg[:50]}...); trying next model", file=sys.stderr, flush=True)
                    break
                if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                    if re.search(r"PerDay|per day", msg, re.I):  # daily quota gone: waiting is pointless
                        quota_hits.append(m)
                        after = re.search(r"retry in (\d+h)?(\d+m)?", msg)
                        reset_in = "".join(g for g in after.groups() if g) if after else reset_in
                        print(f"[llm] {m} daily quota used up; trying next model", file=sys.stderr, flush=True)
                        break
                    hint = re.search(r"retryDelay['\"]?:\s*['\"]?(\d+)", msg)  # Google says how long to wait
                    wait = min(int(hint.group(1)) + 2, 90) if hint else 30 * (attempt + 1)
                else:
                    wait = 10 * 2 ** attempt  # busy server: 10s, 20s
                print(f"[llm] {m} busy ({msg[:50]}...). Retry {attempt + 1}/{retries} in {wait}s",
                      file=sys.stderr, flush=True)
                time.sleep(wait)
            else:
                LAST_MODEL = m
                used = count_call(m) if counting else 0
                note = f" (about {used}/{DAILY_LIMIT} free requests used today)" if used else ""
                print(f"[llm] {m} answered in {time.time() - t0:.0f}s{note}", file=sys.stderr, flush=True)
                CACHE.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps({"model": m, "data": data}))
                return data
    if quota_hits:
        raise QuotaExhausted(f"daily free quota used up on {quota_hits}"
                             + (f"; resets in about {reset_in}" if reset_in else "")) from last_err
    raise RuntimeError(f"all models failed; last error: {last_err}") from last_err


if __name__ == "__main__":  # smoke test: python -m pipeline.llm
    models = [flash_model()] + [f for f in fallback_models() if f != flash_model()]
    print(f"provider={provider()}  models to test: {models}")  # so silence can never be ambiguous
    for m in models:
        t0 = time.time()
        try:
            out = _default_call(m, "Answer in JSON.", 'Return {"ok": true}')
            print(f"OK    {m:22s} {time.time() - t0:5.1f}s  {out.strip()[:30]!r}")
        except Exception as e:
            print(f"FAIL  {m:22s} {time.time() - t0:5.1f}s")
            print("      full error:", str(e)[:700])
