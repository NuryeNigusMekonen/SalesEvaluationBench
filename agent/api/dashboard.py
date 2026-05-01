DASHBOARD_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Conversion Engine — Tenacious</title>
  <style>
    :root {
      --bg: #f5f7fb;
      --surface: #ffffff;
      --surface-soft: #f8fafc;
      --ink: #0f1f3d;
      --ink-mid: #334766;
      --muted: #64748b;
      --line: #dde4ee;
      --line-strong: #b8c6dc;
      --blue: #1f6feb;
      --blue-dark: #1554c0;
      --blue-soft: #eaf2ff;
      --green: #15803d;
      --green-soft: #dcfce7;
      --amber: #b45309;
      --amber-soft: #fef3c7;
      --red: #b91c1c;
      --red-soft: #fee2e2;
      --gray-soft: #f1f5f9;
      --sidebar-w: 216px;
      --radius: 8px;
      --shadow: 0 1px 3px rgba(15,31,61,.07), 0 4px 14px rgba(15,31,61,.05);
    }

    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
      font-size: 14px;
      color: var(--ink);
      background: var(--bg);
      line-height: 1.5;
    }

    a { color: inherit; text-decoration: none; }

    /* ── SHELL ─────────────────────────────── */
    .shell {
      display: grid;
      grid-template-columns: var(--sidebar-w) 1fr;
      min-height: 100vh;
    }

    /* ── SIDEBAR ───────────────────────────── */
    .sidebar {
      position: sticky;
      top: 0;
      height: 100vh;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      background: var(--surface);
      border-right: 1px solid var(--line);
      padding: 18px 10px;
      gap: 2px;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 2px 8px 16px;
      border-bottom: 1px solid var(--line);
      margin-bottom: 8px;
    }

    .brand-mark {
      width: 32px; height: 32px;
      border-radius: 8px;
      background: linear-gradient(135deg, #1f6feb, #5d8df8);
      color: #fff;
      font-size: 13px;
      font-weight: 800;
      display: grid; place-items: center;
      flex-shrink: 0;
    }

    .brand-text strong { display: block; font-size: 12.5px; font-weight: 700; color: var(--ink); }
    .brand-text small { font-size: 10.5px; color: var(--blue); font-weight: 600; text-transform: uppercase; letter-spacing: .06em; }

    .nav-section { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .08em; color: var(--muted); padding: 10px 8px 4px; }

    .nav a {
      display: flex;
      align-items: center;
      gap: 9px;
      height: 36px;
      padding: 0 8px;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 550;
      color: var(--ink-mid);
      transition: background .1s;
    }

    .nav a:hover, .nav a.active { background: var(--blue-soft); color: var(--blue-dark); font-weight: 650; }

    .nav-ic {
      width: 20px; height: 20px;
      border-radius: 5px;
      background: var(--gray-soft);
      color: var(--muted);
      font-size: 9.5px;
      font-weight: 800;
      display: grid; place-items: center;
      flex-shrink: 0;
    }
    .nav a.active .nav-ic, .nav a:hover .nav-ic { background: rgba(31,111,235,.14); color: var(--blue-dark); }

    .sidebar-footer {
      margin-top: auto;
      padding-top: 12px;
      border-top: 1px solid var(--line);
      display: grid;
      gap: 8px;
    }

    .util-links { display: flex; flex-wrap: wrap; gap: 5px; }
    .util-link {
      height: 26px;
      padding: 0 9px;
      border: 1px solid var(--line);
      border-radius: 5px;
      font-size: 11px;
      font-weight: 600;
      color: var(--muted);
      display: inline-flex;
      align-items: center;
    }
    .util-link:hover { color: var(--blue); border-color: var(--blue); }

    .team-row { display: flex; align-items: center; gap: 8px; }
    .avatar {
      width: 28px; height: 28px;
      border-radius: 50%;
      background: #143f7d;
      color: #fff;
      font-size: 10px;
      font-weight: 800;
      display: grid; place-items: center;
      flex-shrink: 0;
    }
    .team-info strong { display: block; font-size: 11.5px; font-weight: 700; }
    .team-info small { font-size: 10.5px; color: var(--muted); }

    /* ── WORKSPACE ─────────────────────────── */
    .workspace { min-width: 0; padding: 22px 26px 40px; }

    /* ── TOPBAR ────────────────────────────── */
    .topbar {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 16px;
      margin-bottom: 18px;
    }

    .page-title h1 { font-size: 20px; font-weight: 800; color: var(--ink); line-height: 1.2; }
    .page-title p { font-size: 12.5px; color: var(--muted); margin-top: 2px; }

    .actions { display: flex; gap: 7px; flex-shrink: 0; flex-wrap: wrap; }

    /* ── BUTTONS ───────────────────────────── */
    .btn {
      height: 34px;
      padding: 0 13px;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      border: 1px solid var(--line-strong);
      border-radius: 6px;
      background: var(--surface);
      font: 600 12.5px/1 inherit;
      color: var(--ink);
      cursor: pointer;
      box-shadow: 0 1px 2px rgba(0,0,0,.05);
      white-space: nowrap;
    }
    .btn:hover { border-color: var(--blue); color: var(--blue); }
    .btn-primary { background: var(--blue); border-color: var(--blue); color: #fff; }
    .btn-primary:hover { background: var(--blue-dark); border-color: var(--blue-dark); color: #fff; }
    button:disabled { opacity: .6; cursor: wait; }
    .btn-sm { height: 26px; padding: 0 9px; font-size: 11.5px; }

    /* ── KPI ROW ───────────────────────────── */
    .kpi-row {
      display: grid;
      grid-template-columns: repeat(6, 1fr);
      gap: 10px;
      margin-bottom: 16px;
    }

    .kpi {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      padding: 12px 14px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      box-shadow: var(--shadow);
    }

    .kpi-label { font-size: 10.5px; font-weight: 700; color: var(--muted); text-transform: uppercase; letter-spacing: .04em; }
    .kpi-value { font-size: 20px; font-weight: 800; color: var(--ink); line-height: 1.1; margin-top: 3px; }
    .kpi-value.sm { font-size: 13px; margin-top: 5px; }
    .kpi-icon {
      width: 36px; height: 36px;
      border-radius: 50%;
      background: var(--blue-soft);
      display: grid; place-items: center;
      font-size: 10px;
      font-weight: 800;
      color: var(--blue-dark);
      flex-shrink: 0;
    }
    .kpi.green .kpi-value { color: var(--green); }
    .kpi.green .kpi-icon { background: var(--green-soft); color: var(--green); }

    /* ── GRID HELPERS ──────────────────────── */
    .g2 { display: grid; grid-template-columns: 1fr 1fr; gap: 13px; }
    .g3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 13px; }
    .g5 { display: grid; grid-template-columns: repeat(5, 1fr); gap: 13px; }
    .span2 { grid-column: span 2; }
    .span3 { grid-column: span 3; }
    .mb { margin-bottom: 13px; }
    .mt { margin-top: 16px; }

    /* ── CARD ──────────────────────────────── */
    .card {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
    }

    .card-hd {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
      padding: 13px 16px 0;
    }

    .card-title {
      display: flex;
      align-items: center;
      gap: 7px;
      font-size: 12.5px;
      font-weight: 700;
      color: var(--ink);
    }

    .card-icon {
      width: 24px; height: 24px;
      border-radius: 5px;
      background: var(--blue-soft);
      display: grid; place-items: center;
      font-size: 9px;
      font-weight: 800;
      color: var(--blue-dark);
      flex-shrink: 0;
    }

    .card-body { padding: 12px 16px 16px; }
    .card-pad { padding: 14px 16px 16px; }

    /* ── SECTION HEADING ───────────────────── */
    .sec-hd {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      margin: 18px 0 10px;
    }
    .sec-hd h2 { font-size: 13px; font-weight: 700; color: var(--ink); }
    .sec-hd p { font-size: 12px; color: var(--muted); }

    /* ── BADGES / CHIPS ────────────────────── */
    .badge, .chip {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      height: 20px;
      padding: 0 7px;
      border-radius: 999px;
      font-size: 11px;
      font-weight: 700;
      white-space: nowrap;
      line-height: 1;
    }

    .brow, .crow { display: flex; flex-wrap: wrap; gap: 5px; }

    .s-ok  { background: var(--green-soft); color: var(--green); }
    .s-warn{ background: var(--amber-soft); color: var(--amber); }
    .s-err { background: var(--red-soft);   color: var(--red); }
    .s-info{ background: var(--blue-soft);  color: var(--blue-dark); }
    .s-nil { background: var(--gray-soft);  color: var(--muted); }
    .s-draft{ background: #ede9fe;          color: #5b21b6; }
    .s-live { background: var(--green-soft);color: var(--green); }

    /* ── KV LIST ───────────────────────────── */
    .kv { display: grid; gap: 1px; background: var(--line); border: 1px solid var(--line); border-radius: 7px; overflow: hidden; }
    .kvr {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
      padding: 7px 10px;
      background: var(--surface);
      font-size: 12.5px;
    }
    .kk { color: var(--muted); font-weight: 600; flex-shrink: 0; }
    .kv-val { color: var(--ink); font-weight: 600; text-align: right; max-width: 60%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

    /* ── SIGNAL ROWS ───────────────────────── */
    .sig-list { display: grid; gap: 7px; }
    .sig-row {
      display: grid;
      grid-template-columns: 24px 1fr auto;
      gap: 8px;
      align-items: start;
      padding: 9px;
      background: var(--surface-soft);
      border: 1px solid var(--line);
      border-radius: 6px;
    }
    .sig-dot {
      width: 22px; height: 22px;
      border-radius: 50%;
      background: var(--blue);
      color: #fff;
      display: grid; place-items: center;
      font-size: 9px;
      font-weight: 800;
    }
    .sig-name { font-size: 12px; font-weight: 700; color: var(--ink); }
    .sig-txt {
      font-size: 11.5px;
      color: var(--muted);
      display: -webkit-box;
      -webkit-box-orient: vertical;
      -webkit-line-clamp: 2;
      overflow: hidden;
      margin-top: 2px;
    }

    /* ── CAPACITY BAR ──────────────────────── */
    .cap-list { display: grid; gap: 9px; }
    .cap-hd { display: flex; justify-content: space-between; font-size: 11.5px; font-weight: 700; color: var(--ink-mid); }
    .cap-bar { height: 6px; border-radius: 999px; background: #d8dee8; overflow: hidden; margin-top: 4px; }
    .cap-bar span { display: block; height: 100%; border-radius: inherit; background: linear-gradient(90deg, var(--blue), #60a5fa); }

    /* ── TOOL GRID ─────────────────────────── */
    .tool-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 5px; }
    .tool-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 6px;
      padding: 6px 9px;
      background: var(--surface-soft);
      border: 1px solid var(--line);
      border-radius: 5px;
      font-size: 12px;
      font-weight: 600;
      color: var(--ink);
    }

    /* ── EMAIL PREVIEW ─────────────────────── */
    .email-wrap {
      background: linear-gradient(180deg, #f9fbff, #fff);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      overflow: hidden;
    }
    .email-meta {
      padding: 9px 12px;
      border-bottom: 1px solid var(--line);
      display: grid;
      gap: 3px;
      font-size: 12px;
    }
    .email-meta strong { color: var(--ink); font-weight: 700; }
    .email-meta span { color: var(--muted); }
    .email-body {
      padding: 9px 12px;
      font-size: 12px;
      color: #172b4d;
      line-height: 1.55;
      display: -webkit-box;
      -webkit-box-orient: vertical;
      -webkit-line-clamp: 4;
      overflow: hidden;
      white-space: pre-wrap;
    }
    .email-foot { padding: 7px 12px; border-top: 1px solid var(--line); display: flex; gap: 5px; }

    /* ── TABLES ────────────────────────────── */
    .tbl-wrap { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; font-size: 12.5px; }
    thead th {
      padding: 7px 9px;
      text-align: left;
      font-size: 10.5px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: .04em;
      color: var(--muted);
      border-bottom: 1px solid var(--line);
      white-space: nowrap;
    }
    tbody td {
      padding: 9px 9px;
      border-bottom: 1px solid var(--line);
      color: var(--ink-mid);
      vertical-align: middle;
    }
    tbody tr:last-child td { border-bottom: 0; }
    tbody tr:hover td { background: var(--surface-soft); }

    /* ── TIMELINE ──────────────────────────── */
    .tl { display: grid; gap: 0; position: relative; }
    .tl-item {
      display: grid;
      grid-template-columns: 16px 1fr;
      gap: 10px;
      position: relative;
    }
    .tl-item::before {
      content: '';
      position: absolute;
      left: 5px; top: 18px; bottom: 0;
      width: 1px;
      background: var(--line);
    }
    .tl-item:last-child::before { display: none; }
    .tl-dot {
      width: 12px; height: 12px;
      border-radius: 50%;
      background: var(--blue);
      border: 2px solid var(--blue-soft);
      margin-top: 4px;
      flex-shrink: 0;
    }
    .tl-body { padding-bottom: 12px; }
    .tl-evt { font-size: 12.5px; font-weight: 700; color: var(--ink); }
    .tl-txt { font-size: 11.5px; color: var(--muted); margin-top: 2px; display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 2; overflow: hidden; }
    .tl-meta { display: flex; gap: 5px; margin-top: 5px; flex-wrap: wrap; align-items: center; }

    /* ── ARTIFACT CARDS ────────────────────── */
    .art-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
    .art-card {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      padding: 12px;
      display: grid;
      gap: 7px;
      box-shadow: var(--shadow);
    }
    .art-title { font-size: 12.5px; font-weight: 700; color: var(--ink); display: flex; align-items: center; gap: 6px; }
    .art-preview { font-size: 11.5px; color: var(--muted); display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 2; overflow: hidden; line-height: 1.45; }

    /* ── FACT GRID ─────────────────────────── */
    .fact-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      border: 1px solid var(--line);
      border-radius: 7px;
      overflow: hidden;
    }
    .fact { padding: 9px 11px; background: var(--surface-soft); border-right: 1px solid var(--line); border-bottom: 1px solid var(--line); }
    .fact:nth-child(4n) { border-right: 0; }
    .fact:nth-last-child(-n+4) { border-bottom: 0; }
    .fact-lbl { font-size: 10px; font-weight: 700; color: var(--muted); text-transform: uppercase; letter-spacing: .04em; }
    .fact-val { font-size: 12.5px; font-weight: 700; color: var(--ink); margin-top: 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

    /* ── COMPANY TILE ──────────────────────── */
    .co-tile { display: flex; gap: 12px; align-items: flex-start; padding: 14px 16px; border-left: 1px solid var(--line); }
    .logo-tile {
      width: 48px; height: 48px;
      border-radius: 9px;
      background: linear-gradient(135deg, #081735, #1e3a6e);
      color: #fff;
      font-size: 14px;
      font-weight: 900;
      display: grid; place-items: center;
      flex-shrink: 0;
      box-shadow: 0 4px 10px rgba(8,23,53,.18);
    }
    .co-name { font-size: 13.5px; font-weight: 700; color: var(--ink); }
    .co-desc { font-size: 12px; color: var(--muted); margin-top: 3px; display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 3; overflow: hidden; }

    /* ── FLOW LAYOUT ───────────────────────── */
    .flow-layout { display: grid; grid-template-columns: 1fr 190px; }
    .flow-left { display: grid; gap: 12px; padding: 12px 16px 16px; }

    /* ── FORM ──────────────────────────────── */
    .form-grid { display: grid; gap: 9px; }
    .form-field { display: grid; gap: 3px; }
    .form-label { font-size: 11.5px; font-weight: 700; color: var(--ink-mid); }
    input {
      height: 34px;
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 0 9px;
      font: 13px/1 inherit;
      color: var(--ink);
      background: var(--surface);
      box-shadow: inset 0 1px 2px rgba(0,0,0,.04);
    }
    input:focus { outline: 2px solid rgba(31,111,235,.18); border-color: var(--blue); }
    select {
      height: 34px;
      border: 1px solid var(--line-strong);
      border-radius: 6px;
      padding: 0 9px;
      font: 600 12.5px/1 inherit;
      color: var(--ink);
      background: var(--surface);
      cursor: pointer;
    }
    .status-txt { font-size: 12.5px; font-weight: 600; color: var(--blue-dark); min-height: 18px; }

    /* ── CHECKLIST ─────────────────────────── */
    .cklist { display: grid; gap: 7px; }
    .ck-row { display: flex; align-items: center; gap: 7px; font-size: 12.5px; color: var(--ink-mid); font-weight: 550; }

    /* ── CONFIG GRID ───────────────────────── */
    .cfg-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
    .cfg-card {
      padding: 11px 13px;
      background: var(--surface-soft);
      border: 1px solid var(--line);
      border-radius: 6px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 8px;
    }
    .cfg-name { font-size: 12.5px; font-weight: 700; color: var(--ink); }
    .cfg-detail { font-size: 11px; color: var(--muted); margin-top: 2px; }

    /* ── GUARDRAILS STRIP ──────────────────── */
    .gr-strip {
      margin-top: 18px;
      padding: 12px 16px;
      background: var(--surface);
      border: 1px solid #9fb9ea;
      border-radius: var(--radius);
      display: flex;
      align-items: center;
      gap: 0;
    }
    .gr-label {
      display: flex;
      align-items: center;
      gap: 7px;
      font-size: 12.5px;
      font-weight: 700;
      color: var(--ink);
      padding-right: 14px;
      margin-right: 14px;
      border-right: 1px solid var(--line);
      white-space: nowrap;
      flex-shrink: 0;
    }
    .gr-items { display: flex; gap: 14px; flex-wrap: wrap; flex: 1; align-items: center; }
    .gr-item {
      display: flex;
      align-items: flex-start;
      gap: 6px;
      font-size: 12px;
      color: #1e3358;
      line-height: 1.4;
      font-weight: 550;
      max-width: 190px;
    }

    /* ── EMPTY STATE ───────────────────────── */
    .empty {
      padding: 18px;
      border: 1px dashed var(--line-strong);
      border-radius: var(--radius);
      color: var(--muted);
      font-size: 12.5px;
      text-align: center;
    }

    /* ── PAGE VISIBILITY ───────────────────── */
    .page { display: contents; }
    .page[hidden] { display: none !important; }

    /* ── HINT BOX ──────────────────────────── */
    .hint {
      margin-top: 8px;
      padding: 7px 10px;
      border-radius: 6px;
      background: var(--blue-soft);
      color: #28446f;
      font-size: 11.5px;
      font-weight: 600;
      line-height: 1.45;
      display: -webkit-box;
      -webkit-box-orient: vertical;
      -webkit-line-clamp: 2;
      overflow: hidden;
    }

    /* ── SIMULATOR ────────────────────────── */
    .sim-co-header { display:flex; align-items:center; gap:8px; margin-bottom:8px; }
    .sim-co-count { font-size:12px; color:var(--muted); font-weight:600; }
    .sim-co-search { flex:1; padding:5px 9px; border:1.5px solid var(--line); border-radius:6px; font-size:12px; background:var(--surface); color:var(--ink); outline:none; }
    .sim-co-search:focus { border-color:var(--blue); }
    .sim-companies { display:flex; flex-direction:column; gap:4px; margin-bottom:14px; max-height:220px; overflow-y:auto; }
    .sim-co-pill { display:inline-flex; align-items:center; gap:4px; padding:1px 6px; border-radius:4px; font-size:10px; font-weight:700; flex-shrink:0; }
    .pill-new { background:var(--blue-soft); color:var(--blue-dark); }
    .pill-active { background:var(--green-soft); color:var(--green); }
    .sim-co {
      display:flex; align-items:center; justify-content:space-between; gap:8px;
      border:1.5px solid var(--line);
      border-radius:7px;
      padding:7px 11px;
      cursor:pointer;
      background:var(--surface);
      transition:border-color .13s, background .13s;
    }
    .sim-co:hover { border-color:var(--blue); background:var(--blue-soft); }
    .sim-co.selected { border-color:var(--blue); background:var(--blue-soft); }
    .sim-co-name { font-size:12.5px; font-weight:700; color:var(--ink); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
    .sim-co-meta { font-size:10.5px; color:var(--muted); margin-top:1px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
    .sim-thread {
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
      max-height: 520px;
      overflow-y: auto;
    }
    .sim-msg {
      padding: 12px 16px;
      border-bottom: 1px solid var(--line);
      display: flex;
      gap: 10px;
      align-items: flex-start;
    }
    .sim-msg:last-child { border-bottom: 0; }
    .sim-msg.prospect { background: var(--surface-soft); }
    .sim-msg.system { background: var(--blue-soft); }
    .sim-msg.sms-note { background: var(--green-soft); }
    .sim-msg.error { background: var(--red-soft); }
    .sim-avatar {
      width: 30px; height: 30px; border-radius: 50%;
      display: grid; place-items: center;
      font-size: 10px; font-weight: 800; flex-shrink: 0;
    }
    .sim-avatar.p { background: #e0e7ef; color: var(--ink-mid); }
    .sim-avatar.s { background: var(--blue); color: #fff; }
    .sim-avatar.sms { background: var(--green); color: #fff; }
    .sim-msg-body { flex: 1; min-width: 0; }
    .sim-msg-who { font-size: 10.5px; font-weight: 700; color: var(--muted); margin-bottom: 3px; }
    .sim-msg-text { font-size: 12.5px; color: var(--ink); white-space: pre-wrap; line-height: 1.5; }
    .sim-badges { display: flex; gap: 5px; flex-wrap: wrap; margin-top: 6px; }
    .sim-empty { padding: 32px; text-align: center; color: var(--muted); font-size: 12.5px; }
    .sim-status { font-size: 12px; color: var(--muted); min-height: 20px; margin-top: 6px; }
    .judge-toggle {
      display: flex; align-items: center; gap: 8px;
      padding: 9px 10px; border: 1px solid var(--line);
      border-radius: 7px; background: var(--surface-soft);
      font-size: 12px; font-weight: 650; color: var(--ink-mid);
    }
    .judge-toggle input { width: 16px; height: 16px; accent-color: var(--blue); }
    .comparison-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 9px; }
    .comparison-panel { border: 1px solid var(--line); border-radius: 8px; background: var(--surface); padding: 10px; }
    .comparison-panel.blocked { background: var(--gray-soft); color: var(--muted); }
    .comparison-title { font-size: 10.5px; font-weight: 800; text-transform: uppercase; letter-spacing: .05em; color: var(--muted); margin-bottom: 6px; }
    .comparison-body { font-size: 12px; white-space: pre-wrap; color: var(--ink); line-height: 1.45; }
    .comparison-meta { display:flex; gap:5px; flex-wrap:wrap; margin-top:8px; }
    .judge-pass { color: var(--green); background: var(--green-soft); }
    .judge-fail { color: var(--red); background: var(--red-soft); }
    .judge-review { color: var(--amber); background: var(--amber-soft); }

    /* ── RESPONSIVE ────────────────────────── */
    @media (max-width: 1280px) {
      .kpi-row { grid-template-columns: repeat(3, 1fr); }
      .g5 { grid-template-columns: repeat(3, 1fr); }
    }
    @media (max-width: 960px) {
      .shell { grid-template-columns: 1fr; }
      .sidebar { position: static; height: auto; flex-direction: row; flex-wrap: wrap; padding: 10px; gap: 4px; }
      .brand { padding: 0; border: 0; margin: 0; }
      .nav { display: flex; flex-wrap: wrap; gap: 3px; }
      .nav-section, .sidebar-footer { display: none; }
      .kpi-row { grid-template-columns: repeat(2, 1fr); }
      .g2, .g3, .g5 { grid-template-columns: 1fr; }
      .span2, .span3 { grid-column: auto; }
      .flow-layout { grid-template-columns: 1fr; }
      .co-tile { border-left: 0; border-top: 1px solid var(--line); }
      .art-grid { grid-template-columns: 1fr 1fr; }
      .tool-grid { grid-template-columns: 1fr; }
      .fact-grid { grid-template-columns: repeat(2, 1fr); }
      .cfg-grid { grid-template-columns: 1fr; }
      .comparison-grid { grid-template-columns: 1fr; }
    }
    @media (max-width: 600px) {
      .workspace { padding: 14px; }
      .kpi-row, .art-grid { grid-template-columns: 1fr; }
      .fact-grid { grid-template-columns: 1fr 1fr; }
      .actions { flex-wrap: wrap; }
    }
  </style>
</head>
<body>
<div class="shell">

  <!-- ═══════════════════ SIDEBAR ═══════════════════ -->
  <aside class="sidebar">
    <div class="brand">
      <div class="brand-mark">T</div>
      <div class="brand-text">
        <strong>TENACIOUS</strong>
        <small>Conversion Engine</small>
      </div>
    </div>

    <div class="nav-section">Main</div>
    <nav class="nav">
      <a href="#overview"  data-page="overview" ><span class="nav-ic">OV</span>Overview</a>
      <a href="#prospects" data-page="prospects"><span class="nav-ic">PR</span>Prospects</a>
      <a href="#outreach"  data-page="outreach" ><span class="nav-ic">OU</span>Outreach</a>
      <a href="#signals"   data-page="signals"  ><span class="nav-ic">SI</span>Signals</a>
      <a href="#meetings"  data-page="meetings" ><span class="nav-ic">ME</span>Meetings</a>
    </nav>

    <div class="nav-section">Testing</div>
    <nav class="nav">
      <a href="#simulator" data-page="simulator"><span class="nav-ic">&#9654;</span>Simulator</a>
    </nav>

    <div class="nav-section">Ops</div>
    <nav class="nav">
      <a href="#crm"      data-page="crm"     ><span class="nav-ic">CR</span>CRM</a>
      <a href="#traces"   data-page="traces"  ><span class="nav-ic">TR</span>Traces</a>
      <a href="#settings" data-page="settings"><span class="nav-ic">SE</span>Settings</a>
    </nav>

    <div class="sidebar-footer">
      <div class="util-links">
        <a class="util-link" href="/docs">API Docs</a>
        <a class="util-link" href="/health">Health</a>
        <a class="util-link" href="/tools/status">Tools JSON</a>
      </div>
      <div class="team-row">
        <div class="avatar">TS</div>
        <div class="team-info">
          <strong>Tenacious Team</strong>
          <small>tenacious@tenacious.ai</small>
        </div>
      </div>
    </div>
  </aside>

  <!-- ═══════════════════ WORKSPACE ═══════════════════ -->
  <main class="workspace">

    <!-- ████████████  OVERVIEW PAGE  ████████████ -->
    <section class="page" id="page-overview">
      <div class="topbar">
        <div class="page-title">
          <h1>Conversion Engine</h1>
          <p>Email-first research, qualification, scheduling, CRM sync, and trace review.</p>
        </div>
        <div class="actions">
          <a class="btn" id="export-brief" href="/dashboard/state">&#8681; Export Brief</a>
          <a class="btn" id="hubspot-link" href="/tools/status">HS Open HubSpot</a>
          <button class="btn btn-primary" id="run-demo-button">&#9654; Run Demo</button>
        </div>
      </div>

      <!-- KPI ROW -->
      <div class="kpi-row">
        <div class="kpi">
          <div><div class="kpi-label">Prospects</div><div class="kpi-value" id="kpi-prospects">—</div></div>
          <div class="kpi-icon">PR</div>
        </div>
        <div class="kpi">
          <div><div class="kpi-label">Trace Events</div><div class="kpi-value" id="kpi-traces">—</div></div>
          <div class="kpi-icon">TR</div>
        </div>
        <div class="kpi">
          <div><div class="kpi-label">Channel</div><div class="kpi-value sm">Email</div></div>
          <div class="kpi-icon">EM</div>
        </div>
        <div class="kpi">
          <div><div class="kpi-label">Outbound Mode</div><div class="kpi-value sm" id="kpi-mode">Preview</div></div>
          <div class="kpi-icon">SH</div>
        </div>
        <div class="kpi green">
          <div><div class="kpi-label">Health</div><div class="kpi-value sm" id="kpi-health">Checking…</div></div>
          <div class="kpi-icon">OK</div>
        </div>
        <div class="kpi">
          <div><div class="kpi-label">Benchmark</div><div class="kpi-value sm" id="kpi-bench">&#964;&#178;-Bench</div></div>
          <div class="kpi-icon">BN</div>
        </div>
      </div>

      <!-- ROW 1 -->
      <div class="g2 mb">
        <!-- 1. Create Brief -->
        <div class="card">
          <div class="card-hd"><div class="card-title"><span class="card-icon">BR</span>1. Create Prospect Brief</div></div>
          <div class="card-body">
            <form id="prospect-form" class="form-grid">
              <div class="form-field">
                <label class="form-label">Company Name</label>
                <input name="company_name" required placeholder="Northstar Labs" />
              </div>
              <div class="g2" style="gap:7px">
                <div class="form-field"><label class="form-label">Domain</label><input name="company_domain" placeholder="northstarlabs.ai" /></div>
                <div class="form-field"><label class="form-label">Contact Name</label><input name="contact_name" placeholder="Jordan Lee" /></div>
              </div>
              <div class="g2" style="gap:7px">
                <div class="form-field"><label class="form-label">Email</label><input name="contact_email" type="email" placeholder="jordan@northstarlabs.ai" /></div>
                <div class="form-field"><label class="form-label">Phone</label><input name="contact_phone" placeholder="+254700000000" /></div>
              </div>
              <button class="btn btn-primary" id="submit-button" type="submit" style="width:100%;justify-content:center">&#9654; Run Full Toolchain</button>
              <div class="status-txt" id="status"></div>
            </form>
          </div>
        </div>

        <!-- 2. Latest Flow -->
        <div class="card">
          <div class="card-hd">
            <div class="card-title"><span class="card-icon">FL</span>2. Latest Flow</div>
            <span class="badge s-nil" id="latest-event-badge">No recent event</span>
          </div>
          <div id="latest-flow-body">
            <div class="card-body"><div class="empty">No interaction flow recorded yet.</div></div>
          </div>
        </div>
      </div>

      <!-- Intelligence heading -->
      <div class="sec-hd">
        <div><h2>Intelligence</h2><p>Prospect snapshot · hiring signals · bench fit · competitor gap · outreach draft.</p></div>
        <span class="badge s-info" id="selected-trace">Trace pending</span>
      </div>

      <!-- INTELLIGENCE GRID -->
      <div class="g5 mb" id="intelligence-grid">
        <div class="card card-pad"><div class="card-title mb" style="margin-bottom:9px"><span class="card-icon">A</span>Prospect Snapshot</div><div class="empty">Run toolchain.</div></div>
        <div class="card card-pad"><div class="card-title mb" style="margin-bottom:9px"><span class="card-icon">B</span>Hiring Signals</div><div class="empty">Run toolchain.</div></div>
        <div class="card card-pad"><div class="card-title mb" style="margin-bottom:9px"><span class="card-icon">C</span>Bench Match</div><div class="empty">Run toolchain.</div></div>
        <div class="card card-pad"><div class="card-title mb" style="margin-bottom:9px"><span class="card-icon">D</span>Competitor Gap</div><div class="empty">Run toolchain.</div></div>
        <div class="card card-pad"><div class="card-title mb" style="margin-bottom:9px"><span class="card-icon">E</span>Outreach Draft</div><div class="empty">Run toolchain.</div></div>
      </div>

      <!-- Operational heading -->
      <div class="sec-hd">
        <div><h2>Operational Evidence</h2><p>Toolchain status · prospects · trace events · generated artifacts.</p></div>
      </div>

      <!-- ROW: Toolchain + Prospects + Traces -->
      <div class="g3 mb">
        <div class="card">
          <div class="card-hd"><div class="card-title"><span class="card-icon">TL</span>Toolchain Results</div></div>
          <div class="card-body"><div id="tool-statuses" class="tool-grid"><div class="empty">Loading…</div></div></div>
        </div>
        <div class="card">
          <div class="card-hd">
            <div class="card-title"><span class="card-icon">RP</span>Recent Prospects</div>
            <a class="btn btn-sm" href="#prospects" data-page="prospects">View all</a>
          </div>
          <div class="card-body" style="padding-top:8px"><div id="recent-prospects"><div class="empty">No prospects yet.</div></div></div>
        </div>
        <div class="card">
          <div class="card-hd">
            <div class="card-title"><span class="card-icon">RT</span>Recent Traces</div>
            <a class="btn btn-sm" href="#traces" data-page="traces">View all</a>
          </div>
          <div class="card-body" style="padding-top:8px"><div id="recent-traces"><div class="empty">No trace events.</div></div></div>
        </div>
      </div>

      <!-- Artifacts -->
      <div class="card mb">
        <div class="card-hd" style="padding-bottom:12px"><div class="card-title"><span class="card-icon">AR</span>Latest Artifacts</div></div>
        <div class="card-body" style="padding-top:0"><div id="latest-artifacts" class="art-grid"><div class="empty">No artifacts yet.</div></div></div>
      </div>

      <!-- Guardrails -->
      <div class="gr-strip">
        <div class="gr-label"><span class="card-icon">GR</span>Guardrails</div>
        <div class="gr-items">
          <div class="gr-item"><span class="badge s-info">&#10003;</span>Do not promise staffing capacity without bench confirmation.</div>
          <div class="gr-item"><span class="badge s-info">&#10003;</span>Do not frame outreach around unobserved leadership transitions.</div>
          <div class="gr-item"><span class="badge s-info">&#10003;</span>Respect quiet hours &amp; outreach limits.</div>
          <div class="gr-item"><span class="badge s-info">i</span>AI outputs are suggestions — review before sending.</div>
        </div>
      </div>
    </section><!-- /overview -->


    <!-- ████████████  PROSPECTS PAGE  ████████████ -->
    <section class="page" id="page-prospects" hidden>
      <div class="topbar">
        <div class="page-title"><h1>Prospects</h1><p>Lead research pipeline — qualification, segmentation, and brief links.</p></div>
        <div class="actions"><button class="btn" id="prospects-refresh">&#8635; Refresh</button></div>
      </div>

      <div class="brow mb" id="segment-chips"></div>

      <div class="card">
        <div class="card-hd">
          <div class="card-title"><span class="card-icon">PR</span>All Prospects</div>
          <input id="prospects-search" placeholder="Search company or segment…" style="width:200px;height:30px;font-size:12px" />
        </div>
        <div class="card-body" style="padding-top:8px">
          <div class="tbl-wrap">
            <table>
              <thead><tr><th>Company</th><th>Segment</th><th>Confidence</th><th>AI Maturity</th><th>Status</th><th>Last Updated</th><th>Brief</th><th>Re-run</th></tr></thead>
              <tbody id="prospects-tbody"><tr><td colspan="8"><div class="empty">No prospects yet.</div></td></tr></tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Re-run status -->
      <div style="margin-top:10px;min-height:20px">
        <span class="status-txt" id="rerun-status"></span>
      </div>
    </section><!-- /prospects -->


    <!-- ████████████  OUTREACH PAGE  ████████████ -->
    <section class="page" id="page-outreach" hidden>
      <div class="topbar">
        <div class="page-title"><h1>Outreach</h1><p>Email drafts, SMS handoff, reply management, and provider status.</p></div>
      </div>

      <div class="g3 mb">
        <div class="card card-pad">
          <div class="card-title" style="margin-bottom:10px"><span class="card-icon">EM</span>Email Channel</div>
          <div class="kv" id="out-email-kv"></div>
        </div>
        <div class="card card-pad">
          <div class="card-title" style="margin-bottom:10px"><span class="card-icon">SM</span>SMS Handoff</div>
          <div class="kv" id="out-sms-kv"></div>
        </div>
        <div class="card card-pad">
          <div class="card-title" style="margin-bottom:10px"><span class="card-icon">CA</span>Scheduling</div>
          <div class="kv" id="out-cal-kv"></div>
        </div>
      </div>

      <div class="sec-hd"><div><h2>Latest Outreach Draft</h2><p>Current draft / live email for the most recent prospect.</p></div></div>
      <div class="card mb" id="out-draft-card"><div class="card-body"><div class="empty">No outreach draft yet.</div></div></div>

      <!-- Simulate Reply panel -->
      <div class="sec-hd"><div><h2>Simulate Inbound Reply</h2><p>Test how the conversation engine handles different prospect reply types.</p></div></div>
      <div class="card mb">
        <div class="card-body">
          <form id="reply-sim-form" class="form-grid">
            <div class="g3" style="gap:8px">
              <div class="form-field">
                <label class="form-label">Prospect ID (optional)</label>
                <input id="reply-prospect-id" placeholder="pros_… or leave blank for latest" />
              </div>
              <div class="form-field">
                <label class="form-label">Contact Email (optional)</label>
                <input id="reply-contact-email" type="email" placeholder="contact@company.ai" />
              </div>
              <div class="form-field">
                <label class="form-label">Channel</label>
                <select id="reply-channel" style="height:34px">
                  <option value="email">Email</option>
                  <option value="sms">SMS</option>
                  <option value="voice">Voice</option>
                </select>
              </div>
            </div>
            <div class="brow" style="gap:6px">
              <span style="font-size:12px;font-weight:600;color:var(--muted);align-self:center">Quick fill:</span>
              <button type="button" class="btn btn-sm" id="qf-meeting">Meeting request</button>
              <button type="button" class="btn btn-sm" id="qf-pricing">Pricing question</button>
              <button type="button" class="btn btn-sm" id="qf-normal">Normal reply</button>
              <button type="button" class="btn btn-sm" id="qf-opt-out">Opt-out</button>
            </div>
            <div class="form-field">
              <label class="form-label">Message Body</label>
              <textarea id="reply-body" rows="3" style="width:100%;border:1px solid var(--line);border-radius:6px;padding:8px 10px;font:13px/1.5 inherit;color:var(--ink);background:var(--surface);resize:vertical" placeholder="Hi, thanks for reaching out. I'd like to schedule a call…"></textarea>
            </div>
            <div style="display:flex;gap:8px;align-items:center">
              <button type="submit" class="btn btn-primary" id="reply-sim-btn">&#9654; Send Simulated Reply</button>
              <span class="status-txt" id="reply-sim-status"></span>
            </div>
          </form>
          <!-- Reply decision output -->
          <div id="reply-decision-out" style="margin-top:14px;display:none">
            <div class="card-title" style="margin-bottom:8px"><span class="card-icon">DE</span>Decision</div>
            <div class="kv" id="reply-decision-kv"></div>
            <div id="reply-draft-preview" style="margin-top:10px"></div>
          </div>
        </div>
      </div>

      <div class="sec-hd"><div><h2>Inbound Reply Events</h2><p>Reply type classification and conversation decisions.</p></div></div>
      <div class="card">
        <div class="card-body">
          <div class="tbl-wrap">
            <table>
              <thead><tr><th>Event</th><th>Prospect</th><th>Reply Type</th><th>Provider</th><th>Timestamp</th><th>Trace</th></tr></thead>
              <tbody id="out-replies-tbody"><tr><td colspan="6"><div class="empty">No reply events recorded.</div></td></tr></tbody>
            </table>
          </div>
        </div>
      </div>
    </section><!-- /outreach -->


    <!-- ████████████  SIGNALS PAGE  ████████████ -->
    <section class="page" id="page-signals" hidden>
      <div class="topbar">
        <div class="page-title"><h1>Signals</h1><p>Public evidence quality, enrichment sources, and hiring intelligence.</p></div>
      </div>

      <div class="brow mb">
        <span class="badge s-info">Crunchbase</span>
        <span class="badge s-info">Job Posts</span>
        <span class="badge s-info">layoffs.fyi</span>
        <span class="badge s-info">Leadership</span>
      </div>

      <div class="g2">
        <div class="card">
          <div class="card-hd">
            <div class="card-title"><span class="card-icon">SI</span>Latest Signal Brief</div>
            <span class="badge s-nil" id="sig-company-badge">No prospect</span>
          </div>
          <div class="card-body"><div id="sig-list" class="sig-list"><div class="empty">Run the toolchain to generate signal data.</div></div></div>
        </div>
        <div class="card card-pad">
          <div class="card-title" style="margin-bottom:10px"><span class="card-icon">AI</span>AI Maturity &amp; Evidence</div>
          <div class="kv mb" id="sig-meta-kv"></div>
          <div class="card-title" style="margin-bottom:7px;margin-top:12px">Evidence Gaps</div>
          <div id="evidence-gaps"><div class="empty">No gaps reported.</div></div>
        </div>
      </div>
    </section><!-- /signals -->


    <!-- ████████████  MEETINGS PAGE  ████████████ -->
    <section class="page" id="page-meetings" hidden>
      <div class="topbar">
        <div class="page-title"><h1>Meetings</h1><p>Cal.com booking links, discovery call briefs, and calendar webhook status.</p></div>
      </div>

      <div class="g3">
        <div class="card card-pad">
          <div class="card-title" style="margin-bottom:10px"><span class="card-icon">CA</span>Cal.com Status</div>
          <div class="kv" id="mtg-cal-kv"></div>
        </div>
        <div class="card card-pad">
          <div class="card-title" style="margin-bottom:10px"><span class="card-icon">BK</span>Booking Summary</div>
          <div class="kv" id="mtg-booking-kv"></div>
        </div>
        <div class="card card-pad">
          <div class="card-title" style="margin-bottom:10px"><span class="card-icon">CB</span>Context Brief</div>
          <div id="mtg-ctx-brief"><div class="empty">No context brief yet.</div></div>
        </div>
      </div>
    </section><!-- /meetings -->


    <!-- ████████████  CRM PAGE  ████████████ -->
    <section class="page" id="page-crm" hidden>
      <div class="topbar">
        <div class="page-title"><h1>CRM</h1><p>HubSpot contact sync, field completeness, and lifecycle stage tracking.</p></div>
        <div class="actions"><a class="btn" id="crm-hubspot-link" href="/tools/status">Open HubSpot &#8599;</a></div>
      </div>

      <div class="g2 mb">
        <div class="card">
          <div class="card-hd">
            <div class="card-title"><span class="card-icon">HS</span>HubSpot Contact</div>
            <span class="badge s-nil" id="crm-sync-badge">Not synced</span>
          </div>
          <div class="card-body"><div class="kv" id="crm-contact-kv"></div></div>
        </div>
        <div class="card">
          <div class="card-hd">
            <div class="card-title"><span class="card-icon">FC</span>Field Completeness</div>
            <span class="badge s-nil" id="crm-score-badge">—</span>
          </div>
          <div class="card-body"><div id="crm-checklist" class="cklist"><div class="empty">No CRM data yet.</div></div></div>
        </div>
      </div>

      <div class="sec-hd"><div><h2>CRM Activity Log</h2><p>Field writes, sync events, and custom property updates.</p></div></div>
      <div class="card">
        <div class="card-body">
          <div class="tbl-wrap">
            <table>
              <thead><tr><th>Event</th><th>Field / Property</th><th>Value</th><th>Timestamp</th><th>Status</th></tr></thead>
              <tbody id="crm-activity-tbody"><tr><td colspan="5"><div class="empty">No CRM activity yet.</div></td></tr></tbody>
            </table>
          </div>
        </div>
      </div>
    </section><!-- /crm -->


    <!-- ████████████  TRACES PAGE  ████████████ -->
    <section class="page" id="page-traces" hidden>
      <div class="topbar">
        <div class="page-title"><h1>Traces</h1><p>Execution timeline, tool steps, event sequences, and Langfuse observability.</p></div>
        <div class="actions">
          <select id="traces-filter-type">
            <option value="">All event types</option>
            <option value="toolchain_run">toolchain_run</option>
            <option value="prospect_enriched">prospect_enriched</option>
            <option value="inbound_reply_handled">inbound_reply_handled</option>
            <option value="webhook_received">webhook_received</option>
          </select>
          <button class="btn" id="traces-refresh">&#8635; Refresh</button>
        </div>
      </div>

      <div class="brow mb" id="trace-chips"></div>

      <div class="g2" style="align-items:start">
        <div class="card">
          <div class="card-hd"><div class="card-title"><span class="card-icon">TL</span>Event Timeline</div></div>
          <div class="card-body"><div id="traces-timeline" class="tl"><div class="empty">No trace events yet.</div></div></div>
        </div>
        <div class="card">
          <div class="card-hd"><div class="card-title"><span class="card-icon">LG</span>Event Log</div></div>
          <div class="card-body" style="padding-top:8px">
            <div class="tbl-wrap">
              <table>
                <thead><tr><th>Event</th><th>Prospect</th><th>Trace ID</th><th>Provider</th><th>Time (UTC)</th></tr></thead>
                <tbody id="traces-tbody"><tr><td colspan="5"><div class="empty">No events yet.</div></td></tr></tbody>
              </table>
            </div>
            <div id="langfuse-link-row" style="margin-top:9px;display:none">
              <a class="btn btn-sm" id="langfuse-link" href="#">Open Langfuse Trace &#8599;</a>
            </div>
          </div>
        </div>
      </div>
      <div class="card mt">
        <div class="card-hd"><div class="card-title"><span class="card-icon">W11</span>Week 10 vs Week 11 Comparison Reviews</div></div>
        <div class="card-body"><div id="comparison-review-list"><div class="empty">No comparison reviews yet.</div></div></div>
      </div>
    </section><!-- /traces -->


    <!-- ████████████  SETTINGS PAGE  ████████████ -->
    <section class="page" id="page-settings" hidden>
      <div class="topbar">
        <div class="page-title"><h1>Settings</h1><p>Provider configuration, guardrails, kill switch, and environment status.</p></div>
      </div>

      <div class="g3 mb">
        <div class="card card-pad">
          <div class="card-title" style="margin-bottom:9px"><span class="card-icon">MD</span>Outbound Mode</div>
          <div class="kv">
            <div class="kvr"><span class="kk">Current Mode</span><span class="kv-val" id="settings-mode">Preview</span></div>
            <div class="kvr"><span class="kk">Kill Switch</span><span class="badge s-ok">Active</span></div>
            <div class="kvr"><span class="kk">Draft by default</span><span class="badge s-ok">Yes</span></div>
          </div>
        </div>
        <div class="card card-pad">
          <div class="card-title" style="margin-bottom:9px"><span class="card-icon">BN</span>&#964;&#178;-Bench</div>
          <div class="kv">
            <div class="kvr"><span class="kk">Status</span><span class="kv-val" id="settings-bench">—</span></div>
            <div class="kvr"><span class="kk">Mode</span><span class="kv-val">Evaluation</span></div>
          </div>
        </div>
        <div class="card card-pad">
          <div class="card-title" style="margin-bottom:9px"><span class="card-icon">HE</span>Environment</div>
          <div class="kv">
            <div class="kvr"><span class="kk">API Health</span><span class="kv-val" id="settings-health">—</span></div>
            <div class="kvr"><span class="kk">Seed Materials</span><span class="badge s-ok">Loaded</span></div>
          </div>
        </div>
      </div>

      <div class="card card-pad mb">
        <div class="card-title" style="margin-bottom:9px"><span class="card-icon">W11</span>Week 11 Judge Runtime</div>
        <div class="kv" id="settings-judge-runtime">
          <div class="kvr"><span class="kk">Runtime Mode</span><span class="kv-val">Loading…</span></div>
        </div>
      </div>

      <div class="sec-hd"><div><h2>Provider Configuration</h2><p>Tool readiness and integration status.</p></div></div>
      <div class="cfg-grid mb" id="settings-providers"><div class="empty" style="grid-column:span 2">Loading…</div></div>

      <div class="sec-hd"><div><h2>Active Guardrails</h2><p>Policy rules enforced at outreach time.</p></div></div>
      <div class="card card-pad">
        <div class="cklist">
          <div class="ck-row"><span class="badge s-info">&#10003;</span>Do not promise staffing capacity without bench confirmation.</div>
          <div class="ck-row"><span class="badge s-info">&#10003;</span>Do not frame outreach around a leadership transition that was not observed in-window.</div>
          <div class="ck-row"><span class="badge s-info">&#10003;</span>Do not overclaim weak signals — qualify confidence before use.</div>
          <div class="ck-row"><span class="badge s-info">&#10003;</span>Keep outbound content draft unless live sending is explicitly enabled.</div>
          <div class="ck-row"><span class="badge s-info">&#10003;</span>Respect quiet hours and outreach rate limits.</div>
        </div>
      </div>
    </section><!-- /settings -->


    <!-- ████████████  SIMULATOR PAGE  ████████████ -->
    <section class="page" id="page-simulator" hidden>
      <div class="topbar">
        <div class="page-title">
          <h1>Conversation Simulator</h1>
          <p>Simulate prospect conversations and test all reply scenarios.</p>
        </div>
        <div class="actions">
          <button class="btn" id="sim-reset-btn">&#8635; Reset</button>
        </div>
      </div>

      <div class="g2 mb">

        <!-- LEFT: Prospect Panel -->
        <div>
          <div class="card mb">
            <div class="card-hd">
              <div class="card-title"><span class="card-icon">PR</span>1. Select Prospect</div>
              <span class="badge s-nil" id="sim-prospect-badge">Not created</span>
            </div>
            <div class="card-body">
              <p style="font-size:11.5px;color:var(--muted);margin-bottom:10px">Pick a real company from the snapshot database or enter custom details below.</p>
              <div class="sim-co-header">
                <span class="sim-co-count" id="sim-co-count">0 companies</span>
                <input class="sim-co-search" id="sim-co-search" type="search" placeholder="Search company name…" oninput="simFilterCompanies(this.value)" />
              </div>
              <div class="sim-companies" id="sim-co-grid">
                <div class="empty" style="padding:10px">Loading companies…</div>
              </div>

              <form id="sim-form" style="display:grid;gap:7px">
                <div class="g2" style="gap:7px">
                  <div class="form-field"><label class="form-label">Company Name</label><input id="sim-company" name="company_name" required placeholder="ClearMint" /></div>
                  <div class="form-field"><label class="form-label">Domain</label><input id="sim-domain" name="company_domain" placeholder="clearmint.io" /></div>
                </div>
                <div class="g2" style="gap:7px">
                  <div class="form-field"><label class="form-label">Contact Name</label><input id="sim-contact" name="contact_name" placeholder="Amara Cole" /></div>
                  <div class="form-field"><label class="form-label">Email (replies go here)</label><input id="sim-email" name="contact_email" type="email" placeholder="nurye.nigus.me@gmail.com" /></div>
                </div>
                <div class="form-field"><label class="form-label">Phone (for SMS)</label><input id="sim-phone" name="contact_phone" placeholder="+251929404324" /></div>
                <button class="btn btn-primary" id="sim-run-btn" type="submit" style="width:100%;justify-content:center">&#9654; Create Prospect &amp; Send Initial Email</button>
                <div class="sim-status" id="sim-run-status"></div>
              </form>
            </div>
          </div>

          <!-- Prospect summary (shown after creation) -->
          <div class="card" id="sim-prospect-card" hidden>
            <div class="card-hd"><div class="card-title"><span class="card-icon">&#10003;</span>Prospect Created</div></div>
            <div class="card-body">
              <div class="kv" id="sim-prospect-kv"></div>
            </div>
          </div>
        </div>

        <!-- RIGHT: Sales Conversation Panel -->
        <div>
          <div class="card mb">
            <div class="card-hd">
              <div class="card-title"><span class="card-icon">CH</span>2. Sales Conversation</div>
              <span class="badge s-nil" id="sim-channel-badge">Waiting for prospect</span>
            </div>
            <div class="card-body">
              <!-- Message composer — visible once prospect is created -->
              <div id="sim-composer" style="display:none">
                <div style="font-size:10.5px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.05em;margin-bottom:5px">
                  Prospect message
                </div>
                <textarea id="sim-body-input"
                  rows="3"
                  style="width:100%;padding:9px 11px;border:1.5px solid var(--blue);border-radius:7px;font:13px/1.5 inherit;color:var(--ink);resize:vertical;outline:none"
                  placeholder="Type your prospect message — real agent reply + Week 11 judge review will be shown…"></textarea>
                <div style="display:flex;gap:8px;margin-top:8px;align-items:center">
                  <button class="btn btn-primary" id="sim-send-btn" onclick="simSend()" style="flex-shrink:0" disabled>&#9654; Send Reply</button>
                  <span class="sim-status" id="sim-reply-status" style="margin-top:0"></span>
                </div>
              </div>
            </div>
          </div>

          <!-- Conversation thread -->
          <div class="card">
            <div class="card-hd"><div class="card-title"><span class="card-icon">TH</span>Conversation Thread</div></div>
            <div class="card-body" style="padding:0">
              <div class="sim-thread" id="sim-thread">
                <div class="sim-empty">Create a prospect to start the conversation.</div>
              </div>
            </div>
          </div>
        </div>

      </div>
    </section><!-- /simulator -->

  </main>
</div><!-- /shell -->

<script>
// ── DATA STORE ──────────────────────────────────────
let _state = null, _snap = null, _allTraces = [], _allProspects = [], _comparisonReviews = [];

// ── UTILITIES ───────────────────────────────────────
const esc = v => String(v ?? "").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");

function trunc(v, n = 80, fallback = "Not available") {
  const s = String(v || fallback).trim();
  return s.length > n ? s.slice(0, n - 1) + "…" : s;
}

function fmt(v) {
  if (!v) return "—";
  const d = new Date(v);
  return isNaN(d) ? String(v) : d.toISOString().replace("T", " ").slice(0, 16) + " UTC";
}

const pct = v => v != null ? Math.round(Number(v) * 100) + "%" : "—";

function titl(v) {
  return String(v || "").replace(/_/g, " ").replace(/\\b\\w/g, c => c.toUpperCase()) || "—";
}

function tone(s) {
  const v = String(s || "").toLowerCase();
  if (["executed","configured","confirmed","healthy","logged","ready","booked","ok","live","success"].some(w => v.includes(w))) return "s-ok";
  if (["previewed","preview","pending","mock","draft","unknown","not_started"].some(w => v.includes(w))) return "s-warn";
  if (["error","failed","unavailable"].some(w => v.includes(w))) return "s-err";
  if (["skipped","not configured","missing"].some(w => v.includes(w))) return "s-nil";
  return "s-info";
}

const bdg = (label, t) => `<span class="badge ${t || tone(label)}">${esc(label)}</span>`;
const emp = msg => `<div class="empty">${esc(msg || "Not available")}</div>`;

// KV row helper
const kvr = (k, v) => `<div class="kvr"><span class="kk">${esc(k)}</span><span class="kv-val">${v}</span></div>`;

// ── ROUTING ─────────────────────────────────────────
let _simCompaniesLoaded = false;
function showPage(hash) {
  const id = hash || "overview";
  document.querySelectorAll(".page").forEach(p => p.hidden = true);
  const pg = document.getElementById("page-" + id);
  if (pg) pg.hidden = false;
  document.querySelectorAll(".nav a").forEach(a => a.classList.toggle("active", a.dataset.page === id));
  if (_state) populatePage(id);
  if (id === "simulator" && !_simCompaniesLoaded) { _simCompaniesLoaded = true; loadSimCompanies(); }
}

window.addEventListener("hashchange", () => showPage(location.hash.slice(1)));

document.querySelectorAll("[data-page]").forEach(el => {
  el.addEventListener("click", () => { if (el.dataset.page) location.hash = "#" + el.dataset.page; });
});

// ── TOOLS LIST ──────────────────────────────────────
const TOOLS = [
  ["crunchbase","Crunchbase"],["job_posts","Job Posts"],["layoffs_fyi","layoffs.fyi"],
  ["leadership","Leadership"],["email","Email"],["sms","SMS"],
  ["calcom","Cal.com"],["hubspot","HubSpot"],["langfuse","Langfuse"],["tau2_bench","τ²-Bench"],
];

function buildToolRows(statuses, snap) {
  const results = snap?.toolchain_report?.results || [];
  return TOOLS.map(([name, label]) => {
    const r = results.find(x => x.name === name);
    const s = (statuses || []).find(x => x.name === name);
    if (r) return { name, label, status: r.status, mode: r.mode, details: r.message };
    if (s) return { name, label: s.label || label, status: s.configured ? "Not run" : "Not configured", mode: s.mode, details: s.details };
    return { name, label, status: "Not configured", mode: "unavailable", details: "" };
  });
}

function getArtifact(name) { return (_state?.latest_artifacts || []).find(a => a.name === name); }

// ── SIGNALS HELPERS ─────────────────────────────────
function normSignals(snap) {
  const sigs = snap?.hiring_signal_brief?.signals || [];
  return [
    ["funding_event", ["funding","crunchbase","raised"]],
    ["job_post_velocity", ["job","hiring","velocity","opening"]],
    ["layoff_signal", ["layoff","workforce","reduction"]],
    ["leadership_change", ["leadership","cto","vp","transition"]],
  ].map(([name, pats]) => {
    const sig = sigs.find(s => pats.some(p => `${s.name||""} ${s.summary||""}`.toLowerCase().includes(p))) || {};
    return { name, label: titl(name), summary: sig.summary || "No matching public signal found.", confidence: Number(sig.confidence ?? 0) };
  });
}

function confLabel(c) { return c >= .72 ? "High" : c >= .45 ? "Medium" : c > 0 ? "Low" : "No signal"; }
function confTone(c)  { return c >= .72 ? "s-ok" : c >= .45 ? "s-warn" : "s-nil"; }

function extractSubject(snap) {
  const d = snap?.initial_decision?.reply_draft || "";
  const line = d.split("\\n").find(l => l.toLowerCase().startsWith("subject:"));
  return line ? line.replace(/^subject:\\s*/i, "").trim() : `${snap?.prospect?.company_name || "Prospect"}: Engineering team velocity?`;
}

function extractBody(snap) {
  return (snap?.initial_decision?.reply_draft || "").replace(/^subject:.*\\n?/i, "").trim() || "No outreach draft available.";
}

// ── OVERVIEW RENDERS ─────────────────────────────────
function renderKpis() {
  document.getElementById("kpi-prospects").textContent = _state?.total_prospects ?? "—";
  document.getElementById("kpi-traces").textContent    = _state?.total_traces ?? "—";
}

function renderToolStatuses() {
  const rows = buildToolRows(_state?.tool_statuses || [], _snap);
  document.getElementById("tool-statuses").innerHTML = rows.map(t =>
    `<div class="tool-row">${esc(t.label)}${bdg(titl(t.status), tone(t.status))}</div>`
  ).join("");
  const email = rows.find(t => t.name === "email");
  const live = email?.mode === "configured" && email?.status === "executed";
  document.getElementById("kpi-mode").textContent = live ? "Live" : "Safe Preview";
  const tau = rows.find(t => t.name === "tau2_bench");
  document.getElementById("kpi-bench").textContent = (tau?.status === "executed" || tau?.mode === "configured") ? "τ²-Bench Ready" : "Not configured";
}

function renderLatestFlow(flow) {
  const bodyEl = document.getElementById("latest-flow-body");
  const badgeEl = document.getElementById("latest-event-badge");
  if (!flow) {
    bodyEl.innerHTML = `<div class="card-body">${emp("No interaction flow recorded yet.")}</div>`;
    badgeEl.textContent = "No recent event"; badgeEl.className = "badge s-nil";
    return;
  }
  const co = flow.company_name || _snap?.prospect?.company_name || "Unknown";
  const summary = _snap?.hiring_signal_brief?.summary || "Latest prospect flow.";
  const booking = flow.booking_status || "pending";
  const crm = flow.crm_logged ? "CRM logged" : "CRM pending";
  const voice = flow.voice_handoff_ready ? "Voice ready" : "Voice pending";
  const traceId = _snap?.trace_id || flow?.trace_id || "Pending";
  const mode = document.getElementById("kpi-mode")?.textContent || "Preview";

  badgeEl.textContent = flow.latest_event || "No recent event";
  badgeEl.className = `badge ${tone(flow.latest_event || "")}`;

  bodyEl.innerHTML = `
    <div class="flow-layout">
      <div class="flow-left">
        <div class="brow">
          ${bdg("Source-backed brief ready","s-ok")}
          ${bdg("Booking " + booking, tone(booking))}
          ${bdg(flow.voice_handoff_ready ? "SMS handoff active" : "Voice pending", flow.voice_handoff_ready ? "s-info" : "s-warn")}
          ${bdg(crm, tone(crm))}
        </div>
        <div class="fact-grid">
          <div class="fact"><div class="fact-lbl">State</div><div class="fact-val">${esc(titl(flow.current_state || flow.status || "unknown"))}</div></div>
          <div class="fact"><div class="fact-lbl">Booking</div><div class="fact-val">${esc(titl(booking))}</div></div>
          <div class="fact"><div class="fact-lbl">CRM</div><div class="fact-val">${esc(crm)}</div></div>
          <div class="fact"><div class="fact-lbl">Voice</div><div class="fact-val">${esc(voice)}</div></div>
          <div class="fact"><div class="fact-lbl">Prospect ID</div><div class="fact-val">${esc(trunc(flow.prospect_id || "—", 20))}</div></div>
          <div class="fact"><div class="fact-lbl">Trace ID</div><div class="fact-val">${esc(trunc(traceId, 20))}</div></div>
          <div class="fact"><div class="fact-lbl">Latest Event</div><div class="fact-val">${esc(flow.latest_event || "—")}</div></div>
          <div class="fact"><div class="fact-lbl">Mode</div><div class="fact-val">${esc(mode)}</div></div>
        </div>
      </div>
      <div class="co-tile">
        <div class="logo-tile">${esc(co.slice(0, 2).toUpperCase())}</div>
        <div>
          <div class="co-name">${esc(co)}</div>
          <div class="co-desc">${esc(trunc(summary, 160, "Latest prospect flow across research, outreach, scheduling, and CRM."))}</div>
        </div>
      </div>
    </div>`;
}

function renderIntelligence(snap) {
  const el = document.getElementById("intelligence-grid");
  const trEl = document.getElementById("selected-trace");
  if (!snap) {
    trEl.textContent = "Trace pending"; trEl.className = "badge s-info";
    el.innerHTML = ["Prospect Snapshot","Hiring Signals","Bench Match","Competitor Gap","Outreach Draft"]
      .map((t, i) => `<div class="card card-pad"><div class="card-title" style="margin-bottom:9px"><span class="card-icon">${"ABCDE"[i]}</span>${t}</div>${emp("Run the toolchain.")}</div>`).join("");
    return;
  }

  const p = snap.prospect || {};
  const brief = snap.hiring_signal_brief || {};
  const gap = snap.competitor_gap_brief || {};
  const bench = brief.bench_match || {};
  const emailArt = getArtifact("email");
  const emailTool = (_state?.tool_statuses || []).find(t => t.name === "email");
  const draftMode = emailTool?.mode === "configured" ? "Live mode" : "Draft mode";
  const practices = (gap.gap_practices || []).map(x => x.description || x.practice_name).filter(Boolean).slice(0, 3);
  if (!practices.length && gap.top_quartile_practices) practices.push(...(gap.top_quartile_practices || []).slice(0, 3));
  const stacks = bench.required_stacks || [];
  const capRows = stacks.length ? stacks : Object.keys(bench.available_capacity || {});

  trEl.textContent = snap.trace_id ? `Trace ${trunc(snap.trace_id, 22)}` : "Trace pending";
  trEl.className = "badge s-info";

  el.innerHTML = `
    <div class="card card-pad">
      <div class="card-title" style="margin-bottom:9px"><span class="card-icon">A</span>Prospect Snapshot</div>
      <div class="kv">
        ${kvr("Company", esc(p.company_name || "Not available"))}
        ${kvr("Domain", esc(p.company_domain || "—"))}
        ${kvr("Segment", esc(p.primary_segment_label || titl(p.primary_segment) || "—"))}
        ${kvr("Confidence", pct(p.segment_confidence ?? brief.segment_confidence))}
        ${kvr("AI Maturity", esc(String(p.ai_maturity_score ?? brief.ai_maturity_score ?? "—")))}
        ${kvr("Employees", esc(String(snap.employee_count || "—")))}
      </div>
      <div style="margin-top:7px;font-size:11px;color:var(--muted)">ID: ${esc(trunc(p.prospect_id || "—", 30))}</div>
    </div>

    <div class="card card-pad">
      <div class="card-title" style="margin-bottom:9px"><span class="card-icon">B</span>Hiring Signals</div>
      <div class="sig-list">
        ${normSignals(snap).map(sig => `
          <div class="sig-row">
            <div class="sig-dot">${esc(sig.label[0])}</div>
            <div>
              <div class="sig-name">${esc(sig.label)}</div>
              <div class="sig-txt">${esc(sig.summary)}</div>
            </div>
            ${bdg(confLabel(sig.confidence), confTone(sig.confidence))}
          </div>`).join("")}
      </div>
    </div>

    <div class="card card-pad">
      <div class="card-title" style="margin-bottom:9px"><span class="card-icon">C</span>Bench Match</div>
      <div class="brow" style="margin-bottom:9px">
        ${bdg(bench.sufficient ? "Match sufficient" : "Gap — review needed", bench.sufficient ? "s-ok" : "s-warn")}
        ${(stacks || []).map(s => bdg(s, "s-info")).join("")}
      </div>
      <div class="cap-list">
        ${capRows.length ? capRows.map(stack => {
          const cap = Number(bench.available_capacity?.[stack] || 0);
          const w = Math.max(8, Math.min(100, cap * 20));
          return `<div>
            <div class="cap-hd"><span>${esc(titl(stack))}</span><span>${cap} avail.</span></div>
            <div class="cap-bar"><span style="width:${w}%"></span></div>
          </div>`;
        }).join("") : emp("Capacity not reported.")}
      </div>
      <div class="hint">${esc(trunc(bench.recommendation || "Quote capacity as available, not committed.", 110))}</div>
    </div>

    <div class="card card-pad">
      <div class="card-title" style="margin-bottom:9px"><span class="card-icon">D</span>Competitor Gap</div>
      <div class="crow" style="margin-bottom:8px">
        ${(gap.top_quartile_companies || []).slice(0, 3).map(c => `<span class="chip s-info">${esc(c)}</span>`).join("") || bdg("Comparison limited","s-nil")}
      </div>
      <ul style="margin:0 0 8px 15px;font-size:12px;color:var(--ink-mid);line-height:1.55">
        ${practices.length ? practices.map(p => `<li>${esc(trunc(p, 70))}</li>`).join("") : "<li>No public competitor data available.</li>"}
      </ul>
      <div class="hint">${esc(trunc(gap.safe_gap_framing || "Frame as research finding, not judgment.", 110))}</div>
    </div>

    <div class="card card-pad">
      <div class="card-title" style="margin-bottom:9px"><span class="card-icon">E</span>Outreach Draft</div>
      <div class="email-wrap">
        <div class="email-meta">
          <div><strong>To:</strong> <span>${esc(p.contact_email || "Not available")}</span></div>
          <div><strong>Subject:</strong> <span>${esc(trunc(extractSubject(snap), 65))}</span></div>
          <div class="brow" style="margin-top:4px">${bdg(draftMode, tone(draftMode))}</div>
        </div>
        <div class="email-body">${esc(extractBody(snap))}</div>
        <div class="email-foot">
          ${emailArt?.route ? `<a class="btn btn-sm" href="${esc(emailArt.route)}">Open Draft &#8599;</a>` : bdg("No artifact link","s-nil")}
        </div>
      </div>
    </div>`;
}

function renderRecentProspects(snaps) {
  const seen = new Set();
  const rows = (snaps || []).filter(s => {
    const k = s.prospect?.prospect_id || s.prospect?.company_name;
    if (seen.has(k)) return false; seen.add(k); return true;
  }).slice(0, 5);
  const el = document.getElementById("recent-prospects");
  if (!rows.length) { el.innerHTML = emp("No saved prospects yet."); return; }
  el.innerHTML = `<table>
    <thead><tr><th>Company</th><th>Segment</th><th>Conf.</th><th>AI</th></tr></thead>
    <tbody>${rows.map(s => {
      const p = s.prospect || {};
      return `<tr>
        <td><strong>${esc(p.company_name || "—")}</strong></td>
        <td>${esc(trunc(p.primary_segment_label || titl(p.primary_segment), 22))}</td>
        <td>${pct(p.segment_confidence)}</td>
        <td>${esc(String(p.ai_maturity_score ?? "—"))}</td>
      </tr>`;
    }).join("")}</tbody></table>`;
}

function renderRecentTraces(traces) {
  const el = document.getElementById("recent-traces");
  if (!traces?.length) { el.innerHTML = emp("No trace events yet."); return; }
  el.innerHTML = `<table>
    <thead><tr><th>Event</th><th>Prospect</th><th>Time</th></tr></thead>
    <tbody>${traces.slice(0, 5).map(t => `<tr>
      <td><strong>${esc(t.event_type || "—")}</strong></td>
      <td>${esc(t.company_name || t.prospect_id || "—")}</td>
      <td style="white-space:nowrap;font-size:11px">${esc(fmt(t.timestamp))}</td>
    </tr>`).join("")}</tbody></table>`;
}

const ART_LABELS = { context_brief:"Context Brief", calcom:"Cal.com Link", email:"Email Draft", sms:"SMS Draft", hubspot:"HubSpot Note", langfuse:"Langfuse Trace" };
const artLabel = n => ART_LABELS[n] || titl(n);

function renderArtifacts(arts) {
  const el = document.getElementById("latest-artifacts");
  if (!arts?.length) { el.innerHTML = emp("No artifacts yet."); return; }
  const cb = arts.find(a => a.name === "context_brief") || arts[0];
  document.getElementById("export-brief").href = cb?.route || "/dashboard/state";
  const hs = arts.find(a => a.name === "hubspot");
  if (hs?.route) {
    document.getElementById("hubspot-link").href = hs.route;
    document.getElementById("crm-hubspot-link").href = hs.route;
  }
  el.innerHTML = arts.slice(0, 6).map(a => `
    <div class="art-card">
      <div style="display:flex;justify-content:space-between;align-items:center;gap:7px">
        <div class="art-title"><span class="card-icon">${esc(artLabel(a.name).slice(0,2).toUpperCase())}</span>${esc(artLabel(a.name))}</div>
        ${bdg(a.exists ? "Preview" : "Pending", a.exists ? "s-warn" : "s-nil")}
      </div>
      <div class="brow">${bdg(a.name, "s-nil")}</div>
      <div class="art-preview">${esc(trunc(a.preview || a.path || "No preview available.", 90))}</div>
      ${a.route ? `<a class="btn btn-sm" href="${esc(a.route)}" style="justify-self:start">Open &#8599;</a>` : ""}
    </div>`).join("");
}

// ── PAGE-SPECIFIC POPULATES ──────────────────────────
function populatePage(id) {
  if (!_state) return;
  if (id === "prospects") renderProspectsPage();
  if (id === "outreach")  renderOutreachPage();
  if (id === "signals")   renderSignalsPage();
  if (id === "meetings")  renderMeetingsPage();
  if (id === "crm")       renderCrmPage();
  if (id === "traces")    renderTracesPage();
  if (id === "settings")  renderSettingsPage();
}

// Prospects page
function renderProspectsPage() {
  const seen = new Set();
  _allProspects = (_state?.recent_snapshots || []).filter(s => {
    const k = s.prospect?.prospect_id || s.prospect?.company_name;
    if (seen.has(k)) return false; seen.add(k); return true;
  });
  const segs = {};
  _allProspects.forEach(s => {
    const seg = s.prospect?.primary_segment_label || titl(s.prospect?.primary_segment) || "Unknown";
    segs[seg] = (segs[seg] || 0) + 1;
  });
  document.getElementById("segment-chips").innerHTML = Object.entries(segs)
    .map(([s, n]) => `<span class="badge s-info">${esc(s)} <strong>${n}</strong></span>`).join("");
  renderProspectsTable(_allProspects);
}

function renderProspectsTable(rows) {
  const tbody = document.getElementById("prospects-tbody");
  if (!rows.length) { tbody.innerHTML = `<tr><td colspan="8">${emp("No prospects yet.")}</td></tr>`; return; }
  tbody.innerHTML = rows.map(s => {
    const p = s.prospect || {};
    const dataAttr = `data-company="${esc(p.company_name || "")}" data-domain="${esc(p.company_domain || "")}" data-contact="${esc(p.contact_name || "")}" data-email="${esc(p.contact_email || "")}" data-phone="${esc(p.contact_phone || "")}"`;
    return `<tr>
      <td><strong>${esc(p.company_name || "—")}</strong><br><span style="font-size:11px;color:var(--muted)">${esc(p.company_domain || "")}</span></td>
      <td>${esc(p.primary_segment_label || titl(p.primary_segment) || "—")}</td>
      <td>${pct(p.segment_confidence)}</td>
      <td>${esc(String(p.ai_maturity_score ?? "—"))}</td>
      <td>${bdg(p.status || "Active", tone(p.status || ""))}</td>
      <td style="font-size:11px;white-space:nowrap">${esc(fmt(p.updated_at))}</td>
      <td>${p.prospect_id ? `<a class="btn btn-sm" href="/prospects/${esc(p.prospect_id)}">Brief &#8599;</a>` : "—"}</td>
      <td><button class="btn btn-sm rerun-btn" ${dataAttr}>&#9654; Re-run</button></td>
    </tr>`;
  }).join("");

  // Attach re-run handlers
  document.querySelectorAll(".rerun-btn").forEach(btn => {
    btn.addEventListener("click", async () => {
      const statusEl = document.getElementById("rerun-status");
      const payload = {
        company_name:   btn.dataset.company,
        company_domain: btn.dataset.domain  || undefined,
        contact_name:   btn.dataset.contact || undefined,
        contact_email:  btn.dataset.email   || undefined,
        contact_phone:  btn.dataset.phone   || undefined,
      };
      btn.disabled = true;
      statusEl.textContent = `Re-running toolchain for ${payload.company_name}…`;
      try {
        const r = await fetch("/pipeline/run", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
        if (!r.ok) throw new Error("Re-run failed.");
        _snap = await r.json();
        renderIntelligence(_snap);
        await loadState();
        statusEl.textContent = `Re-run complete for ${payload.company_name}.`;
      } catch (e) {
        statusEl.textContent = e.message;
      } finally {
        btn.disabled = false;
      }
    });
  });
}

document.getElementById("prospects-search").addEventListener("input", e => {
  const q = e.target.value.toLowerCase();
  renderProspectsTable(_allProspects.filter(s => {
    const p = s.prospect || {};
    return (p.company_name || "").toLowerCase().includes(q) || (p.primary_segment_label || "").toLowerCase().includes(q);
  }));
});

document.getElementById("prospects-refresh").addEventListener("click", () => { loadState(); });

// Outreach page
function renderOutreachPage() {
  const tools = _state?.tool_statuses || [];
  const flow = _state?.latest_flow;
  const emailTool = tools.find(t => t.name === "email") || {};
  const smsTool   = tools.find(t => t.name === "sms")   || {};
  const calTool   = tools.find(t => t.name === "calcom") || {};
  const emailMode = emailTool.mode === "configured" ? "Live" : "Draft / Preview";

  document.getElementById("out-email-kv").innerHTML = `
    ${kvr("Provider", esc(emailTool.label || "Resend"))}
    ${kvr("Status", bdg(titl(emailTool.status || "Not configured"), tone(emailTool.status)))}
    ${kvr("Mode", bdg(emailMode, emailMode === "Live" ? "s-live" : "s-draft"))}`;

  document.getElementById("out-sms-kv").innerHTML = `
    ${kvr("Provider", "Africa's Talking")}
    ${kvr("Status", bdg(titl(smsTool.status || "Not configured"), tone(smsTool.status)))}
    ${kvr("Warm Handoff", bdg(flow?.voice_handoff_ready ? "Ready" : "Pending", flow?.voice_handoff_ready ? "s-ok" : "s-warn"))}`;

  document.getElementById("out-cal-kv").innerHTML = `
    ${kvr("Provider", "Cal.com")}
    ${kvr("Booking", bdg(titl(flow?.booking_status || "Pending"), tone(flow?.booking_status)))}
    ${kvr("Status", bdg(titl(calTool.status || "Not configured"), tone(calTool.status)))}`;

  const draftEl = document.getElementById("out-draft-card");
  if (_snap) {
    const p = _snap.prospect || {};
    const ea = getArtifact("email");
    const dm = emailTool.mode === "configured" ? "Live mode" : "Draft mode";
    draftEl.innerHTML = `<div class="card-body">
      <div class="email-wrap">
        <div class="email-meta">
          <div><strong>To:</strong> <span>${esc(p.contact_email || "Not available")}</span></div>
          <div><strong>Subject:</strong> <span>${esc(extractSubject(_snap))}</span></div>
          <div><strong>Company:</strong> <span>${esc(p.company_name || "—")}</span></div>
          <div class="brow" style="margin-top:4px">${bdg(dm, tone(dm))}${bdg(emailTool.label || "preview", "s-nil")}</div>
        </div>
        <div class="email-body" style="-webkit-line-clamp:6">${esc(extractBody(_snap))}</div>
        <div class="email-foot">${ea?.route ? `<a class="btn btn-sm" href="${esc(ea.route)}">Open Full Draft &#8599;</a>` : ""}</div>
      </div></div>`;
  } else {
    draftEl.innerHTML = `<div class="card-body">${emp("No outreach draft available yet.")}</div>`;
  }

  const replyEvts = (_state?.latest_interaction_events || []).filter(e => e.event_type?.includes("reply"));
  const tb = document.getElementById("out-replies-tbody");
  tb.innerHTML = replyEvts.length ? replyEvts.slice(0, 10).map(e => `<tr>
    <td><strong>${esc(e.event_type || "—")}</strong></td>
    <td>${esc(e.company_name || e.prospect_id || "—")}</td>
    <td>${bdg(e.reply_type || "Normal", "s-info")}</td>
    <td>${esc(e.provider || "—")}</td>
    <td style="font-size:11px;white-space:nowrap">${esc(fmt(e.created_at))}</td>
    <td style="font-size:11px">${esc(trunc(e.trace_id || "—", 18))}</td>
  </tr>`).join("") : `<tr><td colspan="6">${emp("No reply events recorded.")}</td></tr>`;
}

// ── REPLY SIMULATOR ─────────────────────────────────
const QUICK_FILLS = {
  "qf-meeting": "Hi, thanks for reaching out — I'd like to schedule a discovery call. What times work next week?",
  "qf-pricing": "Interesting approach. Can you share pricing details and how you bill for the engineering capacity?",
  "qf-normal":  "Thanks for the email. I've forwarded it to our engineering lead. We'll circle back shortly.",
  "qf-opt-out": "Thanks but we're not looking at external vendors right now. Please remove me from your list.",
};

Object.entries(QUICK_FILLS).forEach(([id, text]) => {
  document.getElementById(id)?.addEventListener("click", () => {
    document.getElementById("reply-body").value = text;
  });
});

document.getElementById("reply-sim-form").addEventListener("submit", async e => {
  e.preventDefault();
  const statusEl = document.getElementById("reply-sim-status");
  const btn = document.getElementById("reply-sim-btn");
  const body = document.getElementById("reply-body").value.trim();
  if (!body) { statusEl.textContent = "Message body is required."; return; }

  const payload = {
    body,
    channel: document.getElementById("reply-channel").value,
    prospect_id:   document.getElementById("reply-prospect-id").value.trim()   || _snap?.prospect?.prospect_id || undefined,
    contact_email: document.getElementById("reply-contact-email").value.trim() || _snap?.prospect?.contact_email || undefined,
  };
  // Strip undefined keys
  Object.keys(payload).forEach(k => payload[k] === undefined && delete payload[k]);

  btn.disabled = true;
  statusEl.textContent = "Sending simulated reply…";
  try {
    const r = await fetch("/conversations/reply", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    if (!r.ok) throw new Error(`Reply failed (${r.status}).`);
    const decision = await r.json();
    statusEl.textContent = "Reply handled — decision below.";
    // Show decision
    const outEl = document.getElementById("reply-decision-out");
    const kvEl  = document.getElementById("reply-decision-kv");
    const draftEl = document.getElementById("reply-draft-preview");
    outEl.style.display = "block";
    kvEl.innerHTML = `
      ${kvr("Next Action", bdg(decision.next_action || "—", tone(decision.next_action)))}
      ${kvr("Channel", esc(decision.channel || "—"))}
      ${kvr("Needs Human", decision.needs_human ? bdg("Yes","s-warn") : bdg("No","s-ok"))}
      ${decision.risk_flags?.length ? kvr("Risk Flags", esc(decision.risk_flags.join(", "))) : ""}`;
    draftEl.innerHTML = decision.reply_draft ? `
      <div class="card-title" style="margin:10px 0 7px"><span class="card-icon">DR</span>Generated Reply Draft</div>
      <div class="email-wrap">
        <div class="email-body" style="-webkit-line-clamp:8;white-space:pre-wrap">${esc(decision.reply_draft)}</div>
      </div>` : "";
    await loadState();
  } catch (err) {
    statusEl.textContent = err.message;
  } finally {
    btn.disabled = false;
  }
});

// Signals page
function renderSignalsPage() {
  const snap = _snap;
  const co = snap?.prospect?.company_name || "—";
  document.getElementById("sig-company-badge").textContent = co === "—" ? "No prospect" : co;
  if (!snap) {
    document.getElementById("sig-list").innerHTML = emp("Run the toolchain to generate signal data.");
    document.getElementById("sig-meta-kv").innerHTML = `${kvr("Prospect","—")}${kvr("AI Maturity","—")}${kvr("Segment","—")}${kvr("Confidence","—")}`;
    return;
  }
  const brief = snap.hiring_signal_brief || {};
  const p = snap.prospect || {};
  document.getElementById("sig-list").innerHTML = normSignals(snap).map(sig => `
    <div class="sig-row">
      <div class="sig-dot">${esc(sig.label[0])}</div>
      <div><div class="sig-name">${esc(sig.label)}</div><div class="sig-txt">${esc(sig.summary)}</div></div>
      ${bdg(confLabel(sig.confidence), confTone(sig.confidence))}
    </div>`).join("");
  document.getElementById("sig-meta-kv").innerHTML = `
    ${kvr("Prospect", esc(p.company_name || "—"))}
    ${kvr("AI Maturity Score", esc(String(p.ai_maturity_score ?? brief.ai_maturity_score ?? "—")))}
    ${kvr("Segment", esc(p.primary_segment_label || titl(p.primary_segment) || "—"))}
    ${kvr("Confidence", pct(p.segment_confidence ?? brief.segment_confidence))}`;
  const gaps = brief.evidence_gaps || brief.missing_signals || [];
  document.getElementById("evidence-gaps").innerHTML = gaps.length
    ? `<div class="cklist">${gaps.slice(0, 5).map(g => `<div class="ck-row">${bdg("!", "s-warn")}${esc(trunc(String(g), 80))}</div>`).join("")}</div>`
    : emp("No evidence gaps reported.");
}

// Meetings page
function renderMeetingsPage() {
  const flow = _state?.latest_flow;
  const calTool = (_state?.tool_statuses || []).find(t => t.name === "calcom") || {};
  const calArt = getArtifact("calcom");
  const ctxArt = getArtifact("context_brief");
  document.getElementById("mtg-cal-kv").innerHTML = `
    ${kvr("Provider", "Cal.com")}
    ${kvr("Booking", bdg(titl(flow?.booking_status || "Pending"), tone(flow?.booking_status)))}
    ${kvr("Webhook", bdg(titl(calTool.status || "Not configured"), tone(calTool.status)))}
    ${kvr("Prospect", esc(trunc(flow?.company_name || _snap?.prospect?.company_name || "—", 22)))}`;
  document.getElementById("mtg-booking-kv").innerHTML = `
    ${kvr("Status", bdg(titl(flow?.booking_status || "Pending"), tone(flow?.booking_status)))}
    ${kvr("Confirmed", esc(flow?.booking_status === "confirmed" ? "Yes" : "No"))}
    ${calArt?.route ? kvr("Link", `<a class="btn btn-sm" href="${esc(calArt.route)}" style="height:20px;padding:0 7px;font-size:11px">Open &#8599;</a>`) : ""}`;
  const ctxEl = document.getElementById("mtg-ctx-brief");
  if (ctxArt?.route) {
    ctxEl.innerHTML = `
      <div class="kv" style="margin-bottom:9px">
        ${kvr("Type", "Context Brief")}
        ${kvr("Prospect", esc(trunc(_snap?.prospect?.company_name || "—", 22)))}
        ${kvr("Status", bdg(ctxArt.exists ? "Ready" : "Pending", ctxArt.exists ? "s-ok" : "s-warn"))}
      </div>
      <a class="btn btn-sm" href="${esc(ctxArt.route)}">Open Context Brief &#8599;</a>`;
  } else {
    ctxEl.innerHTML = emp("No context brief generated yet.");
  }
}

// CRM page
function renderCrmPage() {
  const hsTool = (_state?.tool_statuses || []).find(t => t.name === "hubspot") || {};
  const synced = hsTool.status === "executed" || hsTool.mode === "configured";
  const syncBadge = document.getElementById("crm-sync-badge");
  syncBadge.textContent = synced ? "Synced" : "Not synced";
  syncBadge.className = `badge ${synced ? "s-ok" : "s-nil"}`;
  const p = _snap?.prospect || {};
  document.getElementById("crm-contact-kv").innerHTML = `
    ${kvr("Company", esc(p.company_name || "—"))}
    ${kvr("Contact", esc(p.contact_name || "—"))}
    ${kvr("Email", esc(p.contact_email || "—"))}
    ${kvr("Phone", esc(p.contact_phone || "—"))}
    ${kvr("Lifecycle Stage", esc(p.lifecycle_stage || "Lead"))}
    ${kvr("Segment", esc(p.primary_segment_label || titl(p.primary_segment) || "—"))}
    ${kvr("Last Activity", esc(fmt(p.updated_at)))}`;
  const fields = [
    ["Company Name", !!p.company_name], ["Contact Email", !!p.contact_email],
    ["Contact Phone", !!p.contact_phone], ["Segment", !!(p.primary_segment_label || p.primary_segment)],
    ["AI Maturity", p.ai_maturity_score != null], ["HubSpot Sync", synced],
  ];
  const filled = fields.filter(f => f[1]).length;
  const scoreBadge = document.getElementById("crm-score-badge");
  scoreBadge.textContent = `${filled}/${fields.length}`;
  scoreBadge.className = `badge ${filled === fields.length ? "s-ok" : filled >= 4 ? "s-warn" : "s-nil"}`;
  document.getElementById("crm-checklist").innerHTML = fields.map(([n, ok]) =>
    `<div class="ck-row">${bdg(ok ? "✓" : "○", ok ? "s-ok" : "s-nil")}${esc(n)}</div>`).join("");
  const evts = (_state?.latest_interaction_events || []).concat(_state?.recent_traces || [])
    .filter(e => e.event_type && (e.event_type.includes("crm") || e.event_type.includes("hubspot")));
  const tb = document.getElementById("crm-activity-tbody");
  tb.innerHTML = evts.length ? evts.slice(0, 8).map(e => `<tr>
    <td><strong>${esc(e.event_type || "—")}</strong></td>
    <td>${esc(e.field || e.channel || "—")}</td>
    <td>${esc(trunc(e.value || e.payload_summary || "—", 40))}</td>
    <td style="white-space:nowrap;font-size:11px">${esc(fmt(e.created_at || e.timestamp))}</td>
    <td>${bdg("Logged", "s-ok")}</td>
  </tr>`).join("") : `<tr><td colspan="5">${emp("No CRM activity logged yet.")}</td></tr>`;
}

// Traces page
function renderTracesPage() {
  const traces = _state?.recent_traces || [];
  const evts = _state?.latest_interaction_events || [];
  _allTraces = [...traces, ...evts].sort((a, b) => new Date(b.timestamp || b.created_at) - new Date(a.timestamp || a.created_at));
  const typeCount = {};
  _allTraces.forEach(t => { const k = t.event_type || "unknown"; typeCount[k] = (typeCount[k] || 0) + 1; });
  document.getElementById("trace-chips").innerHTML = Object.entries(typeCount).slice(0, 6)
    .map(([k, n]) => `<span class="badge s-info">${esc(k)} <strong>${n}</strong></span>`).join("");
  renderTracesTable(_allTraces);
  renderTracesTimeline(_allTraces);
  renderComparisonReviews();
  const lf = getArtifact("langfuse");
  const lfRow = document.getElementById("langfuse-link-row");
  if (lf?.route) { lfRow.style.display = "block"; document.getElementById("langfuse-link").href = lf.route; }
}

function verdictTone(verdict) {
  const v = String(verdict || "").toLowerCase();
  if (v === "pass") return "s-ok judge-pass";
  if (v === "fail") return "s-err judge-fail";
  if (v === "judge_disabled") return "s-nil";
  return "s-warn judge-review";
}

function finalDecisionLabel(v) {
  const d = String(v || "").toLowerCase();
  if (d === "allow") return "ALLOW";
  if (d === "block") return "BLOCK";
  return "ROUTE TO HUMAN";
}

function renderComparisonReviews() {
  const el = document.getElementById("comparison-review-list");
  if (!el) return;
  if (!_comparisonReviews.length) { el.innerHTML = emp("No comparison reviews yet."); return; }
  el.innerHTML = _comparisonReviews.slice(0, 8).map(r => `
    <div class="comparison-panel ${r.final_decision === "block" ? "blocked" : ""}" style="margin-bottom:8px">
      <div style="display:flex;justify-content:space-between;gap:8px;align-items:center">
        <strong>${esc(r.company_name || r.prospect_id || "Comparison review")}</strong>
        ${bdg(String(r.judge_verdict || "needs_human_review").toUpperCase().replace(/_/g, " "), verdictTone(r.judge_verdict))}
      </div>
      <div class="comparison-body" style="margin-top:5px">${esc(trunc(r.baseline_output || "", 180))}</div>
      <div class="comparison-meta">
        ${bdg(finalDecisionLabel(r.final_decision), r.final_decision === "allow" ? "s-ok" : r.final_decision === "block" ? "s-err" : "s-warn")}
        ${bdg(titl(r.action_type), "s-nil")}
        ${bdg(titl(r.channel), "s-nil")}
      </div>
      <div style="font-size:11.5px;color:var(--muted);margin-top:5px">${esc(r.improvement_summary || r.judge_reason || "")}</div>
    </div>
  `).join("");
}

function renderTracesTable(rows) {
  const tb = document.getElementById("traces-tbody");
  if (!rows.length) { tb.innerHTML = `<tr><td colspan="5">${emp("No trace events yet.")}</td></tr>`; return; }
  tb.innerHTML = rows.slice(0, 20).map(t => `<tr>
    <td><strong>${esc(t.event_type || "—")}</strong></td>
    <td>${esc(t.company_name || t.prospect_id || "—")}</td>
    <td style="font-size:11px">${esc(trunc(t.trace_id || "—", 18))}</td>
    <td>${esc(t.channel || t.provider || "—")}</td>
    <td style="white-space:nowrap;font-size:11px">${esc(fmt(t.timestamp || t.created_at))}</td>
  </tr>`).join("");
}

function renderTracesTimeline(rows) {
  const el = document.getElementById("traces-timeline");
  if (!rows.length) { el.innerHTML = emp("No trace events recorded yet."); return; }
  el.innerHTML = rows.slice(0, 10).map(t => `
    <div class="tl-item">
      <div class="tl-dot"></div>
      <div class="tl-body">
        <div class="tl-evt">${esc(t.event_type || "—")}</div>
        <div class="tl-txt">${esc(trunc(t.payload_summary || "", 70, ""))}</div>
        <div class="tl-meta">
          ${t.channel || t.provider ? bdg(t.channel || t.provider, "s-nil") : ""}
          <span style="font-size:11px;color:var(--muted)">${esc(fmt(t.timestamp || t.created_at))}</span>
        </div>
      </div>
    </div>`).join("");
}

document.getElementById("traces-filter-type").addEventListener("change", e => {
  const f = e.target.value;
  const filtered = f ? _allTraces.filter(t => t.event_type === f) : _allTraces;
  renderTracesTable(filtered);
  renderTracesTimeline(filtered);
});

document.getElementById("traces-refresh").addEventListener("click", () => { loadState(); });

// Settings page
function yesNo(value) {
  return value ? bdg("yes", "s-ok") : bdg("no", "s-warn");
}

function trueFalse(value) {
  return value ? bdg("true", "s-ok") : bdg("false", "s-nil");
}

function renderJudgeRuntimePanel() {
  const el = document.getElementById("settings-judge-runtime");
  if (!el) return;
  const rt = _state?.tenacious_judge_runtime || {};
  const deps = rt.required_ml_deps_available || {};
  const depOrder = ["torch", "transformers", "peft", "unsloth"];
  const depBadges = depOrder.map(name => `${esc(name)} ${yesNo(Boolean(deps[name]))}`).join(" ");
  const runtimeMode = rt.runtime_mode || "fallback";
  el.innerHTML = `
    ${kvr("TENACIOUS_JUDGE_ENABLED", trueFalse(Boolean(rt.tenacious_judge_enabled)))}
    ${kvr("TENACIOUS_COMPARISON_MODE", trueFalse(Boolean(rt.tenacious_comparison_mode)))}
    ${kvr("TENACIOUS_COMPARISON_DRY_RUN", trueFalse(Boolean(rt.tenacious_comparison_dry_run)))}
    ${kvr("adapter path", esc(rt.adapter_path || "—"))}
    ${kvr("adapter path exists", yesNo(Boolean(rt.adapter_path_exists)))}
    ${kvr("required ML deps available", depBadges)}
    ${kvr("runtime mode", bdg(runtimeMode, runtimeMode === "real_model" ? "s-ok" : "s-warn"))}
    ${kvr("last judge error", esc(trunc(rt.last_judge_error || "None", 140, "None")))}`;
}

function renderSettingsPage() {
  document.getElementById("settings-mode").textContent = document.getElementById("kpi-mode")?.textContent || "Preview";
  document.getElementById("settings-health").textContent = document.getElementById("kpi-health")?.textContent || "—";
  document.getElementById("settings-bench").textContent = document.getElementById("kpi-bench")?.textContent || "—";
  renderJudgeRuntimePanel();
  const tools = _state?.tool_statuses || [];
  const el = document.getElementById("settings-providers");
  if (!tools.length) { el.innerHTML = emp("No provider data."); return; }
  el.innerHTML = tools.map(t => `
    <div class="cfg-card">
      <div>
        <div class="cfg-name">${esc(t.label || titl(t.name))}</div>
        <div class="cfg-detail">${esc(trunc(t.details || "", 55, ""))}</div>
      </div>
      ${bdg(titl(t.status || "Not configured"), tone(t.status))}
    </div>`).join("");
}

// ── HEALTH CHECK ─────────────────────────────────────
async function checkHealth() {
  try {
    const data = await (await fetch("/health")).json();
    document.getElementById("kpi-health").textContent = data.status === "ok" ? "Healthy" : "Warning";
  } catch {
    document.getElementById("kpi-health").textContent = "Error";
    document.querySelector(".kpi.green")?.classList.remove("green");
  }
}

// ── LOAD STATE ───────────────────────────────────────
async function loadState() {
  try {
    const [stateResp, comparisonResp] = await Promise.all([
      fetch("/dashboard/state"),
      fetch("/api/comparison-reviews"),
    ]);
    _state = await stateResp.json();
    _comparisonReviews = comparisonResp.ok ? await comparisonResp.json() : [];
    if (_state.recent_snapshots?.length && !_snap) _snap = _state.recent_snapshots[0];
    renderKpis();
    renderToolStatuses();
    renderLatestFlow(_state.latest_flow);
    renderIntelligence(_snap || _state.recent_snapshots?.[0]);
    renderRecentProspects(_state.recent_snapshots || []);
    renderRecentTraces(_state.recent_traces || []);
    renderArtifacts(_state.latest_artifacts || []);
    populatePage(location.hash.slice(1) || "overview");
  } catch (e) {
    console.error("Dashboard load error:", e);
  }
}

// ── TOOLCHAIN RUNNER ─────────────────────────────────
async function runToolchain(payload) {
  const sub = document.getElementById("submit-button");
  const demo = document.getElementById("run-demo-button");
  const statusEl = document.getElementById("status");
  sub.disabled = demo.disabled = true;
  statusEl.textContent = "Running full toolchain…";
  try {
    const r = await fetch("/pipeline/run", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    if (!r.ok) throw new Error("Backend could not generate the brief.");
    _snap = await r.json();
    renderIntelligence(_snap);
    await loadState();
    statusEl.textContent = "Toolchain completed and saved.";
    document.getElementById("prospect-form").reset();
  } catch (e) {
    statusEl.textContent = e.message;
  } finally {
    sub.disabled = demo.disabled = false;
  }
}

document.getElementById("prospect-form").addEventListener("submit", e => {
  e.preventDefault();
  runToolchain(Object.fromEntries(new FormData(e.target)));
});

document.getElementById("run-demo-button").addEventListener("click", () => runToolchain({
  company_name: "Northstar Labs", company_domain: "northstarlabs.ai",
  contact_name: "Jordan Lee", contact_email: "jordan@northstarlabs.ai", contact_phone: "+254700000000",
}));

// ── SIMULATOR ────────────────────────────────────────

let _simProspect = null;
let _simAllCompanies = [];

// Dynamic company loader
async function loadSimCompanies() {
  const grid = document.getElementById("sim-co-grid");
  const countEl = document.getElementById("sim-co-count");
  const searchEl = document.getElementById("sim-co-search");
  if (!grid) return;
  grid.innerHTML = '<div class="empty" style="padding:18px 0">Loading companies…</div>';
  try {
    const data = await (await fetch("/prospects/seed-companies")).json();
    _simAllCompanies = data;
    if (countEl) countEl.textContent = data.length + " compan" + (data.length === 1 ? "y" : "ies");
    if (searchEl) searchEl.value = "";
    simRenderCompanyList(data);
  } catch(err) {
    grid.innerHTML = '<div class="empty">Failed to load companies: ' + esc(err.message) + '</div>';
  }
}

function simRenderCompanyList(list) {
  const grid = document.getElementById("sim-co-grid");
  if (!list.length) {
    grid.innerHTML = '<div class="empty">No companies match your search.</div>';
    return;
  }
  grid.innerHTML = list.map(c => {
    const meta = [
      c.company_domain,
      c.funding_musd ? "$" + c.funding_musd + "M" : null,
      c.employee_count ? c.employee_count + " emp" : null,
      c.sector || null,
    ].filter(Boolean).join(" · ");
    const pillCls = c.in_pipeline ? "pill-active" : "pill-new";
    const pillTxt = c.in_pipeline ? "● Active" : "+ New";
    return `<div class="sim-co"
      data-name="${esc(c.company_name)}" data-domain="${esc(c.company_domain)}"
      data-contact="${esc(c.contact_name || "")}" data-email="${esc(c.contact_email || "")}"
      data-prospect="${esc(c.prospect_id || "")}">
      <div style="min-width:0;flex:1">
        <div class="sim-co-name">${esc(c.company_name)}</div>
        <div class="sim-co-meta">${esc(meta)}</div>
      </div>
      <span class="sim-co-pill ${pillCls}">${pillTxt}</span>
    </div>`;
  }).join("");
  grid.querySelectorAll(".sim-co").forEach(el => {
    el.addEventListener("click", () => {
      grid.querySelectorAll(".sim-co").forEach(c => c.classList.remove("selected"));
      el.classList.add("selected");
      document.getElementById("sim-company").value  = el.dataset.name;
      document.getElementById("sim-domain").value   = el.dataset.domain;
      document.getElementById("sim-contact").value  = el.dataset.contact;
      if (el.dataset.email) document.getElementById("sim-email").value = el.dataset.email;
    });
  });
  // Auto-select first in-pipeline, else first
  const first = list.find(c => c.in_pipeline);
  const firstEl = first
    ? [...grid.querySelectorAll(".sim-co")].find(el => el.dataset.name === first.company_name)
    : grid.querySelector(".sim-co");
  if (firstEl) firstEl.click();
}

function simFilterCompanies(query) {
  const q = query.trim().toLowerCase();
  const filtered = q
    ? _simAllCompanies.filter(c =>
        c.company_name.toLowerCase().includes(q) ||
        (c.company_domain || "").toLowerCase().includes(q) ||
        (c.sector || "").toLowerCase().includes(q)
      )
    : _simAllCompanies;
  const countEl = document.getElementById("sim-co-count");
  if (countEl) countEl.textContent = filtered.length + " compan" + (filtered.length === 1 ? "y" : "ies") + (q ? " found" : "");
  simRenderCompanyList(filtered);
}

function simAddMessage(role, who, text, badges = []) {
  const thread = document.getElementById("sim-thread");
  const empty = thread.querySelector(".sim-empty");
  if (empty) empty.remove();
  const cls = role === "prospect" ? "prospect" : role === "sms" ? "sms-note" : "system";
  const avCls = role === "prospect" ? "p" : role === "sms" ? "sms" : "s";
  const avLabel = role === "prospect" ? "PR" : role === "sms" ? "SMS" : "SYS";
  const badgeHtml = badges.map(b => `<span class="badge ${b.tone}">${esc(b.text)}</span>`).join("");
  thread.insertAdjacentHTML("beforeend", `
    <div class="sim-msg ${cls}">
      <div class="sim-avatar ${avCls}">${avLabel}</div>
      <div class="sim-msg-body">
        <div class="sim-msg-who">${esc(who)}</div>
        <div class="sim-msg-text">${esc(text)}</div>
        ${badgeHtml ? `<div class="sim-badges">${badgeHtml}</div>` : ""}
      </div>
    </div>`);
  thread.scrollTop = thread.scrollHeight;
}

function simAddComparisonMessage(comparison) {
  const thread = document.getElementById("sim-thread");
  const empty = thread.querySelector(".sim-empty");
  if (empty) empty.remove();
  const judgeDisabled = comparison.judge_enabled === false || String(comparison.judge_reason || "").toLowerCase() === "judge disabled";
  const verdict = judgeDisabled ? "judge_disabled" : String(comparison.judge_verdict || "needs_human_review").toLowerCase();
  const decision = String(comparison.final_decision || "human_review").toLowerCase();
  const blocked = decision !== "allow";
  const verdictLabel = judgeDisabled ? "JUDGE DISABLED" : verdict === "needs_human_review" ? "HUMAN REVIEW" : verdict.toUpperCase();
  const decisionLabel = judgeDisabled ? "ALLOW (OLD BEHAVIOR)" : finalDecisionLabel(decision);
  const dryRunNote = comparison.comparison_dry_run
    ? `<div class="comparison-body" style="margin-top:6px"><strong>Dry-run:</strong> no real email/SMS/CRM/calendar action was sent or committed.</div>`
    : "";
  const disabledNote = judgeDisabled
    ? `<div class="comparison-body" style="margin-top:6px"><strong>Setup:</strong> TENACIOUS_JUDGE_ENABLED is not active for this running dashboard, so Week 11 did not review this output.</div>`
    : "";
  const comparisonTitle = comparison.title || "Week 10 vs Week 11 Judge Comparison";
  const baselineTitle = comparison.baseline_title || "Week 10 Baseline Output";
  thread.insertAdjacentHTML("beforeend", `
    <div class="sim-msg system">
      <div class="sim-avatar s">W11</div>
      <div class="sim-msg-body">
        <div class="sim-msg-who">${esc(comparisonTitle)}</div>
        <div class="comparison-grid">
          <div class="comparison-panel">
            <div class="comparison-title">${esc(baselineTitle)}</div>
            <div class="comparison-body">${esc(comparison.baseline_output || "(no baseline output)")}</div>
            <div class="comparison-meta">
              ${bdg(titl(comparison.action_type), "s-info")}
              ${bdg(titl(comparison.channel), "s-nil")}
            </div>
          </div>
          <div class="comparison-panel ${blocked ? "blocked" : ""}">
            <div class="comparison-title">Week 11 Judge Review</div>
            <div class="comparison-meta" style="margin-top:0;margin-bottom:7px">
              ${bdg(verdictLabel, verdictTone(verdict))}
              ${bdg(decisionLabel, decision === "allow" ? "s-ok" : decision === "block" ? "s-err" : "s-warn")}
            </div>
            <div class="comparison-body"><strong>Reason:</strong> ${esc(comparison.judge_reason || "No reason provided.")}</div>
            <div class="comparison-body" style="margin-top:6px"><strong>Improvement:</strong> ${esc(comparison.improvement_summary || "No change.")}</div>
            ${disabledNote}
            ${dryRunNote}
          </div>
        </div>
      </div>
    </div>`);
  thread.scrollTop = thread.scrollHeight;
}

function simEnableButtons(on) {
  document.getElementById("sim-composer").style.display = on ? "block" : "none";
  document.getElementById("sim-send-btn").disabled = !on;
}

document.getElementById("sim-form").addEventListener("submit", async e => {
  e.preventDefault();
  const btn = document.getElementById("sim-run-btn");
  const status = document.getElementById("sim-run-status");
  btn.disabled = true;
  status.textContent = "Running pipeline…";
  try {
    const payload = {
      company_name:   document.getElementById("sim-company").value.trim(),
      company_domain: document.getElementById("sim-domain").value.trim(),
      contact_name:   document.getElementById("sim-contact").value.trim(),
      contact_email:  document.getElementById("sim-email").value.trim(),
      contact_phone:  document.getElementById("sim-phone").value.trim(),
    };
    const r = await fetch("/pipeline/run", { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(payload) });
    if (!r.ok) throw new Error("Pipeline failed");
    _simProspect = await r.json();
    const p = _simProspect.prospect;

    // Update UI
    document.getElementById("sim-prospect-badge").textContent = p.prospect_id;
    document.getElementById("sim-prospect-badge").className = "badge s-ok";
    document.getElementById("sim-channel-badge").textContent = "Email thread open";
    document.getElementById("sim-channel-badge").className = "badge s-info";
    document.getElementById("sim-prospect-card").hidden = false;
    document.getElementById("sim-prospect-kv").innerHTML = `
      <div class="kvr"><span class="kk">Prospect ID</span><span class="kv-val" style="font-size:11px">${esc(p.prospect_id)}</span></div>
      <div class="kvr"><span class="kk">Company</span><span class="kv-val">${esc(p.company_name)}</span></div>
      <div class="kvr"><span class="kk">Segment</span><span class="kv-val">${esc(p.primary_segment_label || p.primary_segment)}</span></div>
      <div class="kvr"><span class="kk">AI Maturity</span><span class="kv-val">${esc(p.ai_maturity_score)}/3</span></div>
      <div class="kvr"><span class="kk">Status</span><span class="kv-val">${esc(p.status)}</span></div>
    `;

    const emailResult = (_simProspect.toolchain_report?.results || []).find(x => x.name === "email");
    const emailStatus = String(emailResult?.status || "previewed").toLowerCase();
    const emailReallySent = emailStatus === "executed" && String(emailResult?.message || "").toLowerCase().includes("live email");
    const emailBlocked = emailStatus === "skipped";
    const emailLine = emailReallySent
      ? `Pipeline complete. Live initial outreach email submitted to ${p.contact_email || "prospect"}.`
      : emailBlocked
      ? `Pipeline stopped. Initial outreach was not sent: ${emailResult?.message || "blocked before delivery"}.`
      : `Pipeline complete. Initial outreach email was previewed locally for ${p.contact_email || "prospect"}; no real email was delivered.`;

    // Add initial system message to thread
    document.getElementById("sim-thread").innerHTML = "";
    simAddMessage("system", emailReallySent ? "Tenacious System — Initial Email Sent" : emailBlocked ? "Tenacious System — Initial Email Blocked" : "Tenacious System — Initial Email Preview", emailLine, [
      { text: p.primary_segment_label || p.primary_segment, tone: "s-info" },
      { text: "AI Maturity " + p.ai_maturity_score + "/3", tone: "s-nil" },
      { text: titl(emailStatus), tone: tone(emailStatus) },
    ]);
    try {
      const art = await fetch(`/artifacts/${p.prospect_id}/email`);
      if (art.ok) {
        const emailArtifact = JSON.parse(await art.text());
        const judgeReview = emailArtifact.judge_review || {};
        const verdict = String(judgeReview.verdict || "").toLowerCase();
        if (verdict || judgeReview.reason) {
          simAddComparisonMessage({
            title: "Week 11 Initial Outreach Review",
            baseline_title: "Initial Outreach Draft",
            baseline_output: `Subject: ${emailArtifact.subject || ""}\n\n${emailArtifact.body || ""}`,
            action_type: "email",
            channel: "email",
            judge_verdict: verdict || "pass",
            judge_reason: judgeReview.reason || "No reason provided.",
            final_decision: emailBlocked ? "human_review" : "allow",
            improvement_summary: emailBlocked
              ? "Stopped initial outreach before sending."
              : "Initial outreach passed the Week 11 guardrail.",
            comparison_dry_run: Boolean(emailArtifact.comparison_dry_run),
            judge_enabled: String(judgeReview.reason || "").toLowerCase() !== "judge disabled",
          });
        }
      }
    } catch {}
    simEnableButtons(true);
    status.textContent = "Prospect created. Type a message to continue the conversation.";
    await loadState();
  } catch(err) {
    status.textContent = "Error: " + err.message;
  } finally {
    btn.disabled = false;
  }
});

async function simSend() {
  if (!_simProspect) return;
  const p = _simProspect.prospect;
  const customBody = document.getElementById("sim-body-input").value.trim();
  if (!customBody) return;

  const statusEl = document.getElementById("sim-reply-status");
  document.getElementById("sim-send-btn").disabled = true;
  statusEl.textContent = "Sending…";

  simAddMessage("prospect", p.contact_name || "Prospect", customBody);

  try {
    const payload = {
      prospect_id:   p.prospect_id,
      contact_email: p.contact_email,
      contact_phone: p.contact_phone,
      channel:       "email",
      body:          customBody,
    };
    const r = await fetch("/conversations/reply", { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(payload) });
    if (!r.ok) throw new Error("Reply failed");
    const d = await r.json();

    // Extract reply text (strip Subject: line)
    let replyText = d.reply_draft || "";
    if (replyText.toLowerCase().startsWith("subject:")) {
      const lines = replyText.split("\\n");
      replyText = lines.slice(1).join("\\n").trim();
    }

    const actionTone = d.next_action === "handoff_human" ? "s-warn" : d.next_action === "book_meeting" ? "s-ok" : "s-info";
    const badges = [
      { text: titl(d.next_action), tone: actionTone },
      ...(d.risk_flags || []).filter(f => !f.startsWith("sms_skipped:")).map(f => ({ text: f, tone: "s-warn" })),
    ];
    simAddMessage("system", "Tenacious System — Email Reply", replyText || "(no reply draft)", badges);

    // Run judge on the actual reply and show the verdict panel
    if (replyText) {
      try {
        const judgePayload = {
          prospect_id:     p.prospect_id,
          contact_email:   p.contact_email,
          contact_phone:   p.contact_phone,
          channel:         "email",
          body:            customBody,
          baseline_output: replyText,
        };
        const jr = await fetch("/api/simulator/compare-reply", { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(judgePayload) });
        if (jr.ok) {
          const jc = await jr.json();
          simAddComparisonMessage({
            ...jc,
            title: "Week 11 Agent Reply — Judge Review",
            baseline_title: "Week 11 Agent Reply",
            improvement_summary: jc.final_decision === "allow"
              ? "Agent reply passed the Week 11 guardrail."
              : (jc.improvement_summary || "Agent reply blocked by Week 11 judge."),
          });
        }
      } catch { /* judge review is best-effort */ }
    }

    // Show SMS result — check actual risk flags from server
    const flags = d.risk_flags || [];
    const smsBlocked = flags.includes("sms_warm_lead_gate_blocked");
    const smsFailed  = flags.includes("sms_handoff_failed");
    const smsSkipped = flags.some(f => f.startsWith("sms_skipped:"));
    const bodyLower  = customBody.toLowerCase();
    const hasSmsToken = ["sms","text me","whatsapp","call me","phone me"].some(t => bodyLower.includes(t));
    const hasSchedToken = ["call","calendar","meet","meeting","schedule","next week","tomorrow","book"].some(t => bodyLower.includes(t));
    const smsSent = (hasSmsToken || hasSchedToken) && !smsBlocked && !smsFailed && !smsSkipped;
    if (smsSent) {
      try {
        const art = await fetch(`/artifacts/${p.prospect_id}/sms`);
        if (art.ok) {
          const artData = JSON.parse(await art.text());
          simAddMessage("sms", "Africa\'s Talking SMS → " + (p.contact_phone || "prospect"), artData.body || "Booking link sent.");
        }
      } catch {
        simAddMessage("sms", "Africa\'s Talking SMS → " + (p.contact_phone || "prospect"), "Booking link sent — check the AT Simulator.");
      }
    } else if (smsBlocked) {
      simAddMessage("sms", "SMS — gate blocked", "No prior email reply recorded; SMS not sent.");
    }

    statusEl.textContent = "Sent — " + titl(d.next_action || "");
    document.getElementById("sim-body-input").value = "";
    await loadState();
  } catch(err) {
    simAddMessage("system", "System Error", err.message);
    statusEl.textContent = "Error: " + err.message;
  } finally {
    document.getElementById("sim-send-btn").disabled = false;
  }
}

document.getElementById("sim-reset-btn").addEventListener("click", () => {
  _simProspect = null;
  document.getElementById("sim-prospect-badge").textContent = "Not created";
  document.getElementById("sim-prospect-badge").className = "badge s-nil";
  document.getElementById("sim-channel-badge").textContent = "Waiting for prospect";
  document.getElementById("sim-channel-badge").className = "badge s-nil";
  document.getElementById("sim-prospect-card").hidden = true;
  document.getElementById("sim-thread").innerHTML = '<div class="sim-empty">Create a prospect to start the conversation.</div>';
  document.getElementById("sim-form").reset();
  _simCompaniesLoaded = false;
  loadSimCompanies();
  document.getElementById("sim-run-status").textContent = "";
  document.getElementById("sim-reply-status").textContent = "";
  simEnableButtons(false);
});

// ── INIT ─────────────────────────────────────────────
checkHealth();
loadState();
showPage(location.hash.slice(1) || "overview");
</script>
</body>
</html>
"""
