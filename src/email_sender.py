"""
Email digest sender via Resend API.
Builds an HTML digest and sends it to the recipient.
"""

import logging
import os
from datetime import datetime
import resend

logger = logging.getLogger(__name__)

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


def _source_badge(source: str) -> str:
    color = SOURCE_COLORS.get(source, "#555555")
    return (
        f'<span style="background:{color};color:white;padding:2px 8px;'
        f'border-radius:12px;font-size:11px;font-weight:600;'
        f'letter-spacing:0.5px">{source}</span>'
    )


def _score_badge(score: int) -> str:
    if score < 3:
        return ""
    label = SCORE_LABELS.get(score, "Match")
    bg = "#1a7f37" if score == 5 else "#b08800" if score == 4 else "#444"
    return (
        f'<span style="background:{bg};color:white;padding:2px 8px;'
        f'border-radius:12px;font-size:11px;font-weight:600;margin-left:6px">'
        f'{label}</span>'
    )


def _still_available_badge() -> str:
    return (
        '<span style="background:#f0f0f0;color:#555;border:1px solid #d0d0d0;'
        'padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600;'
        'margin-left:6px">↩ Still Available</span>'
    )


def _new_badge() -> str:
    return (
        '<span style="background:#dff0d8;color:#2d6a1e;border:1px solid #b2d7a0;'
        'padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600;'
        'margin-left:6px">✨ New</span>'
    )


def _license_badges(licenses: list) -> str:
    if not licenses:
        return ""
    badges = []
    for lic in licenses:
        badges.append(
            f'<span style="background:#fff0f3;color:#9b1c3a;border:1px solid #f5c6cb;'
            f'padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600;'
            f'margin-left:6px">🪪 {lic}</span>'
        )
    return "".join(badges)


def _job_card(job: dict) -> str:
    title = job.get("title", "Unknown Title")
    company = job.get("company", "Unknown Company")
    location = job.get("location", "Remote")
    salary = job.get("salary")
    url = job.get("url", "#")
    source = job.get("source", "")
    summary = job.get("summary", "")
    score = job.get("score", 3)
    posted_at = job.get("posted_at", "")
    licenses = job.get("licenses", [])
    is_new = job.get("is_new", True)

    # Format posted date
    date_str = ""
    if posted_at:
        try:
            dt = datetime.fromisoformat(posted_at.replace("Z", "+00:00"))
            date_str = dt.strftime("%b %d")
        except Exception:
            date_str = ""

    salary_html = (
        f'<span style="color:#1a7f37;font-weight:600;font-size:14px">{salary}</span>'
        if salary else ""
    )

    date_html = (
        f'<span style="color:#888;font-size:12px;margin-left:8px">Posted {date_str}</span>'
        if date_str else ""
    )

    return f"""
<div style="background:#ffffff;border:1px solid #e1e4e8;border-radius:8px;
            padding:20px;margin-bottom:16px;border-left:4px solid {SOURCE_COLORS.get(source, '#888')}">
  <div style="margin-bottom:8px;line-height:2">
    {_source_badge(source)}{_score_badge(score)}{"" if is_new else _still_available_badge()}{_license_badges(licenses)}
    {date_html}
  </div>
  <h3 style="margin:0 0 4px 0;font-size:17px;color:#0f0f0f">
    <a href="{url}" style="color:#0550AE;text-decoration:none">{title}</a>
  </h3>
  <p style="margin:0 0 10px 0;color:#444;font-size:14px">
    <strong>{company}</strong>
    <span style="color:#888"> &middot; {location}</span>
  </p>
  {f'<p style="margin:0 0 10px 0">{salary_html}</p>' if salary else ""}
  {f'<p style="margin:0 0 12px 0;color:#333;font-size:14px;line-height:1.5">{summary}</p>' if summary else ""}
  <a href="{url}"
     style="display:inline-block;background:#0550AE;color:white;padding:8px 18px;
            border-radius:6px;text-decoration:none;font-size:13px;font-weight:600">
    View Job →
  </a>
</div>"""


