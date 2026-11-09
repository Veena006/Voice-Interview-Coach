"""
Voice Interview Coach (English / Hinglish / Kannada)
This file is the screen and its events. Everything else lives in:
  auth.py       email accounts and saved history (local SQLite file)
  candidate_profile.py  resume (PDF), GitHub and LinkedIn text -> skills, projects, tips
  services.py   Gnani speech-to-text, text-to-speech, LLM calls
  interview.py  reading AI replies, sessions, history, statistics
  views.py      dashboard / history / performance content
  prompts.py    instructions for the LLM       config.py  settings
  styles.py     black + neon-green theme

Run:  python app.py   then open  http://127.0.0.1:7860
"""
import time

import gradio as gr

import auth
import config
import interview
import candidate_profile as profile
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
# SIGN IN / SIGN UP / SIGN OUT
# =====================================================================
def _enter(user=None):
    """Open the app for a guest (user=None) or a signed-in account."""
    store = {"name": "Guest", "user_id": None, "email": None, "history": [], "profile": None}
    if user:
        store.update(name=user["name"], user_id=user["id"], email=user["email"],
                     history=auth.load_history(user["id"]))
    return (store, _u(visible=False), _u(visible=True),
            views.user_chip(store["name"], store["email"]),
            views.render_dashboard(store), gr.Tabs(selected="dashboard"), "", "", "",
            *_nav_updates("dashboard"))


def sign_in_email(email, password):
    if not (email or "").strip() or not password:
        raise gr.Error("Please enter your email and password.")
    try:
        return _enter(auth.verify_user(email, password))
    except ValueError as e:
        raise gr.Error(str(e))


def sign_up(name, email, password, confirm):
    problem = auth.validate_signup(name, email, password, confirm)
    if problem:
        raise gr.Error(problem)
    try:
        return _enter(auth.create_user(name, email, password))
    except ValueError as e:
        raise gr.Error(str(e))


def sign_in_guest():
    return _enter()


def sign_out():
    # store, session, login_view, main_view, transcript, audio, heard, progress,
    # status, score, profile_html, profile_status
    return (None, None, _u(visible=True), _u(visible=False), "", None, "",
            views.progress(None), "", "", "", "")


def account_info(store):
    if not store:
        return ""
    if store.get("user_id"):
        return (f"**{store['name']}** · {store['email']}\n\nYour interviews are saved in a "
                f"local database on this computer. Your resume is never saved.")
    return "**Guest session.** Nothing is saved after you close or refresh this page."


def delete_account(confirmed, store):
    if not store or not store.get("user_id"):
        raise gr.Error("Guests do not have an account to delete.")
    if not confirmed:
        raise gr.Error("Tick the box to confirm that you want to delete your account.")
    auth.delete_user(store["user_id"])
    return sign_out() + (False,)


# =====================================================================
# INTERVIEW
# =====================================================================
def _save(store, session):
    """Save an interview to History (and to the account database for signed-in users)."""
    if interview.save_session(store, session) and store.get("user_id"):
        try:
            auth.add_record(store["user_id"], store["history"][-1])
        except Exception as e:
            print("[warning] could not save the interview to the database:", e)


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


def _ask(messages, system):
    """Ask the LLM. If its reply cannot be read, ask once more instead of speaking junk."""
    raw = services.ask_llm(messages, system, json_mode=True)
    parsed = interview.parse_reply(raw)
    if not parsed["ok"]:
        print("[warning] unreadable AI reply, asking again:", raw[:300])
        raw = services.ask_llm(
            messages, system + "\nIMPORTANT: reply with ONLY the JSON object, no other text.",
            json_mode=True)
        parsed = interview.parse_reply(raw)
        if not parsed["ok"]:
            print("[warning] still unreadable:", raw[:300])
            raise RuntimeError("The AI sent a reply I could not read. Please try again.")
    return parsed


# Output order for the interview buttons:
# [store, session, transcript, coach_audio, heard, progress, status, score, mic]

