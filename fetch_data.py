"""
fetch_data.py
Fetches two student-status API endpoints and:
  1. Appends a timestamped snapshot to data/history.json (keeps last 200)
  2. Re-generates index.html with live stats for both colleges
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
import requests

# ── Config ─────────────────────────────────────────────────────────────────────
# Set these as GitHub Secrets: API_URL_1 and API_URL_2
# No Bearer token needed for these endpoints.

APIS = [
    {
        "key":   "api1",
        "label": os.environ.get("API_LABEL_1", "College 1"),   # override via secret/env if you like
        "url":   os.environ.get("API_URL_1", "").strip(),
    },
    {
        "key":   "api2",
        "label": os.environ.get("API_LABEL_2", "College 2"),
        "url":   os.environ.get("API_URL_2", "").strip(),
    },
]

DATA_FILE  = Path("data/history.json")
HTML_FILE  = Path("index.html")
MAX_ROWS   = 200   # keep last 200 snapshots (~50 hours at 15-min intervals)

# ── Validate ────────────────────────────────────────────────────────────────────
missing = [a["label"] for a in APIS if not a["url"]]
if missing:
    print(f"ERROR: API URL not set for: {', '.join(missing)}")
    print("Please set API_URL_1 and API_URL_2 in GitHub repository secrets.")
    sys.exit(1)

# ── Fetch both APIs ─────────────────────────────────────────────────────────────
fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
results = {}

for api in APIS:
    try:
        resp = requests.get(api["url"], headers={"Content-Type": "application/json"}, timeout=30)
        resp.raise_for_status()
        results[api["key"]] = {"label": api["label"], "data": resp.json(), "error": None}
        print(f"✅ Fetched {api['label']}")
    except requests.exceptions.RequestException as e:
        results[api["key"]] = {"label": api["label"], "data": None, "error": str(e)}
        print(f"⚠️  ERROR fetching {api['label']}: {e}")
    except json.JSONDecodeError:
        results[api["key"]] = {"label": api["label"], "data": None, "error": "Invalid JSON response"}
        print(f"⚠️  ERROR: {api['label']} did not return valid JSON")

# ── Build snapshot ──────────────────────────────────────────────────────────────
snapshot = {"fetched_at": fetched_at, **results}

# ── Load existing history ───────────────────────────────────────────────────────
DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
if DATA_FILE.exists():
    try:
        history = json.loads(DATA_FILE.read_text())
        if not isinstance(history, list):
            history = []
    except json.JSONDecodeError:
        history = []
else:
    history = []

history.append(snapshot)
history = history[-MAX_ROWS:]
DATA_FILE.write_text(json.dumps(history, indent=2))
print(f"📦 Saved snapshot #{len(history)} to {DATA_FILE}")

# ── Generate index.html ─────────────────────────────────────────────────────────
def safe(data, *keys, default="—"):
    """Safely traverse nested dict keys."""
    val = data
    for k in keys:
        if not isinstance(val, dict):
            return default
        val = val.get(k, default)
    return val if val != default else default

def college_section(key, result):
    """Return the HTML block for one college."""
    label = result["label"]
    d     = result["data"] or {}
    err   = result["error"]

    if err:
        return f"""
        <section class="college-section error-section">
          <h2 class="college-title">{label}</h2>
          <p class="fetch-error">⚠️ Could not fetch data: {err}</p>
        </section>"""

    overall  = d.get("overall",           {})
    breakup  = d.get("registered_breakup",{})
    test     = d.get("test_status",       {})

    return f"""
        <section class="college-section">
          <h2 class="college-title">{label}</h2>

          <div class="cards-grid">
            <!-- Overall -->
            <div class="card">
              <span class="card-label">Total Students</span>
              <span class="card-value">{safe(overall,'total_students')}</span>
            </div>
            <div class="card highlight-green">
              <span class="card-label">Registered</span>
              <span class="card-value">{safe(overall,'registered')}</span>
              <span class="card-pct">{safe(overall,'registered_pct')}%</span>
            </div>
            <div class="card highlight-red">
              <span class="card-label">Unregistered</span>
              <span class="card-value">{safe(overall,'unregistered')}</span>
              <span class="card-pct">{safe(overall,'unregistered_pct')}%</span>
            </div>
          </div>

          <h3 class="sub-title">Registered Breakup</h3>
          <div class="cards-grid">
            <div class="card highlight-blue">
              <span class="card-label">Male</span>
              <span class="card-value">{safe(breakup,'male')}</span>
              <span class="card-pct">{safe(breakup,'male_pct')}%</span>
            </div>
            <div class="card highlight-purple">
              <span class="card-label">Female</span>
              <span class="card-value">{safe(breakup,'female')}</span>
              <span class="card-pct">{safe(breakup,'female_pct')}%</span>
            </div>
          </div>

          <h3 class="sub-title">Test Status</h3>
          <div class="cards-grid">
            <div class="card highlight-green">
              <span class="card-label">Completed</span>
              <span class="card-value">{safe(test,'completed')}</span>
              <span class="card-pct">{safe(test,'completed_pct')}%</span>
            </div>
            <div class="card highlight-yellow">
              <span class="card-label">Started (Incomplete)</span>
              <span class="card-value">{safe(test,'started_incomplete')}</span>
              <span class="card-pct">{safe(test,'started_incomplete_pct')}%</span>
            </div>
            <div class="card highlight-red">
              <span class="card-label">Not Started</span>
              <span class="card-value">{safe(test,'not_started')}</span>
              <span class="card-pct">{safe(test,'not_started_pct')}%</span>
            </div>
          </div>

          <!-- Progress bars -->
          <div class="progress-block">
            <div class="progress-label">
              <span>Registration Progress</span>
              <span>{safe(overall,'registered_pct')}%</span>
            </div>
            <div class="progress-bar">
              <div class="progress-fill green" style="width:{safe(overall,'registered_pct', default=0)}%"></div>
            </div>

            <div class="progress-label">
              <span>Test Completion</span>
              <span>{safe(test,'completed_pct')}%</span>
            </div>
            <div class="progress-bar">
              <div class="progress-fill blue" style="width:{safe(test,'completed_pct', default=0)}%"></div>
            </div>
          </div>
        </section>"""

sections_html = "\n".join(college_section(k, results[k]) for k in ("api1", "api2"))

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Student IRI Dashboard</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet" />
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    :root {{
      --bg:        #0d0f14;
      --surface:   #151820;
      --border:    #252a35;
      --text:      #e8ecf4;
      --muted:     #6b7589;
      --green:     #22d3a5;
      --red:       #f45b69;
      --blue:      #4fa3f7;
      --yellow:    #f5c842;
      --purple:    #c084fc;
      --accent:    #4fa3f7;
    }}

    body {{
      background: var(--bg);
      color: var(--text);
      font-family: 'Syne', sans-serif;
      min-height: 100vh;
      padding: 2rem 1rem 4rem;
    }}

    /* noise overlay */
    body::before {{
      content: '';
      position: fixed; inset: 0;
      background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.75' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.04'/%3E%3C/svg%3E");
      pointer-events: none;
      z-index: 0;
    }}

    .page {{ position: relative; z-index: 1; max-width: 960px; margin: 0 auto; }}

    header {{
      display: flex; justify-content: space-between; align-items: flex-end;
      border-bottom: 1px solid var(--border);
      padding-bottom: 1.5rem; margin-bottom: 2.5rem;
      flex-wrap: wrap; gap: 1rem;
    }}

    .header-left h1 {{
      font-size: clamp(1.6rem, 4vw, 2.4rem);
      font-weight: 800;
      letter-spacing: -0.03em;
      background: linear-gradient(135deg, var(--text) 40%, var(--accent));
      -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }}

    .header-left p {{
      font-size: 0.8rem; color: var(--muted);
      font-family: 'DM Mono', monospace; margin-top: .3rem;
    }}

    .last-updated {{
      font-family: 'DM Mono', monospace;
      font-size: 0.72rem; color: var(--muted);
      background: var(--surface);
      border: 1px solid var(--border);
      padding: .4rem .8rem; border-radius: 6px;
      white-space: nowrap;
    }}
    .last-updated span {{ color: var(--green); }}

    /* two-column layout for the two colleges */
    .colleges-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
      gap: 2rem;
    }}

    .college-section {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 1.8rem;
      display: flex; flex-direction: column; gap: 1.4rem;
      animation: fadeUp .5s ease both;
    }}

    .college-section:nth-child(2) {{ animation-delay: .1s; }}

    @keyframes fadeUp {{
      from {{ opacity:0; transform:translateY(16px); }}
      to   {{ opacity:1; transform:translateY(0); }}
    }}

    .error-section {{ border-color: var(--red); }}
    .fetch-error {{ color: var(--red); font-size: .85rem; font-family:'DM Mono',monospace; }}

    .college-title {{
      font-size: 1.25rem; font-weight: 700; letter-spacing: -.02em;
      color: var(--text);
      padding-bottom: .8rem;
      border-bottom: 1px solid var(--border);
    }}

    .sub-title {{
      font-size: .75rem; font-weight: 600;
      text-transform: uppercase; letter-spacing: .12em;
      color: var(--muted);
    }}

    .cards-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(110px, 1fr));
      gap: .75rem;
    }}

    .card {{
      background: var(--bg);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: .9rem .8rem;
      display: flex; flex-direction: column; gap: .3rem;
      transition: transform .15s, border-color .15s;
    }}
    .card:hover {{ transform: translateY(-2px); border-color: var(--accent); }}

    .card-label {{
      font-size: .65rem; text-transform: uppercase; letter-spacing: .1em;
      color: var(--muted); font-family: 'DM Mono', monospace;
    }}
    .card-value  {{ font-size: 1.6rem; font-weight: 800; line-height: 1; }}
    .card-pct    {{ font-size: .72rem; font-family:'DM Mono',monospace; color: var(--muted); }}

    .highlight-green  {{ border-color: #22d3a530; }}
    .highlight-green  .card-value {{ color: var(--green); }}
    .highlight-red    {{ border-color: #f45b6930; }}
    .highlight-red    .card-value {{ color: var(--red); }}
    .highlight-blue   {{ border-color: #4fa3f730; }}
    .highlight-blue   .card-value {{ color: var(--blue); }}
    .highlight-yellow {{ border-color: #f5c84230; }}
    .highlight-yellow .card-value {{ color: var(--yellow); }}
    .highlight-purple {{ border-color: #c084fc30; }}
    .highlight-purple .card-value {{ color: var(--purple); }}

    /* Progress bars */
    .progress-block {{ display: flex; flex-direction: column; gap: .65rem; }}
    .progress-label {{
      display: flex; justify-content: space-between;
      font-size: .72rem; color: var(--muted); font-family:'DM Mono',monospace;
    }}
    .progress-bar {{
      height: 6px; background: var(--border); border-radius: 99px; overflow: hidden;
    }}
    .progress-fill {{
      height: 100%; border-radius: 99px;
      transition: width .6s ease;
    }}
    .progress-fill.green {{ background: var(--green); }}
    .progress-fill.blue  {{ background: var(--blue);  }}

    footer {{
      margin-top: 3rem; text-align: center;
      font-size: .72rem; color: var(--muted); font-family:'DM Mono',monospace;
    }}

    @media (max-width: 480px) {{
      .colleges-grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class="page">
    <header>
      <div class="header-left">
        <h1>Student IRI Dashboard</h1>
        <p>Auto-refreshed every 15 minutes via GitHub Actions</p>
      </div>
      <div class="last-updated">
        Last fetched: <span>{fetched_at}</span>
      </div>
    </header>

    <div class="colleges-grid">
{sections_html}
    </div>

    <footer>
      Data sourced from SkillAgent API &nbsp;·&nbsp; Generated by GitHub Actions &nbsp;·&nbsp; {fetched_at}
    </footer>
  </div>
</body>
</html>"""

HTML_FILE.write_text(html)
print(f"🌐 index.html updated at {fetched_at}")
