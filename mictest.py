"""
Voice Interview Coach (English / Hinglish / Kannada)
This file is the screen and its events. Everything else lives in:
  services.py   Gnani speech-to-text, text-to-speech, LLM calls
  interview.py  reading AI replies, sessions, history, statistics
  views.py      dashboard / history / performance content
  prompts.py    instructions for the LLM       config.py  settings
  styles.py     black + neon-green theme

Run:  python app.py   then open  http://127.0.0.1:7860
"""
import time

import gradio as gr

import config
import interview
import prompts
import services
import views
from styles import CUSTOM_CSS

ROLES = [
    "Software Engineering Intern", "Python Developer Intern", "Web Development Intern",
    "Full Stack Developer Intern", "Mobile App Developer Intern", "Data Science Intern",
    "Data Analyst Intern", "Machine Learning / AI Intern", "Cloud / DevOps Intern",
    "Cybersecurity Intern", "Electronics / Embedded Systems Intern", "UI/UX Design Intern",
    "Product Management Intern", "Business Analyst Intern", "Digital Marketing Intern",
    "Sales & Business Development Intern", "HR Intern", "Finance / Accounting Intern",
    "Content Writing Intern", "Customer Support Intern",
]

MIC_HELP = ("🎙️ **How to record:** click the microphone, speak, then press **Stop**. "
            "Wait for the ✅ message before submitting. If the microphone does not work, "
            "use the **Upload** tab in the box.")

_u = gr.update  # "leave this component unchanged"


# =====================================================================
# SIGN IN / SIGN OUT  (simple profile for this browser session only)
# =====================================================================
def _enter(name):
    store = {"name": name, "history": []}
    return (store, _u(visible=False), _u(visible=True), views.user_chip(name),
            views.render_dashboard(store), gr.Tabs(selected="dashboard"))


def sign_in(name):
    name = (name or "").strip()
    if not name:
        raise gr.Error("Please type your name, or choose 'Continue as guest'.")
    return _enter(name[:40])


def sign_in_guest():
    return _enter("Guest")


def sign_out():
    return (None, None, _u(visible=True), _u(visible=False), "", None, "",
            views.progress(None), "", "")


# =====================================================================
# INTERVIEW
# =====================================================================
def _check_settings():
    missing = config.missing_settings()
    if missing:
        raise gr.Error("Fill these in your .env file: " + ", ".join(missing))


def mic_status(audio_path):
    """Shows whether Gradio really has your recording."""
    if audio_path is None:
        return MIC_HELP
    seconds = services.audio_duration_seconds(audio_path)
    if seconds is None:
        return "✅ Recording ready. Now click **Submit Answer**."
    if seconds < 0.5:
        return "⚠️ That recording is empty. Please record again."
    if seconds > config.MAX_AUDIO_SECONDS:
        return f"⚠️ Recording is {seconds:.0f}s. Please keep it under {config.MAX_AUDIO_SECONDS}s."
    return f"✅ Recording ready ({seconds:.0f}s). Now click **Submit Answer**."


# Output order for the interview buttons:
# [store, session, transcript, coach_audio, heard, progress, status, score, mic]

def start_interview(lang, role, category, difficulty, total, speed, store, session):
    if not store:
        raise gr.Error("Please sign in first.")
    role = (role or "").strip()
    if not role:
        raise gr.Error("Please choose or type the job role you are interviewing for.")
    _check_settings()
    interview.save_session(store, session)  # keep an unfinished interview in History

    total = int(total)
    settings = {"lang": lang, "role": role, "category": category,
                "difficulty": difficulty, "total": total}
    yield (store, session, _u(), _u(), "", "", "⏳ Preparing your first question…", "", _u())

    try:
        t0 = time.perf_counter()
        system = prompts.build_system_prompt(role, category, difficulty, lang, total)
        raw = services.ask_llm([{"role": "user", "content": prompts.opening_note()}], system)
        parsed = interview.parse_reply(raw)
        if not parsed["spoken"]:
            raise RuntimeError("The AI sent an empty reply. Please click Start Interview again.")
        t1 = time.perf_counter()
        audio = services.text_to_speech(parsed["spoken"], lang, speed)
        t2 = time.perf_counter()
    except gr.Error:
        raise
    except Exception as e:
        raise gr.Error(str(e))

    print(f"[timing] start: AI {t1 - t0:.1f}s | voice {t2 - t1:.1f}s")
    session = interview.new_session(settings, raw, parsed)
    yield (store, session, interview.transcript(session), audio, "",
           views.progress(session), f"⏱ Ready in {t2 - t0:.1f}s", "", None)


