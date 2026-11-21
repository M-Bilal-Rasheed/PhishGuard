"""PhishGuard web app (Streamlit Cloud).

Run locally:  streamlit run streamlit_app.py
The URL is only analysed as text; the app never opens or fetches it.
"""
import html
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from predictor import InvalidURL, PhishGuard  # noqa: E402

EXAMPLES = {
    "Meezan Bank": "https://www.meezanbank.com",
    "Daraz": "https://www.daraz.pk/products/samsung-galaxy",
    "Fake bank login": "http://meezan-bank-login.firebaseapp.com/verify",
    "Fake PayPal": "http://paypal.com@192.168.10.5/secure/update-account",
}

# One 3-colour combination (60-30-10 rule): black background ~60%, dark-green cards ~30%,
# bright emerald ~10% for actions and highlights. Red and amber appear only for phishing / invalid verdicts.
COLOURS = {"bg": "#070b09", "card": "#0f2219", "card2": "#163626", "brand": "#2ee07f"}

ICON_SHIELD = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
               'stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>'
               '<path d="m9 12 2 2 4-4"/></svg>')
ICON_SAFE = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" '
             'stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path class="pg-draw" d="m7.5 12.5 3 3 6-6.5"/></svg>')
ICON_DANGER = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" '
               'stroke-linejoin="round"><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/>'
               '<path d="M12 9v4"/><path d="M12 17h.01"/></svg>')
ICON_WARN = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" '
             'stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 8v4"/><path d="M12 16h.01"/></svg>')

