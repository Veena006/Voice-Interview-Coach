"""Interview logic with no screen and no API calls: reading the AI's reply,
keeping the session, saving finished interviews and calculating statistics."""
import json
import re
from datetime import datetime

_EMOJI = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF]")


def clean_spoken(text):
    """Remove markdown symbols and emojis so the text can be read aloud cleanly.
    The SAME cleaned text is shown on screen and sent to text-to-speech."""
    text = _EMOJI.sub("", text or "")
    text = re.sub(r"[*_#`]+", "", text)
    return re.sub(r"\s+", " ", text).strip()


_KEY = re.compile(r'"(score|feedback|question)"\s*:\s*')


def _lenient_fields(raw):
    """Pull score / feedback / question out of JSON that is slightly broken
    (unescaped quotes, cut off in the middle, extra text around it)."""
    matches = list(_KEY.finditer(raw))
    if not matches:
        return None
    out = {}
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
        value = re.sub(r"[\s,}`]+$", "", raw[m.end():end].strip())
        if value.startswith('"'):
            value = value[1:]
        if value.endswith('"'):
            value = value[:-1]
        out[m.group(1)] = value.replace('\\"', '"').replace("\\n", " ")
    return out


def _looks_like_json(text):
    return text.lstrip().startswith(("{", "```")) or '"score"' in text or '"question"' in text


def parse_reply(raw):
    """Turn the LLM reply into score, feedback, question and the text to speak.

    Returns "ok": False when the reply is JSON-like but unreadable. The caller must
    then ask again instead of speaking it. Raw JSON is never returned as speech."""
    raw = (raw or "").strip()
    data = None
    match = re.search(r"\{.*\}", raw, flags=re.S)
    if match:
        try:
            data = json.loads(match.group(0))
        except ValueError:
            data = None
    if not isinstance(data, dict):
        data = _lenient_fields(raw)

    if not isinstance(data, dict):
        if _looks_like_json(raw) or not raw:
            return {"score": None, "feedback": "", "question": "", "spoken": "", "ok": False}
        text = clean_spoken(raw)  # plain text from the AI: use it as the question
        return {"score": None, "feedback": "", "question": text, "spoken": text, "ok": True}

    try:
        score = max(1, min(10, int(round(float(data.get("score"))))))
    except (TypeError, ValueError):
        score = None
    feedback = clean_spoken(str(data.get("feedback") or ""))
    question = clean_spoken(str(data.get("question") or ""))
    if feedback.lower() == "null":
        feedback = ""
    if question.lower() == "null":
        question = ""
    spoken = " ".join(part for part in (feedback, question) if part)
    if re.search(r'"(score|feedback|question)"|[{}]', spoken):
        return {"score": None, "feedback": "", "question": "", "spoken": "", "ok": False}
    return {"score": score, "feedback": feedback, "question": question,
            "spoken": spoken, "ok": True}


def canonical(parsed):
    """Clean JSON for the LLM's memory, so it keeps seeing the correct format."""
    return json.dumps({"score": parsed["score"], "feedback": parsed["feedback"],
                       "question": parsed["question"]}, ensure_ascii=False)


# ---------------------------------------------------------------- sessions
def new_session(settings, parsed):
    """Start a session after the AI asked question 1."""
    return {
        "settings": settings,
        "messages": [{"role": "assistant", "content": canonical(parsed)}],  # what the LLM sees
        "turns": [("Coach", parsed["spoken"])],                # what the screen shows
        "qa": [{"question": parsed["question"] or parsed["spoken"],
                "answer": None, "score": None, "feedback": ""}],
        "asked": 1,
        "finished": False,
        "saved": False,
        "date": datetime.now().strftime("%d %b %Y, %I:%M %p"),
    }


def is_last_question(session):
    return session["asked"] >= session["settings"]["total"]


def apply_answer(session, heard, parsed):
    """Return a new session that includes the student's answer and the AI's reply."""
    qa = [dict(item) for item in session["qa"]]
    qa[-1].update(answer=heard, score=parsed["score"], feedback=parsed["feedback"])
    finished = is_last_question(session)
    asked = session["asked"]
    if not finished:
        qa.append({"question": parsed["question"] or parsed["spoken"],
                   "answer": None, "score": None, "feedback": ""})
        asked += 1
    new = dict(session)
    new.update(
        qa=qa,
        asked=asked,
        finished=finished,
        messages=session["messages"] + [{"role": "user", "content": heard},
                                        {"role": "assistant", "content": canonical(parsed)}],
        turns=session["turns"] + [("You", heard), ("Coach", parsed["spoken"])],
    )
    return new


def llm_messages(session, opening_note, heard=None):
    """The conversation to send to the LLM."""
    msgs = [{"role": "user", "content": opening_note}] + session["messages"]
    if heard is not None:
        msgs.append({"role": "user", "content": heard})
    return msgs


def transcript(session):
    return "\n\n".join(f"{who}: {text}" for who, text in session["turns"])


def answered_count(session):
    return sum(1 for item in session["qa"] if item.get("answer"))


# ---------------------------------------------------------------- history
def average_score(answers):
    scores = [a["score"] for a in answers if a.get("score") is not None]
    return round(sum(scores) / len(scores), 1) if scores else None


def save_session(store, session):
    """Save an interview into this user's history (only once, only if answered)."""
    if not store or not session or session.get("saved") or answered_count(session) == 0:
        return False
    s = session["settings"]
    answers = [dict(a) for a in session["qa"] if a.get("answer")]
    store["history"].append({
        "id": len(store["history"]) + 1,
        "date": session["date"],
        "role": s["role"], "category": s["category"], "difficulty": s["difficulty"],
        "lang": s["lang"], "total": s["total"],
        "answers": answers,
        "avg": average_score(answers),
        "complete": len(answers) >= s["total"],
    })
    session["saved"] = True
    return True


def overall_stats(history):
    avgs = [r["avg"] for r in history if r["avg"] is not None]
    return {
        "interviews": len(history),
        "questions": sum(len(r["answers"]) for r in history),
        "avg": round(sum(avgs) / len(avgs), 1) if avgs else None,
        "best": max(avgs) if avgs else None,
    }