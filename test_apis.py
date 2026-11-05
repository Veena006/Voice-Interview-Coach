"""
Test each API one by one (run this BEFORE app.py).

    python test_apis.py                 -> tests LLM + text-to-speech in all 3 languages
    python test_apis.py my_clip.wav     -> also tests speech-to-text on your recording
                                           (record a short 5-10 second clip first)
"""
import sys

import app

SAMPLES = {
    "English": "Hello, welcome to your practice interview. Tell me about yourself.",
    "Hinglish": "Namaste, aapke practice interview mein swagat hai. Apne baare mein bataiye.",
    "Kannada": "ನಮಸ್ಕಾರ, ನಿಮ್ಮ ಅಭ್ಯಾಸ ಸಂದರ್ಶನಕ್ಕೆ ಸ್ವಾಗತ. ನಿಮ್ಮ ಬಗ್ಗೆ ಹೇಳಿ.",
}

print("--- 1. LLM ---")
try:
    print(app.ask_llm([{"role": "user", "content": "Please begin the interview."}],
                      "English", "a software internship"))
except Exception as e:
    print("LLM FAILED:", e)

print("\n--- 2. Text-to-speech (saves a .wav per language) ---")
for lang, text in SAMPLES.items():
    try:
        path = app.text_to_speech(text, lang)
        print(f"{lang}: OK -> {path}  (play it and check it sounds right)")
    except Exception as e:
        print(f"{lang}: FAILED -> {e}")

if len(sys.argv) > 1:
    print("\n--- 3. Speech-to-text ---")
    for lang in app.LANGS:
        try:
            print(f"{lang}: {app.speech_to_text(sys.argv[1], lang)}")
        except Exception as e:
            print(f"{lang}: FAILED -> {e}")
else:
    print("\n(Add a recording to test speech-to-text: python test_apis.py my_clip.wav)")
