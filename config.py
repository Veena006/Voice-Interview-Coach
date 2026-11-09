"""Settings, language table and interview options. No API calls happen here."""
import os

from dotenv import load_dotenv

load_dotenv()

# ---- Keys and settings come from your .env file (never hardcode them) ----
GNANI_API_KEY = os.getenv("GNANI_API_KEY", "")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "")
LLM_MODEL = os.getenv("LLM_MODEL", "")


# Optional: "low" makes reasoning models such as gpt-oss answer much faster.
# Leave it empty in .env if your LLM does not support it.
LLM_REASONING_EFFORT = os.getenv("LLM_REASONING_EFFORT", "").strip()

VOICES = {
    "English": os.getenv("VOICE_ENGLISH", "Shivani"),
    "Hinglish": os.getenv("VOICE_HINGLISH", "Shivani"),
    "Kannada": os.getenv("VOICE_KANNADA", "Shivani"),
}

# Local file that stores accounts and saved interviews (keep it out of GitHub)
DB_PATH = os.getenv("APP_DB_PATH", "users.db")

# ---- Gnani endpoints ----
STT_URL = "https://api.vachana.ai/stt/v3"
TTS_URL = "https://api.vachana.ai/api/v1/tts/inference"
STT_MODEL = "prisma-v3.0"
TTS_MODEL = "timbre-v3.0"

# ---- Languages: speech-to-text code, text-to-speech code, LLM language rule ----
LANGS = {
    "English": {
        "stt": "en-IN",
        "tts": "en-IN",
        "llm": "Reply only in simple, clear English.",
    },
    "Hinglish": {
        "stt": "en-IN,hi-IN",  # comma-separated = mixed Hindi-English audio
        "tts": "hi-IN",
        "llm": "Reply in natural Hinglish (Hindi and English mixed, written in "
               "Devanagari for Hindi words and Latin for English words).",
    },
    "Kannada": {
        "stt": "kn-IN",
        "tts": "kn-IN",
        "llm": "Reply only in Kannada, written in Kannada script.",
    },
}

# ---- Interview options (Phase 1) ----
CATEGORIES = [
    "Technical Interview",
    "HR Interview",
    "Behavioural Interview",
    "Coding Interview",
    "General Interview",
]
DIFFICULTIES = ["Beginner", "Intermediate", "Advanced"]
MIN_QUESTIONS, MAX_QUESTIONS, DEFAULT_QUESTIONS = 3, 10, 5
MAX_AUDIO_SECONDS = 55  # Gnani file upload limit is 60 s
MIN_SPEED, MAX_SPEED, DEFAULT_SPEED = 0.9, 1.2, 1.0  # voice speed slider


def missing_settings():
    """Names of settings that are still placeholders (checked only when needed)."""
    needed = {
        "GNANI_API_KEY": GNANI_API_KEY,
        "LLM_API_KEY": LLM_API_KEY,
        "LLM_BASE_URL": LLM_BASE_URL,
        "LLM_MODEL": LLM_MODEL,
    }
    return [name for name, val in needed.items()
            if not val or val.strip().upper().startswith("PASTE")]