def build_html(jobs: list[dict], total_scraped: int, sources_summary: dict) -> str:
    today = datetime.now().strftime("%A, %B %d, %Y")

    # New jobs first, then returning — within each group, score descending
    sorted_jobs = sorted(jobs, key=lambda j: (0 if j.get("is_new", True) else 1, -j.get("score", 3)))
    new_count = sum(1 for j in jobs if j.get("is_new", True))
    returning_count = len(jobs) - new_count
    job_count = len(jobs)

    source_pills = "".join(
        f'<span style="background:#f3f4f6;color:#444;padding:3px 10px;'
        f'border-radius:12px;font-size:12px;margin:2px;display:inline-block">'
        f'{src}: {count}</span>'
        for src, count in sorted(sources_summary.items(), key=lambda x: -x[1])
        if count > 0
    )

    job_cards = "".join(_job_card(job) for job in sorted_jobs)

    no_jobs_msg = """
<div style="background:#fff8e1;border:1px solid #ffe082;border-radius:8px;
            padding:24px;text-align:center;color:#5d4037">
  <p style="margin:0;font-size:16px">No new remote social work jobs found today.</p>
  <p style="margin:8px 0 0 0;font-size:14px;color:#888">Check back tomorrow!</p>
</div>""" if not jobs else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Remote Social Work Jobs — {today}</title>
</head>
<body style="margin:0;padding:0;background:#f6f8fa;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif">
<div style="max-width:640px;margin:0 auto;padding:24px 16px">

  <!-- Header -->
  <div style="background:linear-gradient(135deg,#1a365d,#2b6cb0);border-radius:12px;
              padding:28px 24px;margin-bottom:24px;text-align:center">
    <h1 style="margin:0 0 4px 0;color:white;font-size:24px;font-weight:700">
      🏠 Remote Social Work Jobs
    </h1>
    <p style="margin:0;color:#bee3f8;font-size:14px">{today}</p>
  </div>

  <!-- Stats bar -->
  <div style="background:white;border:1px solid #e1e4e8;border-radius:8px;
              padding:16px 20px;margin-bottom:20px">
    <div style="margin-bottom:6px">
      <span style="font-size:28px;font-weight:700;color:#0550AE">{job_count}</span>
      <span style="color:#444;font-size:14px;margin-left:8px">curated positions</span>
    </div>
    <div>
      {f'<span style="background:#dff0d8;color:#2d6a1e;border:1px solid #b2d7a0;padding:2px 10px;border-radius:12px;font-size:12px;font-weight:600;margin-right:6px">✨ {new_count} new</span>' if new_count else ''}
      {f'<span style="background:#f0f0f0;color:#555;border:1px solid #d0d0d0;padding:2px 10px;border-radius:12px;font-size:12px;font-weight:600">↩ {returning_count} still available</span>' if returning_count else ''}
    </div>
  </div>

  <!-- Source breakdown -->
  <div style="margin-bottom:20px">
    <p style="margin:0 0 8px 0;font-size:12px;color:#888;font-weight:600;
              text-transform:uppercase;letter-spacing:0.5px">Sources checked</p>
    <div>{source_pills}</div>
  </div>

  <!-- Job cards -->
  {job_cards}
  {no_jobs_msg}

  <!-- Footer -->
  <div style="text-align:center;padding:20px 0;border-top:1px solid #e1e4e8;margin-top:24px">
    <p style="margin:0;color:#888;font-size:12px">
      Curated by Claude · Remote Social Work Digest
    </p>
    <p style="margin:4px 0 0 0;color:#aaa;font-size:11px">
      Scraped from: Indeed, RemoteOK, We Work Remotely, Remotive, Arbeitnow, The Muse, USA Jobs, ZipRecruiter, LinkedIn
    </p>
  </div>

</div>
</body>
</html>"""


def send_digest(jobs: list[dict], total_scraped: int, sources_summary: dict) -> bool:
    resend.api_key = os.environ["RESEND_API_KEY"]
    recipient = os.environ["RECIPIENT_EMAIL"]
    sender = os.getenv("SENDER_EMAIL", "Remote Social Work Digest <digest@resend.dev>")

    today = datetime.now().strftime("%B %d, %Y")
    subject = f"🏠 {len(jobs)} Remote Social Work Jobs — {today}"
    if not jobs:
        subject = f"Remote Social Work Digest — No new jobs today ({today})"

    html = build_html(jobs, total_scraped, sources_summary)

    try:
        result = resend.Emails.send({
            "from": sender,
            "to": [recipient],
            "subject": subject,
            "html": html,
        })
        logger.info(f"Email sent successfully: {result}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False
