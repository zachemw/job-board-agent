"""
RemoteOK scraper — free JSON API, no auth required.
Filters by social-work-relevant tags and title keywords.
"""

import logging
import re
import requests

from .keywords import is_social_work_job

logger = logging.getLogger(__name__)

REMOTEOK_API = "https://remoteok.com/remote-jobs.json"

HEADERS = {
    # RemoteOK returns 403 without a browser-like UA
    "User-Agent": "Mozilla/5.0 (compatible; job-digest-bot/1.0)",
}


def fetch() -> list[dict]:
    try:
        resp = requests.get(REMOTEOK_API, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.error(f"RemoteOK fetch error: {e}")
        return []

    jobs = []
    # First entry is metadata, skip it
    for item in data[1:]:
        if not isinstance(item, dict):
            continue

        title = item.get("position", "")
        description = item.get("description", "")
        tags = item.get("tags", []) or []
        tags_str = " ".join(tags)

        if not is_social_work_job(title, f"{description} {tags_str}", tags):
            continue

        job_url = item.get("url", "") or f"https://remoteok.com/remote-jobs/{item.get('id', '')}"
        salary = None
        salary_min = item.get("salary_min")
        salary_max = item.get("salary_max")
        if salary_min and salary_max:
            salary = f"${salary_min:,}–${salary_max:,}/yr"
        elif salary_min:
            salary = f"${salary_min:,}+/yr"

        jobs.append({
            "id": f"remoteok:{item.get('id', job_url)}",
            "title": title,
            "company": item.get("company", "Unknown Company"),
            "location": "Remote",
            "url": job_url,
            "description": re.sub(r"<[^>]+>", " ", description)[:1500],
            "salary": salary,
            "posted_at": item.get("date"),
            "source": "RemoteOK",
            "tags": tags,
        })

    logger.info(f"RemoteOK: {len(jobs)} social work jobs found")
    return jobs