CSS = """
<style>
@property --p { syntax: '<integer>'; inherits: false; initial-value: 0; }
:root { --bg: %(bg)s; --card: %(card)s; --card2: %(card2)s; --brand: %(brand)s; --accent: %(brand)s; --deep: %(card)s;
        --ink: #e9f5ee; --muted: #8fab9b; --line: #1f4231; --safe: %(brand)s; --danger: #ff5a4e; --warn: #f5b83d; }
.stApp { background: radial-gradient(900px 500px at 50%% -10%%, #0d2a1c 0%%, var(--bg) 60%%) fixed, var(--bg); color: var(--ink); }
.block-container { max-width: 1180px; padding-top: 1.4rem; padding-bottom: 2rem; }
/* left panel = bordered st.container */
.st-key-check_panel {
           background: var(--card); border: 1px solid var(--line) !important; border-radius: 20px !important; padding: 22px !important;
           animation: pg-rise .7s ease .1s both; }
.pg-panel-title { font-size: 1.15rem !important; font-weight: 800; color: var(--ink); margin: 2px 0 2px; }
.pg-panel-sub { color: var(--muted); font-size: .88rem !important; margin: 0 0 4px; }
/* empty result placeholder */
.pg-empty { border-radius: 20px; border: 2px dashed var(--line); background: color-mix(in srgb, var(--card) 55%%, transparent);
           min-height: 330px; display: flex; flex-direction: column; align-items: center; justify-content: center;
           text-align: center; padding: 28px; color: var(--muted); animation: pg-rise .7s ease .2s both; }
.pg-empty svg { width: 54px; height: 54px; color: var(--brand); opacity: .55; margin-bottom: 14px; animation: pg-breathe 2.6s ease-in-out infinite; }
.pg-empty b { color: var(--ink); font-size: 1.1rem; display: block; margin-bottom: 6px; }
@keyframes pg-breathe { 50%% { transform: scale(1.08); opacity: .9; } }
header[data-testid="stHeader"] { display: none; }

/* hero */
.pg-hero { position: relative; overflow: hidden; border-radius: 22px; padding: 22px 28px; margin-bottom: 18px;
           display: flex; align-items: center; justify-content: space-between; gap: 24px; flex-wrap: wrap; color: #fff;
           background: linear-gradient(135deg, var(--card) 0%%, var(--card2) 100%%); border: 1px solid var(--line);
           box-shadow: 0 24px 60px -30px var(--brand); animation: pg-rise .7s ease both; }
.pg-hero::before, .pg-hero::after { content: ""; position: absolute; border-radius: 50%%; background: var(--accent); }
.pg-hero::before { width: 240px; height: 240px; right: -70px; top: -90px; opacity: .16; filter: blur(2px); animation: pg-float 7s ease-in-out infinite; }
.pg-hero::after { width: 120px; height: 120px; right: 120px; bottom: -70px; opacity: .10; animation: pg-float 9s ease-in-out infinite reverse; }
.pg-brand { display: flex; align-items: center; gap: 14px; position: relative; z-index: 1; }
.pg-logo { width: 52px; height: 52px; border-radius: 15px; display: grid; place-items: center;
           background: color-mix(in srgb, var(--brand) 14%%, transparent); border: 1px solid color-mix(in srgb, var(--brand) 40%%, transparent); }
.pg-logo svg { width: 30px; height: 30px; color: var(--accent); }
.pg-title { font-size: 2rem !important; font-weight: 800; letter-spacing: -.02em; line-height: 1; margin: 0; color: #fff; }
.pg-tag { margin: 6px 0 0; opacity: .86; font-size: .98rem !important; }
.pg-lead { position: relative; z-index: 1; margin: 12px 0 0; font-size: 1.02rem !important; line-height: 1.55; opacity: .95; max-width: 560px; }
.pg-chips { position: relative; z-index: 1; display: flex; flex-wrap: wrap; gap: 8px; justify-content: flex-end; max-width: 340px; }
.pg-chip { padding: 6px 12px; border-radius: 999px; font-size: .82rem; font-weight: 600; color: var(--ink);
           background: rgba(0,0,0,.28); border: 1px solid var(--line); }
.pg-chip b { color: var(--accent); }

/* input area */
.pg-label { font-weight: 700; color: var(--ink); margin: 10px 0 0; font-size: .95rem; }
.pg-hint { color: var(--muted); font-size: .86rem; margin: 10px 0 4px; }
div[data-testid="stTextInput"] input { background: var(--card); color: var(--ink); caret-color: var(--brand); border-radius: 12px; padding: 14px 14px; font-size: 1rem; }
div[data-testid="stTextInput"] div[data-baseweb="input"], div[data-testid="stTextInput"] div[data-baseweb="base-input"] {
           border-radius: 14px; border: 2px solid var(--line); background: var(--card); transition: border-color .2s, box-shadow .2s; }
div[data-testid="stTextInput"] div[data-baseweb="input"]:focus-within { border-color: var(--brand);
           box-shadow: 0 0 0 4px color-mix(in srgb, var(--brand) 22%%, transparent), 0 0 24px -6px var(--brand); }
div[data-testid="stTextInput"] input::placeholder { color: var(--muted); opacity: .8; }
.stButton > button { border-radius: 999px; border: 1.5px solid color-mix(in srgb, var(--brand) 35%%, var(--line));
           color: var(--ink); background: var(--card); font-weight: 600; transition: all .2s ease; }
.stButton > button:hover { border-color: var(--brand); color: var(--brand); transform: translateY(-1px);
           box-shadow: 0 6px 16px -10px var(--brand); }
.stButton > button[kind="primary"], button[data-testid="stBaseButton-primary"] {
           background: var(--brand); color: #04140b; border: none;
           border-radius: 14px; padding: 12px 0; font-size: 1.05rem; font-weight: 700; }
button[data-testid="stBaseButton-primary"] p { font-weight: 800; font-size: 1.05rem; color: #04140b; }
.stButton > button[kind="primary"]:hover, button[data-testid="stBaseButton-primary"]:hover {
           color: #04140b; filter: brightness(1.08); box-shadow: 0 0 28px -4px var(--brand); }

/* result card */
.pg-result { margin-top: 0; border-radius: 20px; background: var(--card); border: 1px solid var(--line);
             box-shadow: 0 24px 50px -28px var(--tone, var(--brand)); overflow: hidden;
             animation: pg-pop .55s cubic-bezier(.2,.9,.3,1.25) both; }
.pg-result.danger { --tone: var(--danger); }
.pg-result.safe { --tone: var(--safe); }
.pg-result.warn { --tone: var(--warn); }
.pg-result.danger { animation: pg-pop .55s cubic-bezier(.2,.9,.3,1.25) both, pg-shake .5s ease .55s; }
.pg-top { display: flex; align-items: center; gap: 16px; padding: 22px 24px;
          background: linear-gradient(90deg, color-mix(in srgb, var(--tone) 16%%, var(--card)), var(--card));
          border-left: 6px solid var(--tone); }
.pg-icon { position: relative; flex: none; width: 56px; height: 56px; border-radius: 50%%; display: grid; place-items: center;
           color: #06110b; background: var(--tone); box-shadow: 0 0 22px -4px var(--tone); }
.pg-icon svg { width: 30px; height: 30px; }
.danger .pg-icon::after { content: ""; position: absolute; inset: 0; border-radius: 50%%; border: 3px solid var(--tone);
           animation: pg-ring 1.6s ease-out .3s infinite; }
.pg-draw { stroke-dasharray: 20; stroke-dashoffset: 20; animation: pg-draw .6s ease .35s forwards; }
.pg-verdict { font-size: 1.45rem !important; font-weight: 800; color: var(--tone); line-height: 1.15;
              animation: pg-slide .5s ease .15s both; }
.pg-sub { color: var(--muted); margin-top: 4px; font-size: .95rem !important; animation: pg-slide .5s ease .25s both; }
.pg-score { margin-left: auto; text-align: right; animation: pg-slide .5s ease .3s both; }
.pg-num { font-size: 2.1rem !important; font-weight: 800; color: var(--tone); animation: pg-count 1.2s ease-out .2s both;
          counter-reset: p var(--p); font-variant-numeric: tabular-nums; }
.pg-num::after { content: counter(p) "%%"; }
.pg-score small { display: block; color: var(--muted); font-size: .75rem; }
.pg-bar-wrap { padding: 18px 24px 6px; }
.pg-bar { position: relative; height: 12px; border-radius: 999px;
          background: linear-gradient(90deg, color-mix(in srgb, var(--safe) 18%%, var(--bg)), color-mix(in srgb, var(--danger) 22%%, var(--bg))); }
.pg-fill { height: 100%%; border-radius: 999px; background: var(--tone); box-shadow: 0 0 14px var(--tone); animation: pg-fill 1.2s cubic-bezier(.2,.8,.2,1) .2s both; }
.pg-mark { position: absolute; top: -5px; width: 2px; height: 22px; background: var(--ink); border-radius: 2px; }
.pg-mark span { position: absolute; top: 24px; transform: translateX(-50%%); white-space: nowrap; font-size: .72rem; color: var(--muted); }
.pg-meta { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; padding: 26px 24px 22px; }
.pg-meta div { animation: pg-slide .5s ease both; }
.pg-meta div:nth-child(1) { animation-delay: .45s; } .pg-meta div:nth-child(2) { animation-delay: .55s; }
.pg-meta div:nth-child(3) { animation-delay: .65s; grid-column: 1 / -1; }
.pg-k { font-size: .74rem !important; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); font-weight: 700; }
.pg-v { color: var(--ink); font-weight: 600; margin-top: 3px; }
.pg-v code { display: block; padding: 10px 12px; border-radius: 10px; background: var(--bg); color: var(--brand); border: 1px solid var(--line);
             font-size: .86rem; word-break: break-all; white-space: normal; }
.warn .pg-top { padding: 18px 22px; }

/* how it works */
.pg-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 6px 0 14px; }
.pg-tile { background: var(--card2); border: 1px solid var(--line); border-radius: 14px; padding: 12px 14px; }
.pg-tile b { display: block; font-size: 1.35rem; color: var(--brand); }
.pg-tile span { font-size: .8rem; color: var(--muted); }
.pg-foot { text-align: center; color: var(--muted); font-size: .82rem; margin-top: 26px; }
div[data-testid="stExpander"] details { border-radius: 16px; border: 1px solid var(--line); background: var(--card); margin-top: 24px; }
div[data-testid="stExpander"] summary, div[data-testid="stExpander"] p, div[data-testid="stExpander"] li { color: var(--ink); }
div[data-testid="stExpander"] code { color: var(--brand); background: var(--bg); }
div[data-testid="stCaptionContainer"] { color: var(--muted); }

@keyframes pg-rise { from { opacity: 0; transform: translateY(16px); } }
@keyframes pg-pop { from { opacity: 0; transform: translateY(18px) scale(.96); } }
@keyframes pg-slide { from { opacity: 0; transform: translateX(-10px); } }
@keyframes pg-fill { from { width: 0; } }
@keyframes pg-count { from { --p: 0; } }
@keyframes pg-draw { to { stroke-dashoffset: 0; } }
@keyframes pg-ring { from { transform: scale(1); opacity: .7; } to { transform: scale(1.7); opacity: 0; } }
@keyframes pg-shake { 0%%,100%% { transform: translateX(0); } 20%%,60%% { transform: translateX(-6px); } 40%%,80%% { transform: translateX(6px); } }
@keyframes pg-float { 50%% { transform: translateY(14px); } }
@media (max-width: 640px) {
  .pg-top { flex-wrap: wrap; } .pg-score { margin-left: 0; text-align: left; width: 100%%; }
  .pg-meta, .pg-grid { grid-template-columns: 1fr; } .pg-title { font-size: 1.6rem; }
}
@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation: none !important; transition: none !important; } }
</style>
"""

