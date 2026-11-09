"""Builds the HTML / text shown in the Dashboard, History and Performance tabs."""
import html

import interview


def _e(value):
    return html.escape(str(value))


def _fmt(score):
    return "—" if score is None else f"{score:g}"


def score_color(score):
    if score is None:
        return "var(--muted)"
    if score >= 8:
        return "var(--good)"
    if score >= 5:
        return "var(--warn)"
    return "var(--bad)"


def user_chip(name, email=None):
    """Avatar card at the top of the sidebar."""
    initial = _e((name or "?").strip()[:1].upper() or "?")
    sub = _e(email) if email else "Guest session"
    note = ("Your interviews are saved to your account." if email
            else "Nothing is saved after you close this page.")
    return (f'<div class="user-card"><div class="avatar">{initial}</div>'
            f'<div class="user-text"><b>{_e(name)}</b><br><small>{sub}</small></div></div>'
            f'<div class="user-note">{note}</div>')


def progress(session):
    if not session:
        return "Set up your interview and click **Start Interview**."
    total = session["settings"]["total"]
    if session["finished"]:
        return (f"✅ **Interview finished.** You answered "
                f"{interview.answered_count(session)} of {total} questions.")
    return f"📝 **Question {session['asked']} of {total}**"


def score_line(score):
    if score is None:
        return ""
    return (f"⭐ **Your last answer: {score}/10** "
            f"*(AI estimate based on your words, not your voice)*")


def render_dashboard(store):
    if not store:
        return ""
    history = store["history"]
    st = interview.overall_stats(history)
    cards = (
        f'<div class="stat-grid">'
        f'<div class="stat-card"><h2>{st["interviews"]}</h2><p>Interviews</p></div>'
        f'<div class="stat-card"><h2>{st["questions"]}</h2><p>Questions answered</p></div>'
        f'<div class="stat-card"><h2>{_fmt(st["avg"])}</h2><p>Average score</p></div>'
        f'<div class="stat-card"><h2>{_fmt(st["best"])}</h2><p>Best score</p></div>'
        f'</div>'
    )
    if not history:
        body = ('<div class="empty">No interviews yet. Click <b>Start a new interview</b> '
                'below to take your first one.</div>')
    else:
        rows = "".join(
            f'<div class="recent-row"><div><b>{_e(r["role"])}</b><br>'
            f'<small>{_e(r["date"])} · {_e(r["category"])} · {_e(r["lang"])}</small></div>'
            f'<span class="pill" style="color:{score_color(r["avg"])};'
            f'border-color:{score_color(r["avg"])}">{_fmt(r["avg"])}/10</span></div>'
            for r in reversed(history[-5:]))
        trend = "".join(
            f'<div class="trend-col"><div class="trend-bar" '
            f'style="height:{(r["avg"] or 0) * 10}%;background:{score_color(r["avg"])}"></div>'
            f'<small>{_fmt(r["avg"])}</small></div>'
            for r in history[-8:])
        body = (f'<h3 class="section-title">Recent interviews</h3>{rows}'
                f'<h3 class="section-title">Score trend</h3><div class="trend">{trend}</div>')
    ready = ""
    if store.get("profile"):
        ready = ('<div class="profile-ready">✅ Profile ready: '
                 + _e(", ".join(store["profile"]["sources"]))
                 + '. Your interview questions can use it.</div>')
    return (f'<div class="dash-hello">Welcome, {_e(store["name"])} 👋</div>{ready}{cards}{body}')


# ---------------------------------------------------------------- history
HISTORY_HEADERS = ["#", "Date", "Role", "Type", "Level", "Language", "Done", "Score"]


def history_rows(store):
    """Newest first. The table row number maps to reversed(history)."""
    rows = []
    for r in reversed(store["history"] if store else []):
        rows.append([r["id"], r["date"], r["role"], r["category"], r["difficulty"],
                     r["lang"], f'{len(r["answers"])}/{r["total"]}', _fmt(r["avg"])])
    return rows


def record_markdown(record):
    lines = [
        f"### {record['role']}",
        f"{record['date']} · {record['category']} · {record['difficulty']} · {record['lang']}",
        f"**Average score: {_fmt(record['avg'])}/10** "
        f"({'completed' if record['complete'] else 'ended early'})",
        "*Scores are AI estimates based on your words only.*",
        "---",
    ]
    for i, a in enumerate(record["answers"], 1):
        lines += [
            f"**Q{i}. {a['question']}**",
            f"> {a['answer']}",
            f"Score: **{_fmt(a['score'])}/10**" + (f" · {a['feedback']}" if a["feedback"] else ""),
            "",
        ]
    return "\n\n".join(lines)


def record_by_row(store, row):
    history = list(reversed(store["history"])) if store else []
    return history[row] if 0 <= row < len(history) else None


# ---------------------------------------------------------------- performance
def render_performance(store):
    if not store or not store["history"]:
        return '<div class="empty">Finish or end an interview to see your performance here.</div>'
    r = store["history"][-1]
    bars = "".join(
        f'<div class="bar-row"><span>Q{i}</span><div class="bar"><div '
        f'style="width:{(a["score"] or 0) * 10}%;background:{score_color(a["score"])}"></div>'
        f'</div><span>{_fmt(a["score"])}/10</span></div>'
        for i, a in enumerate(r["answers"], 1))
    scores = [a["score"] for a in r["answers"] if a["score"] is not None]
    if scores:
        best = max(r["answers"], key=lambda a: a["score"] or 0)
        worst = min((a for a in r["answers"] if a["score"] is not None), key=lambda a: a["score"])
        notes = (f'<p><b>Strongest answer:</b> {_e(best["question"])} ({best["score"]}/10)</p>'
                 f'<p><b>Needs most work:</b> {_e(worst["question"])} ({worst["score"]}/10)</p>')
    else:
        notes = ""
    return (f'<h3 class="section-title">Latest interview: {_e(r["role"])}</h3>'
            f'<p>{_e(r["date"])} · average <b>{_fmt(r["avg"])}/10</b></p>{bars}{notes}'
            f'<p class="note">Scores are AI estimates based on what you said. '
            f'They do not measure your voice, tone, confidence or body language.</p>')


# ---------------------------------------------------------------- profile
def render_profile(analysis, sources):
    """Show the analysed profile. Everything is escaped: it came from user files and an LLM."""
    chips = "".join(f'<span class="chip">{_e(x)}</span>' for x in analysis["skills"]) or "<i>none found</i>"
    projects = "".join(
        f'<div class="proj"><b>{_e(p["name"])}</b>'
        + (f'<br><small>{_e(p["summary"])}</small>' if p["summary"] else "") + "</div>"
        for p in analysis["projects"]) or "<i>none found</i>"
    tips = "".join(f"<li>{_e(t)}</li>" for t in analysis["tips"]) or "<li>No tips returned.</li>"
    return (
        f'<div class="profile-card">'
        f'<p class="note">Built from: {_e(", ".join(sources))}</p>'
        f'<h3 class="section-title">Skills</h3><div>{chips}</div>'
        f'<h3 class="section-title">Projects</h3>{projects}'
        f'<h3 class="section-title">Education</h3><p>{_e(analysis["education"]) or "<i>not found</i>"}</p>'
        f'<h3 class="section-title">Experience</h3><p>{_e(analysis["experience"]) or "<i>not found</i>"}</p>'
        f'<h3 class="section-title">How to improve your resume and profile</h3><ul class="tips">{tips}</ul>'
        f'<p class="note">These suggestions are AI-generated from the information you gave. '
        f'Check them before you change anything.</p></div>')