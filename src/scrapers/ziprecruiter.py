"""
ZipRecruiter scraper via their Partner API.
Requires a free partner API key from: https://www.ziprecruiter.com/jobs-api/docs
Set ZIPRECRUITER_API_KEY in your .env file.

Note: ZipRecruiter's consumer job search does not expose a public RSS feed.
The Partner API (free to register) provides access to their full job index.
"""

import logging
import os
import re
import requests

logger = logging.getLogger(__name__)

ZIPRECRUITER_API = "https://api.ziprecruiter.com/jobs/v1"

SOCIAL_WORK_QUERIES = [
    "remote social worker",
    "remote LCSW",
    "remote LMSW",
    "remote case manager social work",
    "telehealth therapist",
    "remote behavioral health counselor",
]


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text or "").strip()


def fetch() -> list[dict]:
    api_key = os.getenv("ZIPRECRUITER_API_KEY", "")
    if not api_key:
        logger.info("ZipRecruiter: skipping — ZIPRECRUITER_API_KEY not set")
        return []

    jobs = []
    seen_ids = set()

    for query in SOCIAL_WORK_QUERIES:
        try:
            resp = requests.get(
                ZIPRECRUITER_API,
                params={
                    "search": query,
                    "location": "Remote",
                    "radius_miles": 0,
                    "days_ago": 7,
                    "jobs_per_page": 20,
                    "page": 1,
                    "api_key": api_key,
                },
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error(f"ZipRecruiter fetch error [{query}]: {e}")
            continue

        for item in data.get("jobs", []):
            job_id = str(item.get("id", ""))
            if job_id in seen_ids:
                continue
            seen_ids.add(job_id)

            description = _strip_html(item.get("snippet", "") or item.get("description", ""))
            salary_min = item.get("compensation_min")
            salary_max = item.get("compensation_max")
            salary = None
            if salary_min and salary_max:
                salary = f"${salary_min:,.0f}–${salary_max:,.0f}/yr"

            jobs.append({
                "id": f"ziprecruiter:{job_id}",
                "title": item.get("name", ""),
                "company": item.get("hiring_company", {}).get("name", "Unknown Company"),
                "location": item.get("location", "Remote"),
                "url": item.get("url", ""),
                "description": description[:1500],
                "salary": salary,
                "posted_at": item.get("posted_time"),
                "source": "ZipRecruiter",
                "tags": [],
            })

        logger.info(f"ZipRecruiter [{query}]: {len(data.get('jobs', []))} results")

    return jobs
