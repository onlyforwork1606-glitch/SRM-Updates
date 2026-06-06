"""
fetch_data.py
API 1 → { "total": N, "registered": N, "not_registered": N }
API 2 → { "count": { "completed": N, "inprogress": N, "not_started": N } }
"""

import json, os, sys
from datetime import datetime, timezone
from pathlib import Path
import requests

# ── Config ─────────────────────────────────────────────────────────────────────
API_URL_1   = os.environ.get("API_URL_1",   "").strip()
API_URL_2   = os.environ.get("API_URL_2",   "").strip()
API_LABEL_1 = os.environ.get("API_LABEL_1", "Student Registration").strip()
API_LABEL_2 = os.environ.get("API_LABEL_2", "Test Completion").strip()

DATA_FILE = Path("data/history.json")
HTML_FILE = Path("index.html")
MAX_ROWS  = 200   # ← adjust to keep more/fewer snapshots

# ── Validate ────────────────────────────────────────────────────────────────────
missing = [n for n, v in [("API_URL_1", API_URL_1), ("API_URL_2", API_URL_2)] if not v]
if missing:
    print(f"ERROR: Missing GitHub secrets: {', '.join(missing)}")
    sys.exit(1)

# ── Fetch ────────────────────────────────────────────────────────────────────────
def fetch(url, label):
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        data = r.json()
        print(f"✅ Fetched {label}: {data}")
        return {"data": data, "error": None}
    except Exception as e:
        print(f"⚠️  ERROR fetching {label}: {e}")
        return {"data": None, "error": str(e)}

fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
r1 = fetch(API_URL_1, API_LABEL_1)
r2 = fetch(API_URL_2, API_LABEL_2)

# ── Save history ─────────────────────────────────────────────────────────────────
DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
history = []
if DATA_FILE.exists():
    try:
        history = json.loads(DATA_FILE.read_text())
        if not isinstance(history, list): history = []
    except: history = []
history.append({"fetched_at": fetched_at, "registration": r1, "test_status": r2})
history = history[-MAX_ROWS:]
DATA_FILE.write_text(json.dumps(history, indent=2))
print(f"📦 Snapshot #{len(history)} saved")

# ── HTML helpers ──────────────────────────────────────────────────────────────────
C = 314.16  # circumference of r=50 circle

def pct_str(part, whole):
    try: return f"{round(part / whole * 100, 1)}%"
    except: return "—"

def pct_num(part, whole):
    try: return round(part / whole * 100, 1)
    except: return 0

def bar(val, total, color):
    return f'<div class="progress-fill {color}" style="width:{pct_num(val,total)}%"></div>'

def dash(val, total):
    return round(val / total * C, 2) if total else 0

# ── Registration panel ────────────────────────────────────────────────────────────
def reg_panel():
    err = r1["error"]
    if err:
        return f'<div class="panel"><div class="panel-header"><span class="panel-icon">👥</span><h2>{API_LABEL_1}</h2></div><p class="fetch-error">⚠️ {err}</p></div>'

    d       = r1["data"]
    total   = d.get("total", 0)
    reg     = d.get("registered", 0)
    not_reg = d.get("not_registered", 0)
    OFFSET  = 78.54

    return f"""
    <div class="panel">
      <div class="panel-header">
        <span class="panel-icon">👥</span>
        <h2>{API_LABEL_1}</h2>
        <span class="api-badge">API 1</span>
      </div>
      <div class="hero">
        <div class="hero-stats">
          <span class="hero-label">Total Students</span>
          <span class="hero-num">{total:,}</span>
          <span class="hero-sub"><span>{reg}</span> registered &nbsp;·&nbsp; <span>{not_reg:,}</span> pending</span>
        </div>
        <svg viewBox="0 0 120 120" class="donut">
          <circle cx="60" cy="60" r="50" fill="none" stroke="var(--border)" stroke-width="14"/>
          <circle cx="60" cy="60" r="50" fill="none" stroke="var(--green)" stroke-width="14"
            stroke-dasharray="{dash(reg,total)} {C}" stroke-dashoffset="{OFFSET}" stroke-linecap="round"/>
          <text x="60" y="55" text-anchor="middle" class="donut-pct">{pct_str(reg,total)}</text>
          <text x="60" y="71" text-anchor="middle" class="donut-sub">registered</text>
        </svg>
      </div>
      <div class="stat-row">
        <div class="stat-card neutral">
          <span class="stat-label">Total</span>
          <span class="stat-value">{total:,}</span>
        </div>
        <div class="stat-card green">
          <span class="stat-label">Registered</span>
          <span class="stat-value">{reg}</span>
          <span class="stat-pct">{pct_str(reg,total)}</span>
        </div>
        <div class="stat-card red">
          <span class="stat-label">Not Registered</span>
          <span class="stat-value">{not_reg:,}</span>
          <span class="stat-pct">{pct_str(not_reg,total)}</span>
        </div>
      </div>
      <div class="progress-block">
        <div class="progress-meta"><span>Registered</span><span>{pct_str(reg,total)}</span></div>
        <div class="progress-track">{bar(reg,total,"green")}</div>
        <div class="progress-meta"><span>Not Registered</span><span>{pct_str(not_reg,total)}</span></div>
        <div class="progress-track">{bar(not_reg,total,"red")}</div>
      </div>
    </div>"""

