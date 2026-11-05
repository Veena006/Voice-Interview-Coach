"""
Voice Interview Coach (English / Hinglish / Kannada)
Speech-to-text : Gnani Prisma
Text-to-speech : Gnani Timbre
LLM            : any OpenAI-compatible API (Evon if you get a hosted endpoint)

Run:  python app.py
"""
import hashlib
import os
import re
import tempfile

import gradio as gr
import requests
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# =====================================================================
# API CONFIGURATION (credentials loaded from .env)
# =====================================================================

GNANI_API_KEY = os.getenv("GNANI_API_KEY", "PASTE_YOUR_GNANI_API_KEY_HERE")

LLM_API_KEY = os.getenv("LLM_API_KEY", "PASTE_YOUR_LLM_API_KEY_HERE")

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "PASTE_LLM_BASE_URL_HERE")

LLM_MODEL = os.getenv("LLM_MODEL", "PASTE_LLM_MODEL_NAME_HERE")
# Pick voices from the Voice Catalog at docs.gnani.ai (Kannada and Hinglish
# need a voice that supports that language). Change these after testing.
VOICES = {
    "English": "Nalini",
    "Hinglish": "Nalini",
    "Kannada": "Nalini",
}
# =====================================================================

STT_URL = "https://api.vachana.ai/stt/v3"
TTS_URL = "https://api.vachana.ai/api/v1/tts/inference"
STT_MODEL = "prisma-v3.0"
TTS_MODEL = "timbre-v2.5"

# language code for speech-to-text, language code for text-to-speech,
# and how the LLM should talk
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

SYSTEM_PROMPT = """You are a friendly, professional interview coach helping a student \
practise for an interview for: {role}.
{lang_rule}
Rules:
- Ask ONE interview question at a time.
- After the student answers, give short feedback (1-2 sentences) on clarity, \
confidence and content, then ask the next question.
- Keep every reply under 3 short sentences, because it will be read aloud.
- No bullet points, no markdown, no emojis."""

HEADERS = {"X-API-Key-ID": GNANI_API_KEY}
_tts_cache = {}  # saves credits: same text is never synthesised twice


def _check_keys():
    missing = [
        name for name, val in [
            ("GNANI_API_KEY", GNANI_API_KEY),
            ("LLM_API_KEY", LLM_API_KEY),
            ("LLM_BASE_URL", LLM_BASE_URL),
            ("LLM_MODEL", LLM_MODEL),
        ] if val.startswith("PASTE_")
    ]
    if missing:
        raise gr.Error("Fill these in at the top of app.py: " + ", ".join(missing))


def _find_text(obj):
    """Find the transcript inside whatever JSON the API returns."""
    if isinstance(obj, dict):
        for key in ("transcript", "text", "transcription"):
            if isinstance(obj.get(key), str):
                return obj[key]
        for val in obj.values():
            found = _find_text(val)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for val in obj:
            found = _find_text(val)
            if found is not None:
                return found
    return None


def speech_to_text(audio_path, lang):
    """Gnani Prisma: audio file (max 60 s) -> text."""
    last_error = ""
    for field in ("audio_file", "file"):  # tries both in case the docs differ
        with open(audio_path, "rb") as f:
            r = requests.post(
                STT_URL,
                headers=HEADERS,
                files={field: f},
                data={"model": STT_MODEL, "language_code": LANGS[lang]["stt"]},
                timeout=90,
            )
        if r.ok:
            text = _find_text(r.json())
            if text is None:
                raise RuntimeError(f"Could not find transcript in response: {r.text[:300]}")
            return text.strip()
        last_error = f"{r.status_code}: {r.text[:300]}"
    raise RuntimeError(f"Speech-to-text failed ({last_error})")


