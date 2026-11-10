"""Find Gemini models your key can REALLY use. Listing is not enough: some listed models are
closed to new users and return 404. This sends one tiny request to each candidate.

    python scripts/list_models.py
Needs GEMINI_API_KEY in .env. Get a key at https://aistudio.google.com/apikey
Then set GEMINI_FLASH_MODEL / GEMINI_PRO_MODEL in .env to a model marked OK.
"""
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline import llm  # noqa: F401  (loads .env)

from google import genai

SKIP = ("image", "omni", "tts", "live", "embedding", "audio", "preview-")
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
names = sorted(m.name.replace("models/", "") for m in client.models.list())
names = [n for n in names if "gemini" in n and ("flash" in n or "pro" in n) and not any(s in n for s in SKIP)]
for n in names:
    try:
        r = client.models.generate_content(model=n, contents="Reply with the single word OK.")
        print(f"OK     {n:28s} -> {(r.text or '').strip()[:20]!r}")
    except Exception as e:
        msg = str(e).replace("\n", " ")
        reason = "closed to new users" if "no longer available" in msg else msg[:70]
        print(f"FAIL   {n:28s} {reason}")
    time.sleep(2)
