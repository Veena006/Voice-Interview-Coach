"""Basic tests (no API calls). Run with:  python -m pytest"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import interview
import prompts

S = {"lang": "English", "role": "HR Intern", "category": "HR Interview",
     "difficulty": "Beginner", "total": 2}


def test_parse_clean_json():
    p = interview.parse_reply('{"score": 7, "feedback": "Good.", "question": "Why us?"}')
    assert p["score"] == 7 and p["spoken"] == "Good. Why us?"


def test_parse_json_inside_code_fence_and_markdown_removed():
    p = interview.parse_reply('```json\n{"score": 12, "feedback": "**Nice** 😀", "question": ""}\n```')
    assert p["score"] == 10                 # clamped to 1-10
    assert p["spoken"] == "Nice"            # markdown and emoji removed


def test_parse_plain_text_falls_back():
    p = interview.parse_reply("Tell me about yourself.")
    assert p["score"] is None and p["question"] == "Tell me about yourself."


def test_parse_bad_score():
    assert interview.parse_reply('{"score": "n/a", "feedback": "", "question": "Q?"}')["score"] is None


def test_session_flow_and_saving_once():
    raw = '{"score": null, "feedback": "", "question": "Q1?"}'
    s = interview.new_session(S, interview.parse_reply(raw))
    store = {"name": "T", "history": []}
    assert not interview.save_session(store, s)            # nothing answered yet
    r1 = '{"score": 6, "feedback": "OK.", "question": "Q2?"}'
    s = interview.apply_answer(s, "answer one", interview.parse_reply(r1))
    assert s["asked"] == 2 and not s["finished"]
    r2 = '{"score": 8, "feedback": "Great.", "question": ""}'
    s = interview.apply_answer(s, "answer two", interview.parse_reply(r2))
    assert s["finished"]
    assert interview.save_session(store, s)
    assert not interview.save_session(store, s)            # never saved twice
    assert store["history"][0]["avg"] == 7.0
    assert interview.overall_stats(store["history"])["questions"] == 2


def test_prompts_mention_json_and_final_turn():
    assert "JSON" in prompts.build_system_prompt("HR Intern", "HR Interview", "Beginner", "English", 5)
    assert "Do NOT ask another question" in prompts.turn_note(5, 5)
    assert "question 3 of 5" in prompts.turn_note(2, 5)


# ---- broken AI replies must never be read aloud ----
def _never_leaks(p):
    for bad in ('score', 'feedback', '{', '}', 'null'):
        assert bad not in p["spoken"]


def test_unescaped_quotes_inside_json():
    p = interview.parse_reply('{"score": null, "feedback": "", "question": "Tell me about "yourself" please."}')
    assert p["ok"] and "yourself" in p["spoken"]
    _never_leaks(p)


def test_json_cut_off_in_the_middle():
    p = interview.parse_reply('{"score": 7, "feedback": "Good point.", "question": "What is a list in Py')
    assert p["ok"] and p["score"] == 7 and p["spoken"].startswith("Good point.")
    _never_leaks(p)


def test_text_before_and_after_json():
    p = interview.parse_reply('Sure! {"score": null, "feedback": "", "question": "Hi, tell me about yourself."} Hope it helps')
    assert p["ok"] and p["spoken"] == "Hi, tell me about yourself."


def test_null_text_values_are_dropped():
    p = interview.parse_reply('{"score": null, "feedback": null, "question": "First question?"}')
    assert p["spoken"] == "First question?"


def test_unreadable_json_like_reply_is_not_ok():
    p = interview.parse_reply('{ "score" ')
    assert not p["ok"] and p["spoken"] == ""
    assert not interview.parse_reply("")["ok"]


def test_kannada_reply():
    p = interview.parse_reply('{"score": 6, "feedback": "ಚೆನ್ನಾಗಿದೆ.", "question": "ನಿಮ್ಮ ಬಗ್ಗೆ ಹೇಳಿ."}')
    assert p["ok"] and "ನಿಮ್ಮ" in p["spoken"]


def test_json_mode_falls_back_when_model_rejects_it(monkeypatch):
    import services, config

    class Err(Exception):
        status_code = 400

    class Msg: content = '{"score": null, "feedback": "", "question": "Hi?"}'
    class Choice: message = Msg()
    class Resp: choices = [Choice()]
    seen = []

    class Completions:
        def create(self, **kw):
            seen.append("response_format" in kw)
            if "response_format" in kw:
                raise Err("json mode not supported")
            return Resp()

    class Client:
        class chat: completions = Completions()

    monkeypatch.setattr(services, "_get_client", lambda: Client())
    assert "Hi?" in services.ask_llm([], "system JSON", json_mode=True)
    assert seen == [True, False]