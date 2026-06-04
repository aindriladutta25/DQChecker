"""
app.py — DQChecker Web App
Author: Aindrila Dutta
------------------------------------------------------
Run:
    pip install flask pandas numpy
    python -m src.app
Then open http://localhost:5000
"""

import os
import json
import uuid
import tempfile

import pandas as pd
from flask import Flask, render_template_string, request, jsonify

try:
    from .dq_checker import run_full_report
except ImportError:
    from src.dq_checker import run_full_report

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB upload limit

# ─────────────────────────────────────────────
# HTML Template (single-file app, no templates folder needed)
# ─────────────────────────────────────────────

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>DQChecker — Data Quality Checker</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Mono:ital,wght@0,300;0,400;0,500;1,400&family=Syne:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #0a0a0f;
    --surface: #111118;
    --surface2: #18181f;
    --border: #2a2a35;
    --border2: #3a3a48;
    --text: #e8e8f0;
    --muted: #7a7a90;
    --accent: #7c6fff;
    --accent2: #a78bfa;
    --green: #34d399;
    --red: #f87171;
    --amber: #fbbf24;
    --mono: 'DM Mono', monospace;
    --sans: 'Syne', sans-serif;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--text); font-family: var(--sans); min-height: 100vh; }

  /* ── layout ── */
  .top-bar { border-bottom: 1px solid var(--border); padding: 18px 40px; display: flex; align-items: center; justify-content: space-between; }
  .logo { font-size: 18px; font-weight: 800; letter-spacing: -0.02em; }
  .logo span { color: var(--accent2); }
  .badge { font-family: var(--mono); font-size: 11px; color: var(--muted); border: 1px solid var(--border); padding: 4px 10px; border-radius: 999px; }
  .main { max-width: 900px; margin: 0 auto; padding: 60px 24px 100px; }

  /* ── hero ── */
  .hero { text-align: center; margin-bottom: 56px; }
  .hero h1 { font-size: clamp(32px, 6vw, 52px); font-weight: 800; letter-spacing: -0.03em; line-height: 1.1; margin-bottom: 14px; }
  .hero h1 em { font-style: normal; color: var(--accent2); }
  .hero p { color: var(--muted); font-size: 16px; font-family: var(--mono); max-width: 480px; margin: 0 auto; line-height: 1.6; }

  /* ── drop zone ── */
  #dropzone {
    border: 1.5px dashed var(--border2);
    border-radius: 16px;
    padding: 56px 24px;
    text-align: center;
    cursor: pointer;
    transition: border-color 0.2s, background 0.2s;
    background: var(--surface);
    margin-bottom: 16px;
    position: relative;
  }
  #dropzone.drag-over { border-color: var(--accent); background: #1a1830; }
  #dropzone.has-file { border-color: var(--green); border-style: solid; }
  .drop-icon { font-size: 40px; margin-bottom: 16px; opacity: 0.5; }
  .drop-title { font-size: 18px; font-weight: 600; margin-bottom: 6px; }
  .drop-sub { font-size: 13px; color: var(--muted); font-family: var(--mono); }
  #file-input { display: none; }
  #file-name { font-family: var(--mono); font-size: 13px; color: var(--green); margin-top: 10px; }

  /* ── options ── */
  .options-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 20px; }
  .field label { display: block; font-size: 11px; font-family: var(--mono); color: var(--muted); margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.05em; }
  .field input, .field select {
    width: 100%; background: var(--surface); border: 1px solid var(--border); color: var(--text);
    border-radius: 8px; padding: 10px 14px; font-family: var(--mono); font-size: 13px;
    outline: none; transition: border-color 0.2s;
  }
  .field input:focus, .field select:focus { border-color: var(--accent); }
  .field input::placeholder { color: var(--muted); }

  /* ── run button ── */
  #run-btn {
    width: 100%; padding: 16px; background: var(--accent); border: none; border-radius: 10px;
    color: #fff; font-family: var(--sans); font-size: 15px; font-weight: 700;
    cursor: pointer; letter-spacing: 0.01em; transition: opacity 0.15s, transform 0.1s;
    margin-bottom: 48px;
  }
  #run-btn:hover { opacity: 0.9; }
  #run-btn:active { transform: scale(0.99); }
  #run-btn:disabled { opacity: 0.4; cursor: not-allowed; }

  /* ── results ── */
  #results { display: none; }
  .score-row { display: flex; align-items: center; gap: 24px; margin-bottom: 32px; }
  .score-circle {
    width: 96px; height: 96px; border-radius: 50%; flex-shrink: 0;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    border: 3px solid var(--accent); background: #1a1830;
  }
  .score-num { font-size: 28px; font-weight: 800; line-height: 1; }
  .score-label { font-size: 10px; color: var(--muted); font-family: var(--mono); margin-top: 2px; }
  .score-meta h2 { font-size: 22px; font-weight: 700; letter-spacing: -0.02em; }
  .score-meta p { color: var(--muted); font-family: var(--mono); font-size: 12px; margin-top: 4px; }

  .section { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; margin-bottom: 16px; overflow: hidden; }
  .section-head {
    display: flex; align-items: center; justify-content: space-between;
    padding: 14px 20px; border-bottom: 1px solid var(--border); cursor: pointer;
  }
  .section-head:hover { background: var(--surface2); }
  .section-title { font-size: 13px; font-weight: 600; display: flex; align-items: center; gap: 10px; }
  .pill { font-size: 10px; font-family: var(--mono); padding: 3px 9px; border-radius: 999px; font-weight: 500; }
  .pill-pass { background: #0d2b1e; color: var(--green); border: 1px solid #1a5c3a; }
  .pill-fail { background: #2b0d0d; color: var(--red); border: 1px solid #5c1a1a; }
  .pill-warn { background: #2b2000; color: var(--amber); border: 1px solid #5c4400; }
  .chevron { color: var(--muted); font-size: 14px; transition: transform 0.2s; }
  .chevron.open { transform: rotate(90deg); }
  .section-body { padding: 16px 20px; display: none; }
  .section-body.open { display: block; }

  /* ── table ── */
  .dq-table { width: 100%; border-collapse: collapse; font-family: var(--mono); font-size: 12px; }
  .dq-table th { text-align: left; color: var(--muted); padding: 6px 12px; border-bottom: 1px solid var(--border); font-weight: 400; text-transform: uppercase; letter-spacing: 0.05em; font-size: 10px; }
  .dq-table td { padding: 8px 12px; border-bottom: 1px solid var(--border); color: var(--text); }
  .dq-table tr:last-child td { border-bottom: none; }
  .dq-table tr:hover td { background: var(--surface2); }
  .num-bad { color: var(--red); }
  .num-ok { color: var(--green); }
  .num-warn { color: var(--amber); }

  /* ── bar ── */
  .bar-wrap { background: var(--surface2); border-radius: 4px; height: 6px; margin-top: 4px; }
  .bar-fill { height: 6px; border-radius: 4px; transition: width 0.6s ease; }

  /* ── stat chips ── */
  .chips { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 12px; }
  .chip { background: var(--surface2); border: 1px solid var(--border); border-radius: 8px; padding: 10px 16px; }
  .chip-val { font-size: 20px; font-weight: 700; }
  .chip-key { font-size: 10px; color: var(--muted); font-family: var(--mono); margin-top: 2px; text-transform: uppercase; letter-spacing: 0.05em; }

  /* ── loader ── */
  #loader { display: none; text-align: center; padding: 32px; }
  .spinner { width: 36px; height: 36px; border: 3px solid var(--border2); border-top-color: var(--accent); border-radius: 50%; animation: spin 0.8s linear infinite; margin: 0 auto 14px; }
  @keyframes spin { to { transform: rotate(360deg); } }
  .loader-text { font-family: var(--mono); font-size: 13px; color: var(--muted); }

  .tag-list { display: flex; flex-wrap: wrap; gap: 6px; }
  .col-tag { font-family: var(--mono); font-size: 11px; padding: 3px 8px; background: var(--surface2); border: 1px solid var(--border); border-radius: 4px; color: var(--muted); }

  @media (max-width: 600px) {
    .top-bar { padding: 14px 16px; }
    .main { padding: 32px 16px 80px; }
    .options-row { grid-template-columns: 1fr; }
  }
</style>
</head>
<body>

<div class="top-bar">
  <div class="logo">DQ<span>Checker</span></div>
  <div class="badge">v1.0 · by Aindrila Dutta</div>
</div>

<div class="main">
  <div class="hero">
    <h1>Know your data<br>before it <em>breaks</em> your pipeline.</h1>
    <p>Drop any CSV. Get a full quality report in seconds — nulls, dupes, outliers, schema issues.</p>
  </div>

  <div id="dropzone" onclick="document.getElementById('file-input').click()">
    <div class="drop-icon">⬡</div>
    <div class="drop-title">Drop your CSV here</div>
    <div class="drop-sub">or click to browse · max 10 MB</div>
    <div id="file-name"></div>
  </div>
  <input type="file" id="file-input" accept=".csv">

  <div class="options-row">
    <div class="field">
      <label>Primary key column (optional)</label>
      <input id="key-col" type="text" placeholder="e.g. patient_id, order_id">
    </div>
    <div class="field">
      <label>Outlier detection method</label>
      <select id="method">
        <option value="IQR">IQR (interquartile range)</option>
        <option value="zscore">Z-score (±3σ)</option>
      </select>
    </div>
  </div>

  <button id="run-btn" disabled>Run quality check</button>

  <div id="loader">
    <div class="spinner"></div>
    <div class="loader-text">Analysing your data...</div>
  </div>

  <div id="results"></div>
</div>

<script>
const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('file-input');
const runBtn = document.getElementById('run-btn');
let selectedFile = null;

dropzone.addEventListener('dragover', e => { e.preventDefault(); dropzone.classList.add('drag-over'); });
dropzone.addEventListener('dragleave', () => dropzone.classList.remove('drag-over'));
dropzone.addEventListener('drop', e => {
  e.preventDefault();
  dropzone.classList.remove('drag-over');
  const f = e.dataTransfer.files[0];
  if (f && f.name.endsWith('.csv')) setFile(f);
});
fileInput.addEventListener('change', () => { if (fileInput.files[0]) setFile(fileInput.files[0]); });

function setFile(f) {
  selectedFile = f;
  dropzone.classList.add('has-file');
  document.getElementById('file-name').textContent = '✓ ' + f.name;
  runBtn.disabled = false;
}

function scoreColor(s) {
  if (s >= 80) return 'var(--green)';
  if (s >= 50) return 'var(--amber)';
  return 'var(--red)';
}

function scoreGrade(s) {
  if (s >= 90) return 'Excellent';
  if (s >= 75) return 'Good';
  if (s >= 50) return 'Needs attention';
  return 'Poor quality';
}

function pill(hasIssues) {
  return hasIssues
    ? '<span class="pill pill-fail">FAIL</span>'
    : '<span class="pill pill-pass">PASS</span>';
}

function nullColor(pct) {
  if (pct === 0) return 'num-ok';
  if (pct < 10) return 'num-warn';
  return 'num-bad';
}

function barColor(pct) {
  if (pct === 0) return 'var(--green)';
  if (pct < 10) return 'var(--amber)';
  return 'var(--red)';
}

function toggle(id) {
  const body = document.getElementById('body-' + id);
  const chev = document.getElementById('chev-' + id);
  body.classList.toggle('open');
  chev.classList.toggle('open');
}

function render(data) {
  const r = data;
  const scoreC = scoreColor(r.overall_score);

  let nullRows = Object.entries(r.nulls.columns).map(([col, info]) => {
    const pct = info.null_pct;
    return `<tr>
      <td>${col}</td>
      <td class="${nullColor(pct)}">${info.null_count.toLocaleString()}</td>
      <td>
        <div>${pct.toFixed(1)}%</div>
        <div class="bar-wrap"><div class="bar-fill" style="width:${Math.min(pct,100)}%;background:${barColor(pct)}"></div></div>
      </td>
    </tr>`;
  }).join('');

  let outlierRows = Object.entries(r.outliers.columns).map(([col, info]) => {
    return `<tr>
      <td>${col}</td>
      <td class="${info.outlier_count > 0 ? 'num-bad' : 'num-ok'}">${info.outlier_count.toLocaleString()}</td>
      <td>${info.outlier_pct.toFixed(1)}%</td>
      <td style="color:var(--muted)">${info.lower_bound.toFixed(2)} – ${info.upper_bound.toFixed(2)}</td>
    </tr>`;
  }).join('');

  let schemaRows = Object.entries(r.schema.dtypes).map(([col, dtype]) => {
    const isHighNull = r.schema.high_null_cols.includes(col);
    const isConst = r.schema.constant_cols.includes(col);
    const isLowCard = r.schema.low_cardinality_cols.includes(col);
    let flags = [];
    if (isHighNull) flags.push('<span class="pill pill-fail">high null</span>');
    if (isConst) flags.push('<span class="pill pill-fail">constant</span>');
    if (isLowCard) flags.push('<span class="pill pill-warn">low cardinality</span>');
    return `<tr><td>${col}</td><td style="color:var(--muted)">${dtype}</td><td>${flags.join(' ') || '<span style="color:var(--green);font-size:11px">OK</span>'}</td></tr>`;
  }).join('');

  const html = `
    <div class="score-row">
      <div class="score-circle" style="border-color:${scoreC}">
        <div class="score-num" style="color:${scoreC}">${r.overall_score}</div>
        <div class="score-label">/ 100</div>
      </div>
      <div class="score-meta">
        <h2>${scoreGrade(r.overall_score)}</h2>
        <p>${r.row_count.toLocaleString()} rows · ${r.col_count} columns · ${r.source}</p>
      </div>
    </div>

    <div class="section">
      <div class="section-head" onclick="toggle('nulls')">
        <div class="section-title">Null values ${pill(r.nulls.has_issues)}</div>
        <span class="chevron" id="chev-nulls">▶</span>
      </div>
      <div class="section-body open" id="body-nulls">
        <table class="dq-table">
          <thead><tr><th>Column</th><th>Null count</th><th>Null %</th></tr></thead>
          <tbody>${nullRows}</tbody>
        </table>
      </div>
    </div>

    <div class="section">
      <div class="section-head" onclick="toggle('dupes')">
        <div class="section-title">Duplicates ${pill(r.duplicates.has_issues)}</div>
        <span class="chevron" id="chev-dupes">▶</span>
      </div>
      <div class="section-body" id="body-dupes">
        <div class="chips">
          <div class="chip"><div class="chip-val ${r.duplicates.duplicate_rows > 0 ? 'num-bad' : 'num-ok'}">${r.duplicates.duplicate_rows.toLocaleString()}</div><div class="chip-key">Duplicate rows</div></div>
          <div class="chip"><div class="chip-val ${r.duplicates.duplicate_keys > 0 ? 'num-bad' : 'num-ok'}">${r.duplicates.duplicate_keys.toLocaleString()}</div><div class="chip-key">Duplicate keys${r.duplicates.key_col ? ' (' + r.duplicates.key_col + ')' : ''}</div></div>
          <div class="chip"><div class="chip-val">${r.duplicates.duplicate_pct.toFixed(1)}%</div><div class="chip-key">Duplicate rate</div></div>
        </div>
      </div>
    </div>

    <div class="section">
      <div class="section-head" onclick="toggle('outliers')">
        <div class="section-title">Outliers <span style="color:var(--muted);font-size:11px;font-family:var(--mono)">${r.outliers.method}</span> ${pill(r.outliers.has_issues)}</div>
        <span class="chevron" id="chev-outliers">▶</span>
      </div>
      <div class="section-body" id="body-outliers">
        ${Object.keys(r.outliers.columns).length === 0 ? '<p style="color:var(--muted);font-family:var(--mono);font-size:13px">No numeric columns found.</p>' :
        `<table class="dq-table">
          <thead><tr><th>Column</th><th>Outliers</th><th>Outlier %</th><th>Acceptable range</th></tr></thead>
          <tbody>${outlierRows}</tbody>
        </table>`}
      </div>
    </div>

    <div class="section">
      <div class="section-head" onclick="toggle('schema')">
        <div class="section-title">Schema & types ${pill(r.schema.has_issues)}</div>
        <span class="chevron" id="chev-schema">▶</span>
      </div>
      <div class="section-body" id="body-schema">
        <table class="dq-table">
          <thead><tr><th>Column</th><th>Type</th><th>Flags</th></tr></thead>
          <tbody>${schemaRows}</tbody>
        </table>
      </div>
    </div>
  `;

  document.getElementById('results').style.display = 'block';
  document.getElementById('results').innerHTML = html;
}

runBtn.addEventListener('click', async () => {
  if (!selectedFile) return;
  runBtn.disabled = true;
  document.getElementById('loader').style.display = 'block';
  document.getElementById('results').style.display = 'none';

  const form = new FormData();
  form.append('file', selectedFile);
  form.append('key_col', document.getElementById('key-col').value.trim());
  form.append('method', document.getElementById('method').value);

  try {
    const resp = await fetch('/analyse', { method: 'POST', body: form });
    const data = await resp.json();
    if (data.error) throw new Error(data.error);
    render(data);
  } catch(e) {
    document.getElementById('results').innerHTML = `<div style="color:var(--red);font-family:var(--mono);font-size:13px;padding:20px 0">Error: ${e.message}</div>`;
    document.getElementById('results').style.display = 'block';
  } finally {
    document.getElementById('loader').style.display = 'none';
    runBtn.disabled = false;
  }
});
</script>
</body>
</html>
"""


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────

@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/analyse", methods=["POST"])
def analyse():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    f = request.files["file"]
    if not f.filename.endswith(".csv"):
        return jsonify({"error": "Only CSV files are supported"}), 400

    key_col = request.form.get("key_col", "").strip() or None
    method = request.form.get("method", "IQR")
    if method not in ("IQR", "zscore"):
        method = "IQR"

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
            temp_path = tmp.name
            f.save(temp_path)

        df = pd.read_csv(temp_path)
    except Exception as e:
        return jsonify({"error": f"Could not read CSV: {str(e)}"}), 400
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                pass

    if df.empty:
        return jsonify({"error": "The CSV file is empty"}), 400

    # validate key_col exists
    if key_col and key_col not in df.columns:
        key_col = None

    report = run_full_report(
        df,
        source=f.filename,
        key_col=key_col,
        outlier_method=method,
    )

    return jsonify(report.to_dict())


if __name__ == "__main__":
    print("\n  DQChecker is running → http://localhost:5000\n")
    app.run(debug=True, port=5000)