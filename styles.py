"""Themes and styling. Pure CSS: every colour is a variable, so the theme switcher
in Settings only has to change data-theme on the page."""

CUSTOM_CSS = """
/* =============================== THEMES =============================== */
:root, html[data-theme="dark-neon"] {
    --bg:#080B0A; --card:#101713; --card-2:#121A15; --border:#243329; --border-soft:#1A241E;
    --text:#FFFFFF; --muted:#A7B5AA; --accent:#39FF14; --accent-2:#00C853; --on-accent:#071007;
    --glow:rgba(57,255,20,.10); --glow-strong:rgba(57,255,20,.45);
    --good:#39FF14; --warn:#FFC107; --bad:#FF5252;
    --input:#111A14; --input-border:#304536; --hero-a:#14251A; --hero-b:#0B100D;
    --shadow:rgba(0,0,0,.55); color-scheme: dark;
}
html[data-theme="light"] {
    --bg:#F1F6F3; --card:#FFFFFF; --card-2:#F7FBF8; --border:#D3E0D8; --border-soft:#E4EDE7;
    --text:#0E1A13; --muted:#56665D; --accent:#00A63E; --accent-2:#008A33; --on-accent:#FFFFFF;
    --glow:rgba(0,166,62,.10); --glow-strong:rgba(0,166,62,.30);
    --good:#00A63E; --warn:#C77700; --bad:#D93025;
    --input:#FFFFFF; --input-border:#C5D5CB; --hero-a:#E3F4E9; --hero-b:#F6FBF8;
    --shadow:rgba(20,50,30,.18); color-scheme: light;
}
html[data-theme="midnight"] {
    --bg:#060B18; --card:#0D1630; --card-2:#101B3A; --border:#1F2F5C; --border-soft:#16224A;
    --text:#EAF0FF; --muted:#9AA9CF; --accent:#4C8DFF; --accent-2:#2F6FE0; --on-accent:#04102A;
    --glow:rgba(76,141,255,.14); --glow-strong:rgba(76,141,255,.50);
    --good:#3DDC97; --warn:#FFC24B; --bad:#FF6B6B;
    --input:#0B1430; --input-border:#2A3C70; --hero-a:#122250; --hero-b:#0A1228;
    --shadow:rgba(0,0,0,.60); color-scheme: dark;
}

/* ===== tell every Gradio component to use the theme colours ===== */
:root, .gradio-container, .dark {
    --body-background-fill: var(--bg);
    --background-fill-primary: var(--card);
    --background-fill-secondary: var(--card-2);
    --block-background-fill: var(--card);
    --block-border-color: var(--border);
    --block-label-background-fill: var(--card);
    --block-label-text-color: var(--muted);
    --block-title-text-color: var(--text);
    --panel-background-fill: var(--card);
    --body-text-color: var(--text);
    --body-text-color-subdued: var(--muted);
    --input-background-fill: var(--input);
    --input-border-color: var(--input-border);
    --border-color-primary: var(--border);
    --table-even-background-fill: var(--card);
    --table-odd-background-fill: var(--card-2);
    --table-border-color: var(--border);
    --table-text-color: var(--text);
    --button-secondary-background-fill: var(--card-2);
    --button-secondary-background-fill-hover: var(--border-soft);
    --button-secondary-text-color: var(--text);
    --button-secondary-border-color: var(--border);
    --button-primary-background-fill: var(--accent);
    --button-primary-background-fill-hover: var(--accent-2);
    --button-primary-text-color: var(--on-accent);
    --color-accent: var(--accent);
    --color-accent-soft: var(--glow);
    --slider-color: var(--accent);
    --checkbox-background-color-selected: var(--accent);
    --checkbox-label-text-color: var(--text);
    --link-text-color: var(--accent);
    --neutral-500: var(--muted);
}

/* ===== FULL SCREEN: no maximum width, one background everywhere ===== */
html, body { background: var(--bg) !important; min-height: 100%; }
gradio-app, .app, .main, .gradio-container { background: transparent !important; }
.gradio-container {
    width: 100% !important;
    max-width: 100% !important;
    padding: 14px 26px !important;
    color: var(--text) !important;
    font-family: 'Inter', 'Segoe UI', system-ui, -apple-system, Roboto, sans-serif !important;
    position: relative; z-index: 1;
}
body::before {
    content: ""; position: fixed; inset: 0; pointer-events: none; z-index: 0;
    background:
        radial-gradient(900px 520px at 88% -8%, var(--glow), transparent 62%),
        radial-gradient(760px 460px at -8% 108%, var(--glow), transparent 62%);
}
footer { display: none !important; }

/* ===== sidebar navigation ===== */
#main-tabs .tab-wrapper, #main-tabs > div[role="tablist"] { display: none !important; }
#sidebar { padding: 24px 18px !important; gap: 6px !important; }
#brand { font-size: 30px !important; margin-bottom: 18px !important; }
.user-card { display: flex; align-items: center; gap: 12px; background: var(--card-2);
             border: 1px solid var(--border); border-radius: 14px; padding: 12px 14px; }
.avatar { width: 46px; height: 46px; flex: none; border-radius: 50%; display: grid; place-items: center;
          font-size: 21px; font-weight: 800; color: var(--on-accent);
          background: linear-gradient(135deg, var(--accent), var(--accent-2));
          box-shadow: 0 0 16px var(--glow-strong); }
.user-text { color: var(--text); line-height: 1.35; font-size: 16px; overflow: hidden; }
.user-text small { color: var(--muted); font-size: 12.5px; word-break: break-all; }
.user-note { color: var(--muted); font-size: 12px; margin: 8px 4px 0; }
.nav-label { color: var(--muted); font-size: 12px; font-weight: 700; letter-spacing: 2px; margin: 18px 6px 4px; }
button.nav-btn {
    width: 100%; justify-content: flex-start !important; text-align: left !important;
    font-size: 18px !important; font-weight: 600 !important; padding: 15px 18px !important;
    background: transparent !important; color: var(--text) !important;
    border: 1px solid transparent !important; border-radius: 14px !important;
}
button.nav-btn:hover { background: var(--card-2) !important; border-color: var(--border) !important;
                       transform: translateX(4px); }
button.nav-btn.active {
    background: var(--glow) !important; border-color: var(--accent) !important;
    color: var(--accent) !important; box-shadow: inset 5px 0 0 var(--accent);
}
button.nav-btn.signout { color: var(--muted) !important; }
.page-title { font-size: 36px; font-weight: 800; color: var(--text); margin: 4px 0 2px; }
.page-sub { font-size: 16px; color: var(--muted); margin: 0 0 18px; }

/* inline code such as .env readable in every theme */
.gradio-container code, .gradio-container .prose code {
    background: var(--card-2) !important; color: var(--accent) !important;
    border: 1px solid var(--border); border-radius: 6px; padding: 1px 6px;
}

/* ===== layout pieces ===== */
#sidebar {
    background: var(--card); border: 1px solid var(--border); border-radius: 18px;
    padding: 20px; position: sticky; top: 14px; align-self: flex-start; height: fit-content;
}
#brand { color: var(--accent); font-size: 25px; font-weight: 800; margin-bottom: 20px; }
#hero {
    background: linear-gradient(135deg, var(--hero-a), var(--hero-b));
    border: 1px solid var(--border); border-radius: 20px; padding: 26px 30px; margin-bottom: 18px;
}
#hero h1 { font-size: 34px; color: var(--text); font-weight: 800; margin: 6px 0 0; }
#hero span { color: var(--accent); }
#hero p { color: var(--muted); font-size: 14px; margin: 0; letter-spacing: .5px; }

.stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
             gap: 14px; margin-bottom: 22px; }
.stat-card {
    background: var(--card-2); border: 1px solid var(--border); border-radius: 15px;
    padding: 20px; text-align: center; transition: transform .2s ease, box-shadow .2s ease;
}
.stat-card:hover { transform: translateY(-4px); box-shadow: 0 10px 26px -8px var(--glow-strong); }
.stat-card h2 { color: var(--accent); font-size: 27px; margin: 0 0 4px; }
.stat-card p { color: var(--muted); margin: 0; }
.section-title { color: var(--accent); font-size: 20px; font-weight: 700; margin: 18px 0 8px; }
.dash-hello { font-size: 24px; font-weight: 800; color: var(--text); margin-bottom: 14px; }
.profile-ready {
    border: 1px solid var(--accent); color: var(--accent); background: var(--glow);
    border-radius: 12px; padding: 10px 14px; margin-bottom: 16px; font-weight: 600;
}

/* ===== buttons, inputs, tabs ===== */
button { border-radius: 10px !important; transition: transform .15s ease, box-shadow .15s ease !important; }
button.primary { font-weight: 700 !important; border: none !important; }
button.primary:hover { box-shadow: 0 6px 20px -4px var(--glow-strong) !important; transform: translateY(-1px); }
input, textarea, select { color: var(--text) !important; }
button[role="tab"] { color: var(--muted) !important; font-weight: 600 !important; }
button[role="tab"][aria-selected="true"] { color: var(--accent) !important; border-color: var(--accent) !important; }

/* ===== dashboard / history / performance ===== */
.user-chip {
    background: var(--card-2); border: 1px solid var(--border); border-radius: 12px;
    padding: 12px; color: var(--text); margin-bottom: 12px; line-height: 1.5;
}
.user-chip small { color: var(--muted); }
.dot { display: inline-block; width: 9px; height: 9px; border-radius: 50%;
       background: var(--accent); box-shadow: 0 0 8px var(--accent); margin-right: 4px; }
.recent-row {
    display: flex; justify-content: space-between; align-items: center; gap: 12px;
    background: var(--card-2); border: 1px solid var(--border); border-radius: 12px;
    padding: 12px 16px; margin-bottom: 8px; color: var(--text);
}
.recent-row small { color: var(--muted); }
.pill { border: 1px solid; border-radius: 999px; padding: 4px 14px; font-weight: 700; white-space: nowrap; }
.empty { background: var(--card); border: 1px dashed var(--input-border); border-radius: 14px;
         padding: 24px; color: var(--muted); text-align: center; }
.trend { display: flex; align-items: flex-end; gap: 12px; height: 140px; padding-top: 10px; }
.trend-col { flex: 1; max-width: 60px; height: 100%; display: flex; flex-direction: column;
             justify-content: flex-end; align-items: center; color: var(--muted); }
.trend-bar { width: 100%; border-radius: 8px 8px 0 0; min-height: 4px; }
.bar-row { display: flex; align-items: center; gap: 12px; margin: 8px 0; color: var(--text); }
.bar-row span:first-child { width: 32px; }
.bar-row span:last-child { width: 56px; text-align: right; }
.bar { flex: 1; height: 14px; background: var(--border-soft); border-radius: 999px; overflow: hidden; }
.bar > div { height: 100%; border-radius: 999px; }
.note { color: var(--muted); font-size: 13px; margin-top: 14px; }

/* ===== profile ===== */
.chip { display: inline-block; padding: 4px 12px; margin: 3px; border: 1px solid var(--accent);
        border-radius: 999px; color: var(--accent); font-size: 13px; font-weight: 600; }
.proj { padding: 10px 14px; margin: 6px 0; border: 1px solid var(--border);
        background: var(--card-2); border-radius: 12px; color: var(--text); }
.proj small { color: var(--muted); }
.tips li { margin: 8px 0; color: var(--text); }
.profile-card { color: var(--text); }

/* ===== AI orb (interview screen) ===== */
.orb-box {
    background: radial-gradient(circle, var(--glow), transparent 70%), var(--card);
    border: 1px solid var(--accent); border-radius: 18px; padding: 18px; text-align: center; margin: 10px 0;
}
.orb-box h3 { color: var(--accent); margin: 10px 0 0; }

/* ===== 3D ORB (used on the login page and the interview screen) ===== */
.orb3d { position: relative; width: 72px; height: 72px; margin: 0 auto; }
.orb3d .core {
    position: absolute; inset: 6px; border-radius: 50%;
    background: radial-gradient(circle at 34% 28%, rgba(255,255,255,.85), var(--accent) 32%, var(--accent-2) 70%, #000 140%);
    box-shadow: 0 0 34px var(--glow-strong), inset -8px -10px 18px rgba(0,0,0,.35);
    animation: bob 3.2s ease-in-out infinite;
}
.orb3d .ring {
    position: absolute; inset: -6px; border-radius: 50%;
    border: 2px solid transparent; border-top-color: var(--accent); border-bottom-color: var(--accent-2);
    animation: spin 3.4s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
@keyframes bob { 0%,100% { transform: translateY(0) scale(1); } 50% { transform: translateY(-4px) scale(1.06); } }

/* =============================== LOGIN PAGE =============================== */
#login-page {
    min-height: 92vh; display: flex !important; flex-direction: column;
    align-items: center; justify-content: center; gap: 0 !important;
    position: relative; perspective: 1300px; border: none !important; background: transparent !important;
}
.bg3d { position: fixed; inset: 0; pointer-events: none; z-index: 0; overflow: hidden; perspective: 900px; }
.shape {
    position: absolute; border: 1px solid var(--accent); border-radius: 26px; opacity: .38;
    background: linear-gradient(135deg, var(--glow-strong), transparent 72%);
    animation: floaty 15s ease-in-out infinite; transform-style: preserve-3d;
    translate: calc(var(--mx, 0) * var(--depth, 40) * 1px) calc(var(--my, 0) * var(--depth, 40) * 0.7px);
    transition: translate .35s ease-out;
}
.shape.s1 { width: 190px; height: 190px; left: 7%;  top: 14%; --depth: 46; }
.shape.s2 { width: 120px; height: 120px; right: 9%; top: 20%; animation-delay: -5s; --depth: -34; }
.shape.s3 { width: 250px; height: 250px; right: 15%; bottom: 6%; border-radius: 50%; animation-delay: -9s; --depth: -56; }
.shape.s4 { width: 90px;  height: 90px;  left: 17%; bottom: 13%; animation-delay: -3s; --depth: 28; }
@keyframes floaty {
    0%,100% { transform: translateY(0) rotateX(58deg) rotateZ(18deg); }
    50%     { transform: translateY(-30px) rotateX(66deg) rotateZ(52deg); }
}
#login-card {
    width: min(480px, 92vw) !important; max-width: 480px !important; min-width: 0 !important;
    flex: none !important; position: relative; z-index: 2;
    background: var(--card) !important; border: 1px solid var(--border) !important; border-radius: 24px !important;
    padding: 28px 30px !important;
    transform: rotateX(2deg) rotateY(-3deg);
    box-shadow: 0 40px 70px -30px var(--shadow), 0 0 0 1px var(--border-soft), 0 0 60px -10px var(--glow-strong);
}
/* a leftover loading overlay must never block the login form */
#login-page [data-testid="status-tracker"] { pointer-events: none !important; }
.login-head { text-align: center; margin-bottom: 8px; }
.login-head h1 { color: var(--text); font-size: 28px; font-weight: 800; margin: 16px 0 4px; }
.login-head p { color: var(--muted); margin: 0; }
.or-line { text-align: center; color: var(--muted); font-size: 13px; margin: 6px 0; }
.small-note { color: var(--muted); font-size: 12.5px; text-align: center; }

@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { animation: none !important; transition: none !important; }
    #login-card { transform: none !important; }
    .shape { translate: none !important; }
}
@media (max-width: 800px) {
    .gradio-container { padding: 10px !important; }
    #sidebar { position: static; }
}

.shape { translate: none !important; }
}

@media (max-width: 800px) {
    .gradio-container { padding: 10px !important; }
    #sidebar { position: static; }
}

/* Neon green primary buttons */
.gradio-container button.primary {
    background: #39FF14 !important;
    border-color: #39FF14 !important;
    color: #080B0A !important;
}

.gradio-container button.primary:hover {
    background: #32E600 !important;
    border-color: #32E600 !important;
}

/* Neon green active tabs */
.tab-nav button.selected,
.tab-nav button[aria-selected="true"] {
    color: #39FF14 !important;
    border-bottom-color: #39FF14 !important;
}
"""