# ── Test panel ────────────────────────────────────────────────────────────────────
def test_panel():
    err = r2["error"]
    if err:
        return f'<div class="panel"><div class="panel-header"><span class="panel-icon">📝</span><h2>{API_LABEL_2}</h2></div><p class="fetch-error">⚠️ {err}</p></div>'

    cnt         = r2["data"].get("count", {})
    completed   = cnt.get("completed",   0)
    inprogress  = cnt.get("inprogress",  0)
    not_started = cnt.get("not_started", 0)
    t2          = completed + inprogress + not_started
    OFFSET      = 78.54

    ns_dash = dash(not_started, t2)
    ip_dash = dash(inprogress,  t2)
    cp_dash = dash(completed,   t2)
    ns_off  = OFFSET
    ip_off  = round(OFFSET - ns_dash, 2)
    cp_off  = round(OFFSET - ns_dash - ip_dash, 2)

    return f"""
    <div class="panel">
      <div class="panel-header">
        <span class="panel-icon">📝</span>
        <h2>{API_LABEL_2}</h2>
        <span class="api-badge">API 2</span>
      </div>
      <div class="hero">
        <div class="hero-stats">
          <span class="hero-label">Total Registered</span>
          <span class="hero-num">{t2}</span>
          <span class="hero-sub"><span>{completed}</span> completed &nbsp;·&nbsp; <span>{not_started}</span> not started</span>
        </div>
        <svg viewBox="0 0 120 120" class="donut">
          <circle cx="60" cy="60" r="50" fill="none" stroke="var(--border)" stroke-width="14"/>
          <circle cx="60" cy="60" r="50" fill="none" stroke="var(--red)" stroke-width="14"
            stroke-dasharray="{ns_dash} {C}" stroke-dashoffset="{ns_off}" stroke-linecap="round"/>
          <circle cx="60" cy="60" r="50" fill="none" stroke="var(--yellow)" stroke-width="14"
            stroke-dasharray="{ip_dash} {C}" stroke-dashoffset="{ip_off}" stroke-linecap="round"/>
          <circle cx="60" cy="60" r="50" fill="none" stroke="var(--green)" stroke-width="14"
            stroke-dasharray="{cp_dash} {C}" stroke-dashoffset="{cp_off}" stroke-linecap="round"/>
          <text x="60" y="55" text-anchor="middle" class="donut-pct">{pct_str(completed,t2)}</text>
          <text x="60" y="71" text-anchor="middle" class="donut-sub">completed</text>
        </svg>
      </div>
      <div class="stat-row">
        <div class="stat-card green">
          <span class="stat-label">Completed</span>
          <span class="stat-value">{completed}</span>
          <span class="stat-pct">{pct_str(completed,t2)}</span>
        </div>
        <div class="stat-card yellow">
          <span class="stat-label">In Progress</span>
          <span class="stat-value">{inprogress}</span>
          <span class="stat-pct">{pct_str(inprogress,t2)}</span>
        </div>
        <div class="stat-card red">
          <span class="stat-label">Not Started</span>
          <span class="stat-value">{not_started}</span>
          <span class="stat-pct">{pct_str(not_started,t2)}</span>
        </div>
      </div>
      <div class="progress-block">
        <div class="progress-meta"><span>Completed</span><span>{pct_str(completed,t2)}</span></div>
        <div class="progress-track">{bar(completed,t2,"green")}</div>
        <div class="progress-meta"><span>In Progress</span><span>{pct_str(inprogress,t2)}</span></div>
        <div class="progress-track">{bar(inprogress,t2,"yellow")}</div>
        <div class="progress-meta"><span>Not Started</span><span>{pct_str(not_started,t2)}</span></div>
        <div class="progress-track">{bar(not_started,t2,"red")}</div>
      </div>
      <div class="legend">
        <div class="legend-item"><div class="legend-dot" style="background:var(--green)"></div>Completed ({completed})</div>
        <div class="legend-item"><div class="legend-dot" style="background:var(--yellow)"></div>In Progress ({inprogress})</div>
        <div class="legend-item"><div class="legend-dot" style="background:var(--red)"></div>Not Started ({not_started})</div>
      </div>
    </div>"""