st.set_page_config(page_title="PhishGuard", page_icon="🛡️", layout="wide")


def show_html(markup: str):
    """Raw HTML via markdown; lines are stripped so markdown never treats indented HTML as a code block."""
    st.markdown("\n".join(line.strip() for line in markup.splitlines() if line.strip()), unsafe_allow_html=True)


@st.cache_resource(show_spinner="Loading model...")
def load_guard():
    return PhishGuard()


guard = load_guard()
metrics = guard.meta["test_metrics"]

for key, value in {"url": "", "result": None, "runs": 0}.items():
    st.session_state.setdefault(key, value)


def use_example(url):
    """An example only fills the box; checking happens on the button."""
    st.session_state.url = url
    st.session_state.result = None


def run_check():
    st.session_state.runs += 1
    try:
        st.session_state.result = ("ok", guard.predict(st.session_state.url), st.session_state.url.strip())
    except InvalidURL as e:
        st.session_state.result = ("invalid", str(e), None)


show_html(CSS % COLOURS)

show_html(f"""
<div class="pg-hero">
  <div>
    <div class="pg-brand"><div class="pg-logo">{ICON_SHIELD}</div>
      <div><div class="pg-title">PhishGuard</div><div class="pg-tag">Phishing link checker for Pakistani users</div></div></div>
    <div class="pg-lead">Got a link in an SMS, WhatsApp or email? Check it before you open it.
       The link is only read as text and is never opened.</div>
  </div>
  <div class="pg-chips">
    <span class="pg-chip">Test F1 <b>{metrics['f1']:.3f}</b></span>
    <span class="pg-chip">ROC-AUC <b>{metrics['roc_auc']:.3f}</b></span>
    <span class="pg-chip">Trained on <b>{guard.meta['trained_on_rows']:,}</b> URLs</span>
  </div>
</div>""")

