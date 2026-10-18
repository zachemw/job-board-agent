"""
Persistent job history — tracks every job ID that has been emailed.

sent_jobs.json  — lightweight dedup index: {id: date}
sent_jobs_log.json — rich send history used by the dashboard
"""

import json
import logging
from datetime import date
from pathlib import Path

logger = logging.getLogger(__name__)

HISTORY_FILE = Path(__file__).resolve().parent.parent / "sent_jobs.json"
LOG_FILE = Path(__file__).resolve().parent.parent / "sent_jobs_log.json"


def _load() -> dict:
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text())
        except Exception as e:
            logger.warning(f"Could not read history file, starting fresh: {e}")
    return {"sent": {}}


def _save(data: dict) -> None:
    HISTORY_FILE.write_text(json.dumps(data, indent=2))


def mark_seen(jobs: list[dict]) -> list[dict]:
    """
    Compares jobs against history. Returns the same list with an added
    'is_new' bool on each job. Does NOT save to disk yet — call save_sent()
    after a successful email send.
    """
    data = _load()
    sent = data.get("sent", {})
    for job in jobs:
        job["is_new"] = job["id"] not in sent
    return jobs


def save_sent(jobs: list[dict]) -> None:
    """Persist all job IDs in this batch as sent (only newly seen ones get a date)."""
    data = _load()
    sent = data.setdefault("sent", {})
    today = date.today().isoformat()
    for job in jobs:
        if job["id"] not in sent:
            sent[job["id"]] = today
    _save(data)
    logger.info(f"History saved: {len(sent)} total jobs on record")


def count_new(jobs: list[dict]) -> int:
    return sum(1 for j in jobs if j.get("is_new", True))


def save_send_log(jobs: list[dict]) -> None:
    """Append this send's full job details to sent_jobs_log.json for the dashboard."""
    if LOG_FILE.exists():
        try:
            data = json.loads(LOG_FILE.read_text())
        except Exception:
            data = {"sends": []}
    else:
        data = {"sends": []}

    today = date.today().isoformat()
    new_count = sum(1 for j in jobs if j.get("is_new", True))
    returning_count = len(jobs) - new_count

    entry = {
        "date": today,
        "new_count": new_count,
        "returning_count": returning_count,
        "jobs": [
            {
                "id": j.get("id"),
                "title": j.get("title"),
                "company": j.get("company"),
                "url": j.get("url"),
                "source": j.get("source"),
                "score": j.get("score"),
                "summary": j.get("summary"),
                "licenses": j.get("licenses", []),
                "is_new": j.get("is_new", True),
            }
            for j in jobs
        ],
    }
    data["sends"].append(entry)
    LOG_FILE.write_text(json.dumps(data, indent=2))
    logger.info(f"Send log updated: {len(data['sends'])} total sends on record")