def start_interview(lang, role, category, difficulty, total, speed, use_profile, store, session):
    if not store:
        raise gr.Error("Please sign in first.")
    role = (role or "").strip()
    if not role:
        raise gr.Error("Please choose or type the job role you are interviewing for.")
    _check_settings()
    _save(store, session)  # keep an unfinished interview in History

    total = int(total)
    profile_text = store["profile"]["prompt"] if (use_profile and store.get("profile")) else ""
    settings = {"lang": lang, "role": role, "category": category,
                "difficulty": difficulty, "total": total, "profile": profile_text}
    note = " (using your profile)" if profile_text else ""
    yield (store, session, _u(), _u(), "", "", f"⏳ Preparing your first question{note}…", "", _u())

    try:
        t0 = time.perf_counter()
        system = prompts.build_system_prompt(role, category, difficulty, lang, total, profile_text)
        parsed = _ask([{"role": "user", "content": prompts.opening_note()}], system)
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
    session = interview.new_session(settings, parsed)
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
                                              s["lang"], s["total"], s.get("profile", ""))
                  + "\n" + prompts.turn_note(session["asked"], s["total"]))
        parsed = _ask(interview.llm_messages(session, prompts.opening_note(), heard), system)
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
    session = interview.apply_answer(session, heard, parsed)
    if session["finished"]:
        _save(store, session)
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
    _save(store, session)
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
        if store.get("user_id"):
            auth.clear_history(store["user_id"])
    return store, [], "*History cleared.*"


# =====================================================================
# PROFILE (resume, GitHub, LinkedIn text)
# =====================================================================
def analyse_profile(role, resume_path, github, linkedin, store):
    if not store:
        raise gr.Error("Please sign in first.")
    github, linkedin = (github or "").strip(), (linkedin or "").strip()
    if not (resume_path or github or linkedin):
        raise gr.Error("Upload a resume, enter a GitHub username, or paste your LinkedIn text first.")
    _check_settings()
    role = (role or "").strip() or ROLES[0]

    yield store, _u(), "⏳ Reading your information…", _u()
    try:
        resume_text = profile.read_resume(resume_path) if resume_path else ""
        github_text = profile.fetch_github(github) if github else ""
        yield store, _u(), "🤔 Analysing your profile…", _u()
        analysis = profile.analyse(role, resume_text, github_text, linkedin)
    except ValueError as e:
        raise gr.Error(str(e))
    except gr.Error:
        raise
    except Exception as e:
        raise gr.Error(str(e))

    sources = [name for name, used in (("resume", resume_text), ("GitHub", github_text),
                                       ("LinkedIn text", linkedin)) if used]
    store["profile"] = {"role": role, "analysis": analysis, "sources": sources,
                        "prompt": profile.prompt_text(analysis)}
    profile.delete_upload(resume_path)  # the PDF is no longer needed
    yield (store, views.render_profile(analysis, sources),
           "✅ Profile ready. Turn on “Use my profile” in New Interview to get personalised questions.",
           None)


def remove_profile(store):
    if store:
        store["profile"] = None
    return store, "", "Profile removed from this session.", None, "", ""


# =====================================================================
# SIDEBAR NAVIGATION
# =====================================================================
NAV_ITEMS = [
    ("dashboard", "🏠  Dashboard"),
    ("interview", "🎙️  New Interview"),
    ("history", "🕘  History"),
    ("performance", "📊  Performance"),
    ("profile", "👤  Profile & Resume"),
    ("settings", "⚙️  Settings"),
]


def _nav_updates(active):
    """Highlight the current page in the sidebar."""
    return [gr.update(elem_classes=["nav-btn", "active"] if key == active else ["nav-btn"])
            for key, _ in NAV_ITEMS]


def _go(key, *content):
    return (gr.Tabs(selected=key), *content, *_nav_updates(key))


def go_dashboard(store):
    return _go("dashboard", views.render_dashboard(store))


def go_interview():
    return _go("interview")


def go_history(store):
    rows, message = refresh_history(store)
    return _go("history", rows, message)


