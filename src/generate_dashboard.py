"""
Generate docs/index.html from sent_jobs_log.json.
Run after each digest send (or manually) to refresh the dashboard.
"""

import json
from datetime import datetime
from pathlib import Path

LOG_FILE = Path(__file__).resolve().parent.parent / "sent_jobs_log.json"
DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"

SOURCE_COLORS = {
    "Indeed": "#003A9B",
    "RemoteOK": "#00B65A",
    "We Work Remotely": "#1B4332",
    "Remotive": "#6C47FF",
    "Arbeitnow": "#E85D04",
    "The Muse": "#F72585",
    "USA Jobs": "#B5121B",
    "ZipRecruiter": "#00A651",
    "LinkedIn": "#0077B5",
}

SCORE_LABELS = {5: "⭐ Top Match", 4: "Strong Match", 3: "Good Match"}


def _badge(text: str, bg: str, color: str = "white", border: str = "") -> str:
    border_style = f"border:1px solid {border};" if border else ""
    return (
        f'<span style="background:{bg};color:{color};{border_style}'
        f'padding:2px 9px;border-radius:12px;font-size:11px;font-weight:600;'
        f'white-space:nowrap">{text}</span>'
    )


def _source_badge(source: str) -> str:
    return _badge(source, SOURCE_COLORS.get(source, "#555"))


def _score_badge(score) -> str:
    if not score or score < 3:
        return ""
    label = SCORE_LABELS.get(score, "Match")
    bg = "#1a7f37" if score == 5 else "#b08800" if score == 4 else "#555"
    return _badge(label, bg)


def _job_row(job: dict) -> str:
    title = job.get("title") or f"[details unavailable — {job.get('id', '')}]"
    company = job.get("company") or ""
    url = job.get("url") or "#"
    source = job.get("source") or ""
    score = job.get("score")
    licenses = job.get("licenses") or []
    is_new = job.get("is_new", True)
    summary = job.get("summary") or ""

    has_link = url and url != "#"
    title_html = (
        f'<a href="{url}" target="_blank" rel="noopener" '
        f'style="color:#0550AE;text-decoration:none;font-weight:600">{title}</a>'
        if has_link
        else f'<span style="color:#888;font-style:italic">{title}</span>'
    )

    status_badge = (
        _badge("✨ New", "#dff0d8", "#2d6a1e", "#b2d7a0")
        if is_new
        else _badge("↩ Still Available", "#f0f0f0", "#555", "#d0d0d0")
    )

    license_html = " ".join(
        _badge(f"🪪 {lic}", "#fff0f3", "#9b1c3a", "#f5c6cb") for lic in licenses
    )

    company_html = (
        f'<span style="color:#555;font-size:13px"> &middot; {company}</span>'
        if company
        else ""
    )

    summary_html = (
        f'<div style="color:#555;font-size:12px;margin-top:4px;line-height:1.5">{summary}</div>'
        if summary
        else ""
    )

    return f"""
    <li style="padding:12px 0;border-bottom:1px solid #f0f0f0;list-style:none">
      <div style="display:flex;flex-wrap:wrap;gap:4px;align-items:center;margin-bottom:4px">
        {status_badge}
        {_source_badge(source) if source else ""}
        {_score_badge(score)}
        {license_html}
      </div>
      <div style="font-size:15px">{title_html}{company_html}</div>
      {summary_html}
    </li>"""


def _send_block(send: dict, idx: int) -> str:
    date_str = send.get("date", "Unknown")
    new_count = send.get("new_count", 0)
    returning_count = send.get("returning_count", 0)
    jobs = send.get("jobs", [])
    total = new_count + returning_count

    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        date_label = dt.strftime("%A, %B %d, %Y")
    except Exception:
        date_label = date_str

    count_parts = []
    if new_count:
        count_parts.append(
            _badge(f"✨ {new_count} new", "#dff0d8", "#2d6a1e", "#b2d7a0")
        )
    if returning_count:
        count_parts.append(
            _badge(f"↩ {returning_count} still available", "#f0f0f0", "#555", "#d0d0d0")
        )
    count_html = " ".join(count_parts)

    sorted_jobs = sorted(
        jobs,
        key=lambda j: (0 if j.get("is_new", True) else 1, -(j.get("score") or 0)),
    )
    job_rows = "".join(_job_row(j) for j in sorted_jobs)

    open_attr = " open" if idx == 0 else ""

    return f"""
  <details{open_attr} style="background:white;border:1px solid #e1e4e8;border-radius:8px;
                              margin-bottom:12px;overflow:hidden">
    <summary style="padding:16px 20px;cursor:pointer;list-style:none;
                    display:flex;justify-content:space-between;align-items:center;
                    user-select:none;background:#fafbfc">
      <div>
        <span style="font-weight:700;font-size:16px;color:#0f0f0f">{date_label}</span>
        <span style="color:#888;font-size:13px;margin-left:10px">{total} job{"s" if total != 1 else ""}</span>
      </div>
      <div style="display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end">
        {count_html}
      </div>
    </summary>
    <ul style="margin:0;padding:0 20px 4px 20px">
      {job_rows}
    </ul>
  </details>"""