# ── Write HTML ────────────────────────────────────────────────────────────────────
html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <meta http-equiv="refresh" content="900"/>
  <title>Student Dashboard</title>
  <link rel="preconnect" href="https://fonts.googleapis.com"/>
  <link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet"/>
  <style>
    *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
    :root{{--bg:#0b0d12;--surface:#12151d;--surface2:#181c27;--border:#222636;--text:#e6eaf4;--muted:#5b6278;--green:#1fd6a0;--red:#f4566a;--yellow:#f5c430;--blue:#4b9cf5}}
    body{{background:var(--bg);color:var(--text);font-family:'Syne',sans-serif;min-height:100vh;padding:2rem 1rem 5rem}}
    body::after{{content:'';position:fixed;inset:0;background-image:linear-gradient(var(--border) 1px,transparent 1px),linear-gradient(90deg,var(--border) 1px,transparent 1px);background-size:40px 40px;opacity:.15;pointer-events:none;z-index:0}}
    .page{{position:relative;z-index:1;max-width:1000px;margin:0 auto}}
    header{{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:1rem;padding-bottom:1.5rem;margin-bottom:2.5rem;border-bottom:1px solid var(--border)}}
    .brand h1{{font-size:clamp(1.4rem,4vw,2rem);font-weight:800;letter-spacing:-.04em;background:linear-gradient(120deg,#e6eaf4 30%,var(--blue));-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
    .brand p{{font-size:.72rem;color:var(--muted);font-family:'DM Mono',monospace;margin-top:.2rem}}
    .timestamp{{font-family:'DM Mono',monospace;font-size:.68rem;color:var(--muted);background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:.4rem .85rem}}
    .timestamp strong{{color:var(--green)}}
    .panels{{display:grid;grid-template-columns:repeat(auto-fit,minmax(440px,1fr));gap:1.5rem}}
    .panel{{background:var(--surface);border:1px solid var(--border);border-radius:16px;padding:1.75rem;display:flex;flex-direction:column;gap:1.6rem;animation:rise .5s cubic-bezier(.22,1,.36,1) both}}
    .panel:nth-child(2){{animation-delay:.09s}}
    @keyframes rise{{from{{opacity:0;transform:translateY(18px)}}to{{opacity:1;transform:translateY(0)}}}}
    .panel-header{{display:flex;align-items:center;gap:.7rem;padding-bottom:1.1rem;border-bottom:1px solid var(--border)}}
    .panel-icon{{font-size:1.4rem}}
    .panel-header h2{{font-size:1.05rem;font-weight:700;letter-spacing:-.02em}}
    .api-badge{{margin-left:auto;font-family:'DM Mono',monospace;font-size:.58rem;color:var(--muted);background:var(--surface2);border:1px solid var(--border);border-radius:5px;padding:.2rem .5rem}}
    .fetch-error{{color:var(--red);font-size:.8rem;font-family:'DM Mono',monospace}}
    .hero{{display:flex;align-items:center;justify-content:space-between;gap:1rem}}
    .hero-stats{{display:flex;flex-direction:column;gap:.4rem}}
    .hero-num{{font-size:3.2rem;font-weight:800;line-height:1;letter-spacing:-.05em}}
    .hero-label{{font-size:.68rem;color:var(--muted);font-family:'DM Mono',monospace;text-transform:uppercase;letter-spacing:.1em}}
    .hero-sub{{font-size:.82rem;color:var(--muted);margin-top:.2rem}}
    .hero-sub span{{color:var(--text);font-weight:700}}
    .stat-row{{display:grid;grid-template-columns:repeat(3,1fr);gap:.7rem}}
    .stat-card{{background:var(--surface2);border:1px solid var(--border);border-radius:10px;padding:.85rem .7rem;display:flex;flex-direction:column;gap:.2rem;transition:transform .15s}}
    .stat-card:hover{{transform:translateY(-2px)}}
    .stat-label{{font-size:.58rem;text-transform:uppercase;letter-spacing:.1em;color:var(--muted);font-family:'DM Mono',monospace}}
    .stat-value{{font-size:1.75rem;font-weight:800;line-height:1;letter-spacing:-.03em}}
    .stat-pct{{font-size:.65rem;font-family:'DM Mono',monospace;color:var(--muted)}}
    .stat-card.neutral .stat-value{{color:var(--text)}}
    .stat-card.green{{border-color:#1fd6a025}}.stat-card.green .stat-value{{color:var(--green)}}
    .stat-card.red{{border-color:#f4566a25}}.stat-card.red .stat-value{{color:var(--red)}}
    .stat-card.yellow{{border-color:#f5c43025}}.stat-card.yellow .stat-value{{color:var(--yellow)}}
    .progress-block{{display:flex;flex-direction:column;gap:.55rem}}
    .progress-meta{{display:flex;justify-content:space-between;font-size:.66rem;color:var(--muted);font-family:'DM Mono',monospace}}
    .progress-track{{height:8px;background:var(--border);border-radius:99px;overflow:hidden}}
    .progress-fill{{height:100%;border-radius:99px;transition:width .8s ease}}
    .progress-fill.green{{background:var(--green)}}.progress-fill.red{{background:var(--red)}}.progress-fill.yellow{{background:var(--yellow)}}
    .donut{{width:120px;height:120px}}
    .donut-pct{{fill:var(--text);font-family:'Syne',sans-serif;font-size:19px;font-weight:800}}
    .donut-sub{{fill:var(--muted);font-family:'DM Mono',monospace;font-size:8.5px}}
    .legend{{display:flex;gap:1rem;flex-wrap:wrap}}
    .legend-item{{display:flex;align-items:center;gap:.4rem;font-size:.68rem;color:var(--muted);font-family:'DM Mono',monospace}}
    .legend-dot{{width:8px;height:8px;border-radius:50%}}
    footer{{margin-top:3rem;text-align:center;font-size:.65rem;color:var(--muted);font-family:'DM Mono',monospace}}
    @media(max-width:520px){{.panels{{grid-template-columns:1fr}}.hero-num{{font-size:2.6rem}}}}
  </style>
</head>
<body>
<div class="page">
  <header>
    <div class="brand">
      <h1>Student IRI Dashboard</h1>
      <p>Auto-updated every 15 min via GitHub Actions</p>
    </div>
    <div class="timestamp">Last updated: <strong>{fetched_at}</strong></div>
  </header>
  <div class="panels">
    {reg_panel()}
    {test_panel()}
  </div>
  <footer>SkillAgent API &nbsp;·&nbsp; GitHub Actions &nbsp;·&nbsp; {fetched_at}</footer>
</div>
</body>
</html>"""

HTML_FILE.write_text(html)
print(f"🌐 index.html written with live data at {fetched_at}")