def send_answer(audio_path, speed, store, session):
    if not store:
        raise gr.Error("Please sign in first.")
    if not session:
        raise gr.Error("Click 'Start Interview' first.")
    if session["finished"]:
        raise gr.Error("This interview is finished. Click 'Start Interview' for a new one.")
    if audio_path is None:
        raise gr.Error("No recording found. Click the microphone, speak, press Stop, "
                       "wait for the ✅ message, then click Submit Answer.")
    seconds = services.audio_duration_seconds(audio_path)
    if seconds is not None and seconds < 0.5:
        raise gr.Error("The recording is empty. Please record again.")
    if seconds is not None and seconds > config.MAX_AUDIO_SECONDS:
        raise gr.Error(f"Your answer is {seconds:.0f} seconds long. "
                       f"Please keep it under {config.MAX_AUDIO_SECONDS} seconds.")
    _check_settings()

    s = session["settings"]
    yield (store, session, _u(), _u(), _u(), _u(), "🎧 Listening to your answer…", _u(), _u())
    try:
        t0 = time.perf_counter()
        heard = services.speech_to_text(audio_path, s["lang"])
        if not heard:
            raise gr.Error("I could not hear anything. Please record again.")
        t1 = time.perf_counter()

        # show the student's own words straight away, while the AI is thinking
        yield (store, session, _u(), _u(), heard, _u(), "🤔 Thinking…", _u(), _u())

        system = (prompts.build_system_prompt(s["role"], s["category"], s["difficulty"],
                                              s["lang"], s["total"])
                  + "\n" + prompts.turn_note(session["asked"], s["total"]))
        raw = services.ask_llm(
            interview.llm_messages(session, prompts.opening_note(), heard), system)
        parsed = interview.parse_reply(raw)
        if not parsed["spoken"]:
            if interview.is_last_question(session):
                parsed["spoken"] = "Well done! That was the last question."
            else:
                raise RuntimeError("The AI sent an empty reply. Please submit your answer again.")
        t2 = time.perf_counter()

        audio = services.text_to_speech(parsed["spoken"], s["lang"], speed)
        t3 = time.perf_counter()
    except gr.Error:
        raise
    except Exception as e:
        raise gr.Error(str(e))

    print(f"[timing] answer: speech-to-text {t1 - t0:.1f}s | AI {t2 - t1:.1f}s | "
          f"voice {t3 - t2:.1f}s | total {t3 - t0:.1f}s")
    session = interview.apply_answer(session, heard, raw, parsed)
    if session["finished"]:
        interview.save_session(store, session)
    # text and voice come from the same string and arrive together
    yield (store, session, interview.transcript(session), audio, heard,
           views.progress(session), f"⏱ Replied in {t3 - t0:.1f}s",
           views.score_line(parsed["score"]), None)


def end_interview(store, session):
    if not store:
        raise gr.Error("Please sign in first.")
    if not session or interview.answered_count(session) == 0:
        raise gr.Error("Answer at least one question before ending the interview.")
    session = dict(session, finished=True)
    interview.save_session(store, session)
    return store, session, views.progress(session), "💾 Saved to your History."


# =====================================================================
# HISTORY
# =====================================================================
def refresh_history(store):
    return views.history_rows(store), "*Click a row to see the full interview.*"


def show_record(store, evt: gr.SelectData):
    row = evt.index[0] if isinstance(evt.index, (list, tuple)) else evt.index
    record = views.record_by_row(store, row)
    return views.record_markdown(record) if record else "*Nothing selected.*"


def clear_history(store):
    if store:
        store["history"] = []
    return store, [], "*History cleared.*"


