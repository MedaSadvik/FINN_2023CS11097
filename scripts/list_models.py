"""List Gemini models your API key can use, so you can set GEMINI_FLASH_MODEL / GEMINI_PRO_MODEL.

    python scripts/list_models.py
Needs GEMINI_API_KEY in .env (copy .env.example). Get a key at https://aistudio.google.com/apikey
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline import llm  # noqa: F401  (loads .env)

from google import genai

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
for m in client.models.list():
    name = m.name.replace("models/", "")
    if "gemini" in name and ("flash" in name or "pro" in name):
        print(name)
