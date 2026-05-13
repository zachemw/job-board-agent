"""
Remotive scraper — free REST API, no auth required.
Returns remote-only jobs; we filter for social work relevance.
"""

import logging
import re
import requests

from .keywords import is_social_work_job

logger = logging.getLogger(__name__)

REMOTIVE_API = "https://remotive.com/api/remote-jobs"


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text or "").strip()


def fetch() -> list[dict]:
    try:
        resp = requests.get(REMOTIVE_API, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.error(f"Remotive fetch error: {e}")
        return []

    jobs_data = data.get("jobs", [])
    jobs = []

    for item in jobs_data:
        title = item.get("title", "")
        description = _strip_html(item.get("description", ""))
        tags = item.get("tags", []) or []
        candidate_region = item.get("candidate_required_location", "")
        job_type = item.get("job_type", "")

        if not is_social_work_job(title, f"{description} {' '.join(tags)}", tags):
            continue

        job_url = item.get("url", "")
        salary = item.get("salary", "") or None

        jobs.append({
            "id": f"remotive:{item.get('id', job_url)}",
            "title": title,
            "company": item.get("company_name", "Unknown Company"),
            "location": candidate_region or "Remote Worldwide",
            "url": job_url,
            "description": description[:1500],
            "salary": salary,
            "posted_at": item.get("publication_date"),
            "source": "Remotive",
            "tags": tags,
        })

    logger.info(f"Remotive: {len(jobs)} social work jobs found from {len(jobs_data)} total")
    return jobs
