"""
Test each API one by one (run this BEFORE app.py).

    python test_apis.py                 -> tests LLM + text-to-speech in all 3 languages
    python test_apis.py my_clip.wav     -> also tests speech-to-text on your recording
"""
import sys

import config
import services

SAMPLES = {
    "English": "Hello, welcome to your practice interview. Tell me about yourself.",
    "Hinglish": "Namaste, aapke practice interview mein swagat hai. Apne baare mein bataiye.",
    "Kannada": "ನಮಸ್ಕಾರ, ನಿಮ್ಮ ಅಭ್ಯಾಸ ಸಂದರ್ಶನಕ್ಕೆ ಸ್ವಾಗತ. ದಯವಿಟ್ಟು ನಿಮ್ಮ ಬಗ್ಗೆ ತಿಳಿಸಿ.",
}

missing = config.missing_settings()
if missing:
    sys.exit("Fill these in your .env file first: " + ", ".join(missing))

print("--- 1. LLM ---")
try:
    print(services.ask_llm(
        [{"role": "user", "content": "Ask me one interview question."}],
        "You are a friendly interview coach. Reply in one short sentence."))
except Exception as e:
    print("LLM FAILED:", e)

print("\n--- 2. Text-to-speech (saves a .wav per language) ---")
for lang, text in SAMPLES.items():
    try:
        path = services.text_to_speech(text, lang)
        print(f"{lang}: OK -> {path}  (play it and check it sounds right)")
    except Exception as e:
        print(f"{lang}: FAILED -> {e}")

if len(sys.argv) > 1:
    print("\n--- 3. Speech-to-text ---")
    for lang in config.LANGS:
        try:
            print(f"{lang}: {services.speech_to_text(sys.argv[1], lang)}")
        except Exception as e:
            print(f"{lang}: FAILED -> {e}")
else:
    print("\n(Add a recording to test speech-to-text: python test_apis.py my_clip.wav)")