def go_performance(store):
    return _go("performance", views.render_performance(store))


def go_profile():
    return _go("profile")


def go_settings(store):
    return _go("settings", account_info(store))


# =====================================================================
# SCREEN
# =====================================================================
THEME_LABELS = ["Dark Neon", "Light", "Midnight Blue"]

# runs in the browser: switch the theme and remember it
THEME_JS = """(t) => {
    const map = {"Dark Neon": "dark-neon", "Light": "light", "Midnight Blue": "midnight"};
    const v = map[t] || "dark-neon";
    document.documentElement.setAttribute("data-theme", v);
    try { localStorage.setItem("vic-theme", v); } catch (e) {}
}"""

# runs in the browser when the page opens: restore the theme, add the 3D background movement
LOAD_JS = """() => {
    const labels = {"dark-neon": "Dark Neon", "light": "Light", "midnight": "Midnight Blue"};
    let v = "dark-neon";
    try { v = localStorage.getItem("vic-theme") || "dark-neon"; } catch (e) {}
    if (!labels[v]) v = "dark-neon";
    document.documentElement.setAttribute("data-theme", v);
    const calm = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!window.__vicParallax && !calm) {
        window.__vicParallax = true;
        // only the background shapes move with the mouse; the login card stays still
        document.addEventListener("mousemove", (e) => {
            const root = document.documentElement.style;
            root.setProperty("--mx", (e.clientX / window.innerWidth - 0.5).toFixed(3));
            root.setProperty("--my", (e.clientY / window.innerHeight - 0.5).toFixed(3));
        });
    }
    return labels[v];
}"""

BG3D = """<div class="bg3d"><div class="shape s1"></div><div class="shape s2"></div>
<div class="shape s3"></div><div class="shape s4"></div></div>"""

ORB = '<div class="orb3d"><div class="ring"></div><div class="core"></div></div>'

