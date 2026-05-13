"""
Arbeitnow scraper — free REST API, no auth required.
Remote filter built in; we add keyword filtering for social work roles.
"""

import logging
import re
import requests

from .keywords import is_social_work_job

logger = logging.getLogger(__name__)

ARBEITNOW_API = "https://arbeitnow.com/api/job-board-api"


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text or "").strip()


def fetch() -> list[dict]:
    jobs = []
    page = 1

    while page <= 5:  # cap at 5 pages to avoid runaway fetches
        try:
            resp = requests.get(
                ARBEITNOW_API,
                params={"page": page, "remote": "true"},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error(f"Arbeitnow fetch error (page {page}): {e}")
            break

        items = data.get("data", [])
        if not items:
            break

        for item in items:
            title = item.get("title", "")
            description = _strip_html(item.get("description", ""))
            tags = item.get("tags", []) or []

            if not item.get("remote", False):
                continue

            if not is_social_work_job(title, f"{description} {' '.join(tags)}", tags):
                continue

            job_url = item.get("url", "")
            jobs.append({
                "id": f"arbeitnow:{item.get('slug', job_url)}",
                "title": title,
                "company": item.get("company_name", "Unknown Company"),
                "location": "Remote",
                "url": job_url,
                "description": description[:1500],
                "salary": None,
                "posted_at": item.get("created_at"),
                "source": "Arbeitnow",
                "tags": tags,
            })

        if not data.get("links", {}).get("next"):
            break
        page += 1

    logger.info(f"Arbeitnow: {len(jobs)} social work jobs found")
    return jobs
