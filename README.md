# Voice Interview Coach (English, Hinglish, Kannada)

A voice-based interview practice app for students. Pick a language, answer
interview questions by speaking, and get spoken feedback and a follow-up
question, all by voice.

Built for the **Great Indian AI Internship Challenge** by Gnani AI.
#GnaniAI #GreatIndianAIInternshipChallenge

## Why I built it
Many students in India have nobody to practise interviews with, and even fewer
can practise in their own language. This app lets you practise in English,
Hinglish or Kannada.

## How it works
1. You record your answer.
2. **Gnani Prisma** (speech-to-text) turns it into text.
3. An LLM acts as the interviewer and writes short feedback plus the next question.
4. **Gnani Timbre** (text-to-speech) reads the reply aloud.

## Demo
- Demo video: _paste your LinkedIn / X post link here_
- Screenshot: _add one here_

## Run it yourself
```bash
pip install -r requirements.txt
```
1. Copy `.env.example` to `.env` and fill in your keys.
2. Test each service: `python test_apis.py`
3. Start the app: `python app.py` and open the link shown in the terminal.

## Tech
Python, Gradio, Gnani Prisma and Timbre APIs, Google Gemini (OpenAI-compatible API).

## Notes
Voice input is limited to about 55 seconds per answer (the speech API limit is 60 seconds).