with gr.Blocks(title="Voice Interview Coach") as demo:

    store = gr.State(None)    # signed-in user, their history and profile
    session = gr.State(None)  # the interview in progress

    # ---------------- LOGIN (centred, 3D) ----------------
    with gr.Column(elem_id="login-page") as login_view:
        gr.HTML(BG3D)
        with gr.Column(elem_id="login-card"):
            gr.HTML(f"""<div class="login-head">{ORB}
                <h1>Voice Interview Coach</h1>
                <p>Practise interviews in English, Hinglish and Kannada</p></div>""")
            with gr.Tabs():
                with gr.Tab("Sign in"):
                    li_email = gr.Textbox(label="Email", placeholder="you@example.com", max_lines=1)
                    li_pw = gr.Textbox(label="Password", type="password", max_lines=1)
                    li_btn = gr.Button("Sign in →", variant="primary")
                with gr.Tab("Create account"):
                    su_name = gr.Textbox(label="Your name", placeholder="e.g. Veena", max_lines=1)
                    su_email = gr.Textbox(label="Email", placeholder="you@example.com", max_lines=1)
                    su_pw = gr.Textbox(label="Password (at least 8 characters)", type="password",
                                       max_lines=1)
                    su_pw2 = gr.Textbox(label="Confirm password", type="password", max_lines=1)
                    su_btn = gr.Button("Create account →", variant="primary")
            gr.HTML('<div class="or-line">or</div>')
            guest_btn = gr.Button("Continue as guest")
            gr.HTML('<div class="small-note">Accounts are stored on this computer. Passwords are '
                    'saved as secure hashes, never as plain text. There is no email verification '
                    'or password reset. Guests are not saved.</div>')

    # ---------------- MAIN APP (full width) ----------------
    with gr.Row(visible=False) as main_view:

        with gr.Column(scale=1, min_width=290, elem_id="sidebar"):
            gr.HTML('<div id="brand">◈ VOICE AI</div>')
            user_chip = gr.HTML("")
            gr.HTML('<div class="nav-label">MENU</div>')
            nav_btns = [gr.Button(label, size="lg",
                                  elem_classes=["nav-btn", "active"] if key == "dashboard" else ["nav-btn"])
                        for key, label in NAV_ITEMS]
            gr.HTML('<div class="nav-label">ACCOUNT</div>')
            signout_btn = gr.Button("↩  Sign out", size="lg", elem_classes=["nav-btn", "signout"])

        with gr.Column(scale=5):
            with gr.Tabs(selected="dashboard", elem_id="main-tabs") as tabs:

                # ---- Dashboard ----
                with gr.Tab("🏠 Dashboard", id="dashboard"):
                    gr.HTML("""
                    <div id="hero">
                        <p>YOUR PERSONAL AI INTERVIEW PARTNER</p>
                        <h1>Practice smarter.<br><span>Interview better.</span></h1>
                    </div>""")
                    gr.HTML('<h1 class="page-title">🏠 Dashboard</h1>')
                    dash_html = gr.HTML("")
                    go_btn = gr.Button("✦ Start a new interview", variant="primary")

                # ---- New Interview ----
                with gr.Tab("🎙️ New Interview", id="interview"):
                    gr.HTML('<h1 class="page-title">🎙️ New Interview</h1><p class="page-sub">Set up your interview, then answer each question by voice.</p>')
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
                    use_profile = gr.Checkbox(
                        value=True,
                        label="Use my profile (resume / GitHub / LinkedIn from the Profile tab) "
                              "to personalise the questions")
                    start_btn = gr.Button("✦ Start Interview", variant="primary")

                    gr.Markdown("### 2. Listen and answer")
                    progress = gr.Markdown(views.progress(None))
                    status = gr.Markdown("")
                    gr.HTML(f'<div class="orb-box">{ORB}<h3>AI Interview Coach</h3></div>')
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
                with gr.Tab("🕘 History", id="history"):
                    gr.HTML('<h1 class="page-title">🕘 History</h1><p class="page-sub">Your past interviews. Click a row to open it.</p>')

                    hist_df = gr.Dataframe(headers=views.HISTORY_HEADERS, value=[],
                                           interactive=False, wrap=True)
                    hist_detail = gr.Markdown("*Click a row to see the full interview.*")
                    clear_btn = gr.Button("🗑 Clear history")

                # ---- Performance ----
                with gr.Tab("📊 Performance", id="performance"):
                    gr.HTML('<h1 class="page-title">📊 Performance</h1><p class="page-sub">How your latest interview went.</p>')
                    perf_html = gr.HTML("")

                # ---- Profile & Resume ----
                with gr.Tab("👤 Profile & Resume", id="profile"):
                    gr.HTML('<h1 class="page-title">👤 Profile & Resume</h1><p class="page-sub">Help the coach ask about your own projects.</p>')
                    gr.Markdown(
                        "Add your resume and public profiles. The coach uses them to ask about "
                        "**your** projects and skills, and gives tips to improve your resume.\n\n"
                        "🔒 **Privacy:** your PDF is read in memory and then deleted. Email "
                        "addresses and phone numbers are removed before anything goes to the AI. "
                        "Only a short summary is kept, for this session only.")
                    p_role = gr.Dropdown(choices=ROLES, value=ROLES[0], allow_custom_value=True,
                                         label="Role you are preparing for")
                    resume_file = gr.File(label="Resume (PDF, up to 5 MB)", file_types=[".pdf"],
                                          file_count="single", type="filepath")
                    github_box = gr.Textbox(
                        label="GitHub username or link (public repositories only)",
                        placeholder="e.g. octocat or https://github.com/octocat", max_lines=1)
                    linkedin_box = gr.Textbox(
                        label="LinkedIn: paste your About and Experience text",
                        info="LinkedIn does not allow apps to read profiles automatically, "
                             "so please copy and paste the text yourself.",
                        lines=5, max_lines=10)
                    with gr.Row():
                        analyse_btn = gr.Button("✨ Analyse my profile", variant="primary", scale=3)
                        remove_btn = gr.Button("Remove profile", scale=1)
                    profile_status = gr.Markdown("")
                    profile_html = gr.HTML("")

                # ---- Settings ----
                with gr.Tab("⚙️ Settings", id="settings"):
                    gr.HTML('<h1 class="page-title">⚙️ Settings</h1><p class="page-sub">Theme, voice and account.</p>')
                    gr.Markdown("### Appearance")
                    theme_radio = gr.Radio(THEME_LABELS, value="Dark Neon", label="Colour theme")
                    gr.Markdown("### Voice")
                    speed = gr.Slider(config.MIN_SPEED, config.MAX_SPEED,
                                      value=config.DEFAULT_SPEED, step=0.1,
                                      label="Coach speaking speed (1.0 = normal)")
                    gr.Markdown(
                        "Voices in use (change them in your `.env` file): "
                        + ", ".join(f"**{k}**: {v}" for k, v in config.VOICES.items()))
                    gr.Markdown("### Account")
                    account_md = gr.Markdown("")
                    delete_chk = gr.Checkbox(
                        label="I understand this permanently deletes my account and saved interviews")
                    delete_btn = gr.Button("Delete my account")

    # ---------------- EVENTS ----------------
    enter_out = [store, login_view, main_view, user_chip, dash_html, tabs, li_pw, su_pw, su_pw2] + nav_btns
    signout_out = [store, session, login_view, main_view, log_box, coach_audio, heard_box,
                   progress, status, score_md, profile_html, profile_status]
    session_out = [store, session, log_box, coach_audio, heard_box, progress,
                   status, score_md, mic]

    li_btn.click(sign_in_email, [li_email, li_pw], enter_out, show_progress="hidden")
    li_pw.submit(sign_in_email, [li_email, li_pw], enter_out, show_progress="hidden")
    su_btn.click(sign_up, [su_name, su_email, su_pw, su_pw2], enter_out, show_progress="hidden")
    su_pw2.submit(sign_up, [su_name, su_email, su_pw, su_pw2], enter_out, show_progress="hidden")
    guest_btn.click(sign_in_guest, None, enter_out, show_progress="hidden")
    signout_btn.click(sign_out, None, signout_out, show_progress="hidden")
    delete_btn.click(delete_account, [delete_chk, store], signout_out + [delete_chk], show_progress="hidden")

    nav_dash, nav_int, nav_hist, nav_perf, nav_prof, nav_set = nav_btns
    nav_dash.click(go_dashboard, [store], [tabs, dash_html] + nav_btns)
    nav_int.click(go_interview, None, [tabs] + nav_btns)
    nav_hist.click(go_history, [store], [tabs, hist_df, hist_detail] + nav_btns)
    nav_perf.click(go_performance, [store], [tabs, perf_html] + nav_btns)
    nav_prof.click(go_profile, None, [tabs] + nav_btns)
    nav_set.click(go_settings, [store], [tabs, account_md] + nav_btns)
    go_btn.click(go_interview, None, [tabs] + nav_btns)
    hist_df.select(show_record, [store], [hist_detail])
    clear_btn.click(clear_history, [store], [store, hist_df, hist_detail])

    mic.change(mic_status, [mic], [mic_msg])
    start_btn.click(start_interview,
                    [lang, role, category, difficulty, total, speed, use_profile, store, session],
                    session_out)
    send_btn.click(send_answer, [mic, speed, store, session], session_out)
    end_btn.click(end_interview, [store, session], [store, session, progress, status])

    analyse_btn.click(analyse_profile, [p_role, resume_file, github_box, linkedin_box, store],
                      [store, profile_html, profile_status, resume_file])
    remove_btn.click(remove_profile, [store],
                     [store, profile_html, profile_status, resume_file, github_box, linkedin_box])

    theme_radio.change(None, [theme_radio], None, js=THEME_JS)
    demo.load(None, None, [theme_radio], js=LOAD_JS)


if __name__ == "__main__":
    demo.launch(
        theme=gr.themes.Base(primary_hue="green", neutral_hue="slate"),
        css=CUSTOM_CSS,
    )