left, right = st.columns(2, gap="large")

with left, st.container(key="check_panel"):
    show_html('<div class="pg-panel-title">Check a link</div>'
              '<div class="pg-panel-sub">Paste the full link, then press Check link.</div>'
              '<div class="pg-label">Link</div>')
    st.text_input("URL", key="url", label_visibility="collapsed",
                  placeholder="e.g. http://jazzcash-verify.weebly.com/login")
    show_html('<p class="pg-hint">Or try an example (it only fills the box):</p>')
    names = list(EXAMPLES)
    for row in (names[:2], names[2:]):
        for col, name in zip(st.columns(2), row):
            col.button(name, on_click=use_example, args=(EXAMPLES[name],), use_container_width=True)
    st.button("Check link", type="primary", on_click=run_check, use_container_width=True)

result = st.session_state.result
with right:
    if result is None:
        show_html(f"""<div class="pg-empty">{ICON_SHIELD}<b>Your result will appear here</b>
        Paste a link on the left or pick an example, then press Check link</div>""")
    else:
        kind, data, typed = result
        run = st.session_state.runs  # changes every click so the animation replays
        if kind == "invalid":
            show_html(f"""
    <div class="pg-result warn danger" data-run="{run}"><div class="pg-top">
      <div class="pg-icon">{ICON_WARN}</div>
      <div><div class="pg-verdict">Not a valid web link</div>
      <div class="pg-sub">{html.escape(data.capitalize())}. Paste a full link such as https://example.com/page</div></div>
    </div></div>""")
        else:
            pct = round(data["probability"] * 100)
            thr = round(data["threshold"] * 100)
            if data["is_phishing"]:
                tone, icon, verdict = "danger", ICON_DANGER, "Likely phishing"
                sub = "Do not enter passwords, OTPs or card details on this link."
            else:
                tone, icon, verdict = "safe", ICON_SAFE, "Looks legitimate"
                sub = "No phishing signs found, but stay careful with what you share."
            reason = ("Trusted website (top 2,000 site, never seen in phishing feeds)"
                      if data["reason"].startswith("trusted") else "Machine-learning model (Random Forest)")
            show_html(f"""
    <div class="pg-result {tone}" data-run="{run}">
      <div class="pg-top">
        <div class="pg-icon">{icon}</div>
        <div><div class="pg-verdict">{verdict}</div><div class="pg-sub">{sub}</div></div>
        <div class="pg-score"><div class="pg-num" style="--p:{pct}"></div><small>phishing probability</small></div>
      </div>
      <div class="pg-bar-wrap"><div class="pg-bar">
        <div class="pg-fill" style="width:{max(pct, 2)}%"></div>
        <div class="pg-mark" style="left:{thr}%"><span>threshold {data['threshold']:.2f}</span></div>
      </div></div>
      <div class="pg-meta">
        <div><div class="pg-k">Decided by</div><div class="pg-v">{reason}</div></div>
        <div><div class="pg-k">Rule</div><div class="pg-v">Phishing when probability &ge; {thr}%</div></div>
        <div><div class="pg-k">Checked URL</div><div class="pg-v"><code>{html.escape(typed)}</code></div></div>
      </div>
    </div>""")