def text_to_speech(text, lang):
    """Gnani Timbre: text -> wav file path. Cached to save credits."""
    key = hashlib.md5(f"{lang}|{VOICES[lang]}|{text}".encode()).hexdigest()
    if key in _tts_cache and os.path.exists(_tts_cache[key]):
        return _tts_cache[key]

    r = requests.post(
        TTS_URL,
        headers={**HEADERS, "Content-Type": "application/json"},
        json={
            "text": text,
            "voice": VOICES[lang],
            "model": TTS_MODEL,
            "language": LANGS[lang]["tts"],
            "speed": 1.0,
            "audio_config": {
                "sample_rate": 24000,
                "num_channels": 1,
                "sample_width": 2,
                "encoding": "linear_pcm",
                "container": "wav",
            },
        },
        timeout=90,
    )
    if not r.ok or "json" in r.headers.get("content-type", ""):
        raise RuntimeError(f"Text-to-speech failed ({r.status_code}): {r.text[:300]}")

    path = os.path.join(tempfile.gettempdir(), f"coach_{key}.wav")
    with open(path, "wb") as f:
        f.write(r.content)
    _tts_cache[key] = path
    return path


def ask_llm(history, lang, role):
    client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
    system = SYSTEM_PROMPT.format(role=role, lang_rule=LANGS[lang]["llm"])
    resp = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "system", "content": system}] + history,
        temperature=0.7,
        max_tokens=300,
    )
    text = resp.choices[0].message.content or ""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)  # for reasoning models
    return text.strip()


def _log(history):
    lines = []
    for m in history:
        if m["content"] == "Please begin the interview.":
            continue
        who = "Coach" if m["role"] == "assistant" else "You"
        lines.append(f"{who}: {m['content']}")
    return "\n\n".join(lines)


def start_interview(lang, role):
    _check_keys()
    try:
        history = [{"role": "user", "content": "Please begin the interview."}]
        reply = ask_llm(history, lang, role)
        history.append({"role": "assistant", "content": reply})
        return history, _log(history), text_to_speech(reply, lang), ""
    except gr.Error:
        raise
    except Exception as e:
        raise gr.Error(str(e))


def send_answer(audio_path, lang, role, history):
    _check_keys()
    if audio_path is None:
        raise gr.Error("Record your answer first.")
    if not history:
        raise gr.Error("Click 'Start interview' first.")
    try:
        heard = speech_to_text(audio_path, lang)
        if not heard:
            raise gr.Error("I could not hear anything. Please try again.")
        history = history + [{"role": "user", "content": heard}]
        reply = ask_llm(history, lang, role)
        history.append({"role": "assistant", "content": reply})
        return history, _log(history), text_to_speech(reply, lang), heard
    except gr.Error:
        raise
    except Exception as e:
        raise gr.Error(str(e))


with gr.Blocks(title="Voice Interview Coach") as demo:
    gr.Markdown(
        "# Voice Interview Coach\n"
        "Practise interviews in **English, Hinglish or Kannada**. "
        "Powered by Gnani Prisma (speech-to-text) and Timbre (text-to-speech)."
    )
    state = gr.State([])
    with gr.Row():
        lang = gr.Dropdown(list(LANGS), value="English", label="Language")
        role = gr.Textbox(value="a software engineering internship", label="Interview for")
    start_btn = gr.Button("1. Start interview", variant="primary")
    coach_audio = gr.Audio(label="Coach says (plays automatically)", type="filepath", autoplay=True)
    mic = gr.Audio(sources=["microphone"], type="filepath", format="wav",
                   max_length=55, label="2. Record your answer (max 55 seconds)")
    send_btn = gr.Button("3. Send answer", variant="primary")
    heard_box = gr.Textbox(label="What I heard", interactive=False)
    log_box = gr.Textbox(label="Conversation", lines=10, interactive=False)

    start_btn.click(start_interview, [lang, role], [state, log_box, coach_audio, heard_box])
    send_btn.click(send_answer, [mic, lang, role, state], [state, log_box, coach_audio, heard_box])

if __name__ == "__main__":
    demo.launch()