# =====================================================================
# SCREEN
# =====================================================================
with gr.Blocks(title="Voice Interview Coach") as demo:

    store = gr.State(None)    # signed-in user + their interview history
    session = gr.State(None)  # the interview in progress

    # ---------------- LOGIN ----------------
    with gr.Column(elem_id="login-card") as login_view:
        gr.HTML("""
            <div class="login-head">
                <div class="orb"></div>
                <h1>Voice Interview Coach</h1>
                <p>Practise interviews in English, Hinglish and Kannada</p>
            </div>""")
        name_box = gr.Textbox(label="Your name", placeholder="e.g. Veena", max_lines=1)
        signin_btn = gr.Button("Continue →", variant="primary")
        guest_btn = gr.Button("Continue as guest")
        gr.Markdown("*This is a simple profile for this browser session. There is no password "
                    "and nothing is stored after you close or refresh the page.*")

    # ---------------- MAIN APP ----------------
    with gr.Row(visible=False) as main_view:

        with gr.Column(scale=1, min_width=230, elem_id="sidebar"):
            gr.HTML('<div id="brand">◈ VOICE AI</div>')
            user_chip = gr.HTML("")
            signout_btn = gr.Button("Sign out")

        with gr.Column(scale=5):
            gr.HTML("""
                <div id="hero">
                    <p>YOUR PERSONAL AI INTERVIEW PARTNER</p>
                    <h1>Practice smarter.<br><span>Interview better.</span></h1>
                </div>""")

            with gr.Tabs(selected="dashboard") as tabs:

                # ---- Dashboard ----
                with gr.Tab("🏠 Dashboard", id="dashboard") as dash_tab:
                    dash_html = gr.HTML("")
                    go_btn = gr.Button("✦ Start a new interview", variant="primary")

                # ---- New Interview ----
                with gr.Tab("🎙️ New Interview", id="interview"):
                    gr.Markdown("### 1. Set up your interview")
                    with gr.Row():
                        lang = gr.Dropdown(choices=list(config.LANGS), value="English",
                                           label="Interview Language")
                        role = gr.Dropdown(choices=ROLES, value=ROLES[0],
                                           allow_custom_value=True,
                                           label="Internship / Job Role (pick or type your own)")
                    with gr.Row():
                        category = gr.Dropdown(choices=config.CATEGORIES,
                                               value=config.CATEGORIES[0],
                                               label="Interview Type")
                        difficulty = gr.Dropdown(choices=config.DIFFICULTIES,
                                                 value="Beginner", label="Difficulty")
                        total = gr.Slider(config.MIN_QUESTIONS, config.MAX_QUESTIONS,
                                          value=config.DEFAULT_QUESTIONS, step=1,
                                          label="Number of Questions")
                    start_btn = gr.Button("✦ Start Interview", variant="primary")

                    gr.Markdown("### 2. Listen and answer")
                    progress = gr.Markdown(views.progress(None))
                    status = gr.Markdown("")
                    gr.HTML('<div class="orb-box"><div class="orb"></div>'
                            '<h3>AI Interview Coach</h3></div>')
                    coach_audio = gr.Audio(label="🔊 Coach voice (plays automatically)",
                                           type="filepath", autoplay=True)
                    log_box = gr.Textbox(label="💬 What the coach said (same as the voice)",
                                         lines=10, interactive=False)

                    mic = gr.Audio(sources=["microphone", "upload"], type="filepath",
                                   label="🎤 Record or upload your answer", interactive=True)
                    mic_msg = gr.Markdown(MIC_HELP)
                    with gr.Row():
                        send_btn = gr.Button("➤ Submit Answer", variant="primary", scale=3)
                        end_btn = gr.Button("⏹ End & save", scale=1)
                    score_md = gr.Markdown("")
                    heard_box = gr.Textbox(label="What I heard you say", interactive=False)

                # ---- History ----
                with gr.Tab("🕘 History", id="history") as hist_tab:
                    gr.Markdown("Interviews from this session. Click a row to open it.")
                    hist_df = gr.Dataframe(headers=views.HISTORY_HEADERS, value=[],
                                           interactive=False, wrap=True)
                    hist_detail = gr.Markdown("*Click a row to see the full interview.*")
                    clear_btn = gr.Button("🗑 Clear history")

                # ---- Performance ----
                with gr.Tab("📊 Performance", id="performance") as perf_tab:
                    perf_html = gr.HTML("")

                # ---- Settings ----
                with gr.Tab("⚙️ Settings", id="settings"):
                    gr.Markdown("### Voice")
                    speed = gr.Slider(config.MIN_SPEED, config.MAX_SPEED,
                                      value=config.DEFAULT_SPEED, step=0.1,
                                      label="Coach speaking speed (1.0 = normal)")
                    gr.Markdown(
                        "Voices in use (change them in your `.env` file): "
                        + ", ".join(f"**{k}**: {v}" for k, v in config.VOICES.items()))

    # ---------------- EVENTS ----------------
    session_out = [store, session, log_box, coach_audio, heard_box, progress,
                   status, score_md, mic]

    signin_btn.click(sign_in, [name_box],
                     [store, login_view, main_view, user_chip, dash_html, tabs])
    name_box.submit(sign_in, [name_box],
                    [store, login_view, main_view, user_chip, dash_html, tabs])
    guest_btn.click(sign_in_guest, None,
                    [store, login_view, main_view, user_chip, dash_html, tabs])
    signout_btn.click(sign_out, None,
                      [store, session, login_view, main_view, log_box, coach_audio,
                       heard_box, progress, status, score_md])

    go_btn.click(lambda: gr.Tabs(selected="interview"), None, tabs)
    dash_tab.select(views.render_dashboard, [store], [dash_html])
    perf_tab.select(views.render_performance, [store], [perf_html])
    hist_tab.select(refresh_history, [store], [hist_df, hist_detail])
    hist_df.select(show_record, [store], [hist_detail])
    clear_btn.click(clear_history, [store], [store, hist_df, hist_detail])

    mic.change(mic_status, [mic], [mic_msg])
    start_btn.click(start_interview,
                    [lang, role, category, difficulty, total, speed, store, session],
                    session_out)
    send_btn.click(send_answer, [mic, speed, store, session], session_out)
    end_btn.click(end_interview, [store, session], [store, session, progress, status])


if __name__ == "__main__":
    demo.launch(
        theme=gr.themes.Base(primary_hue="green", neutral_hue="slate"),
        css=CUSTOM_CSS,
    )