with st.expander("How it works and how accurate it is"):
    show_html(f"""
<div class="pg-grid">
  <div class="pg-tile"><b>{metrics['accuracy']:.1%}</b><span>accuracy on test set</span></div>
  <div class="pg-tile"><b>{metrics['precision']:.1%}</b><span>precision (flags that are right)</span></div>
  <div class="pg-tile"><b>{metrics['recall']:.1%}</b><span>recall (scams caught)</span></div>
  <div class="pg-tile"><b>{metrics['f1']:.3f}</b><span>F1 score</span></div>
  <div class="pg-tile"><b>{metrics['roc_auc']:.3f}</b><span>ROC-AUC</span></div>
  <div class="pg-tile"><b>{guard.meta['future_recall']:.0%}</b><span>newer scams caught (unseen sites)</span></div>
</div>""")
    st.write("- A **Random Forest** looks at 30 features of the URL text: length, dots, digits, `@`, IP address, "
             "hyphens, suspicious words, free-hosting sites, shorteners and more.\n"
             "- Trusted sites (Tranco top 2,000 that never appeared in phishing feeds) are marked legitimate first.\n"
             f"- Trained on {guard.meta['trained_on_rows']:,} URLs from 7 sources and tested once on unseen websites.")
    st.caption("Limits: it does not visit the page, so a normal-looking URL can still be a scam, and some links on "
               "shared platforms (e.g. Google Docs) may be flagged. Always double-check.")

show_html('<p class="pg-foot">CT-378 Machine Learning project &middot; Team Link Lockers &middot; NED University</p>')