def generate() -> None:
    DOCS_DIR.mkdir(exist_ok=True)

    if not LOG_FILE.exists():
        data: dict = {"sends": []}
    else:
        data = json.loads(LOG_FILE.read_text())

    sends = data.get("sends", [])
    sends_sorted = sorted(sends, key=lambda s: s.get("date", ""), reverse=True)

    total_sends = len(sends_sorted)
    total_jobs_sent = sum(s.get("new_count", 0) for s in sends_sorted)

    send_blocks = "".join(_send_block(s, i) for i, s in enumerate(sends_sorted))

    if not sends_sorted:
        send_blocks = """
  <div style="background:#fff8e1;border:1px solid #ffe082;border-radius:8px;
              padding:32px;text-align:center;color:#5d4037">
    <p style="margin:0;font-size:16px">No emails sent yet.</p>
    <p style="margin:8px 0 0;font-size:13px;color:#888">
      Once the daily digest runs, sends will appear here.
    </p>
  </div>"""

    generated_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Remote Social Work Digest — Send History</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; padding: 0; background: #f6f8fa;
         font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }}
  details > summary::-webkit-details-marker {{ display: none; }}
  details > summary::marker {{ display: none; }}
  details[open] > summary {{
    border-bottom: 1px solid #e1e4e8;
  }}
  details > summary::after {{
    content: '▶';
    font-size: 10px;
    color: #888;
    margin-left: 8px;
    transition: transform 0.2s;
    display: inline-block;
  }}
  details[open] > summary::after {{
    transform: rotate(90deg);
  }}
  a:hover {{ text-decoration: underline !important; }}
</style>
</head>
<body>
<div style="max-width:720px;margin:0 auto;padding:24px 16px">

  <!-- Header -->
  <div style="background:linear-gradient(135deg,#1a365d,#2b6cb0);border-radius:12px;
              padding:28px 24px;margin-bottom:24px;text-align:center">
    <h1 style="margin:0 0 4px 0;color:white;font-size:24px;font-weight:700">
      🏠 Remote Social Work Digest
    </h1>
    <p style="margin:0;color:#bee3f8;font-size:14px">Send History</p>
  </div>

  <!-- Stats -->
  <div style="display:flex;gap:12px;margin-bottom:24px;flex-wrap:wrap">
    <div style="flex:1;min-width:140px;background:white;border:1px solid #e1e4e8;
                border-radius:8px;padding:16px 20px;text-align:center">
      <div style="font-size:32px;font-weight:700;color:#0550AE">{total_sends}</div>
      <div style="color:#666;font-size:13px;margin-top:2px">emails sent</div>
    </div>
    <div style="flex:1;min-width:140px;background:white;border:1px solid #e1e4e8;
                border-radius:8px;padding:16px 20px;text-align:center">
      <div style="font-size:32px;font-weight:700;color:#1a7f37">{total_jobs_sent}</div>
      <div style="color:#666;font-size:13px;margin-top:2px">new jobs shared</div>
    </div>
  </div>

  <!-- Send history -->
  <h2 style="font-size:14px;font-weight:600;color:#888;text-transform:uppercase;
             letter-spacing:0.5px;margin:0 0 12px 0">Send History</h2>

  {send_blocks}

  <!-- Footer -->
  <div style="text-align:center;padding:20px 0;margin-top:8px;
              border-top:1px solid #e1e4e8">
    <p style="margin:0;color:#aaa;font-size:11px">
      Generated {generated_at} · Curated by Claude AI
    </p>
  </div>

</div>
</body>
</html>"""

    out = DOCS_DIR / "index.html"
    out.write_text(html, encoding="utf-8")
    print(f"Dashboard written to {out}")
    print(f"  {total_sends} sends · {total_jobs_sent} new jobs on record")


if __name__ == "__main__":
    generate()
