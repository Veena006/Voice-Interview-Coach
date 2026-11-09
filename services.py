"""All outside API calls live here: Gnani speech-to-text, Gnani text-to-speech, LLM.
The Gradio screen (app.py) never talks to the APIs directly."""
import hashlib
import os
import re
import tempfile
import wave
import struct
import time

import requests
from openai import OpenAI

import config

_tts_cache = {}  # saves credits: the same text is never synthesised twice


def _headers():
    return {"X-API-Key-ID": config.GNANI_API_KEY}


def audio_duration_seconds(path):
    """Length of a .wav recording in seconds (None if it cannot be read)."""
    try:
        with wave.open(path, "rb") as w:
            return w.getnframes() / float(w.getframerate())
    except Exception:
        return None


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
                config.STT_URL,
                headers=_headers(),
                files={field: f},
                data={"model": config.STT_MODEL,
                      "language_code": config.LANGS[lang]["stt"]},
                timeout=90,
            )
        if r.ok:
            text = _find_text(r.json())
            if text is None:
                raise RuntimeError(f"Could not find transcript in response: {r.text[:300]}")
            return text.strip()
        last_error = f"{r.status_code}: {r.text[:300]}"
    raise RuntimeError(f"Speech-to-text failed ({last_error})")


def text_to_speech(text, lang, speed=1.0):
    """Gnani Timbre: text -> wav file path. Cached to save credits."""
    voice = config.VOICES[lang]
    key = hashlib.md5(f"{lang}|{voice}|{speed}|{text}".encode()).hexdigest()
    if key in _tts_cache and os.path.exists(_tts_cache[key]):
        return _tts_cache[key]

    r = requests.post(
        config.TTS_URL,
        headers={**_headers(), "Content-Type": "application/json"},
        json={
            "text": text,
            "voice": voice,
            "model": config.TTS_MODEL,
            "language": config.LANGS[lang]["tts"],
            "speed": speed,
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

        # Convert response into editable WAV data
    audio_data = bytearray(r.content)

    # Fix Gnani's WAV header if it contains unknown size values
    if (
        len(audio_data) >= 44
        and audio_data[:4] == b"RIFF"
        and audio_data[8:12] == b"WAVE"
        and audio_data[36:40] == b"data"
    ):
        riff_size = struct.unpack_from("<I", audio_data, 4)[0]
        data_size = struct.unpack_from("<I", audio_data, 40)[0]

        if riff_size == 0xFFFFFFFF or data_size == 0xFFFFFFFF:
            struct.pack_into("<I", audio_data, 4, len(audio_data) - 8)
            struct.pack_into("<I", audio_data, 40, len(audio_data) - 44)

    path = os.path.join(tempfile.gettempdir(), f"coach_{key}.wav")

    with open(path, "wb") as f:
        f.write(audio_data)

    _tts_cache[key] = path
    return path

_llm_client = None


def _get_client():
    """Create the LLM connection once and reuse it (saves time on every call)."""
    global _llm_client
    if _llm_client is None:
        _llm_client = OpenAI(
            api_key=config.LLM_API_KEY,
            base_url=config.LLM_BASE_URL,
            timeout=30,
            max_retries=0,
        )
    return _llm_client


def ask_llm(history, system_prompt, json_mode=False):
    """Send the conversation to the LLM, retrying on temporary errors."""
    client = _get_client()
    kwargs = dict(
        model=config.LLM_MODEL,
        messages=[{"role": "system", "content": system_prompt}] + history,
        temperature=0.7,
        max_tokens=900,  # reasoning models spend some of these on thinking
    )
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}  # asks the LLM for valid JSON
    if config.LLM_REASONING_EFFORT:
        kwargs["extra_body"] = {"reasoning_effort": config.LLM_REASONING_EFFORT}

    for attempt in range(4):
        try:
            resp = client.chat.completions.create(**kwargs)
            text = resp.choices[0].message.content or ""
            text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
            return text.strip()
        except Exception as e:
            status_code = getattr(e, "status_code", None)
            if "response_format" in kwargs and status_code in (400, 422):
                kwargs.pop("response_format")  # this model has no JSON mode: carry on without
                continue
            # Retry only temporary server / rate-limit errors
            if status_code not in (429, 500, 502, 503, 504) or attempt == 3:
                raise
            wait_time = 2 ** (attempt + 1)
            print(f"LLM temporarily unavailable. Retrying in {wait_time} seconds...")
            time.sleep(wait_time)