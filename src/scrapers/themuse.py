"""
The Muse scraper — free public API, no auth required.
Has a "Social Work" category and remote location filter.
"""

import logging
import re
import requests

from .keywords import is_social_work_job

logger = logging.getLogger(__name__)

MUSE_API = "https://www.themuse.com/api/public/jobs"

LOCATION_KEYWORDS = re.compile(
    r"remote|work.?from.?home|wfh|virtual|telecommut|anywhere",
    re.IGNORECASE,
)

# The Muse categories relevant to social work
MUSE_CATEGORIES = [
    "Social Work",
    "Healthcare & Nursing",
    "Counseling",
]


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text or "").strip()


def _is_remote(item: dict) -> bool:
    locations = item.get("locations", []) or []
    for loc in locations:
        if LOCATION_KEYWORDS.search(loc.get("name", "")):
            return True
    return False


def fetch() -> list[dict]:
    jobs = []
    seen_ids = set()

    for category in MUSE_CATEGORIES:
        page = 0
        while page < 3:  # max 3 pages per category
            try:
                resp = requests.get(
                    MUSE_API,
                    params={"category": category, "page": page},
                    timeout=15,
                )
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                logger.error(f"The Muse fetch error [{category} p{page}]: {e}")
                break

            results = data.get("results", [])
            if not results:
                break

            for item in results:
                item_id = str(item.get("id", ""))
                if item_id in seen_ids:
                    continue

                if not _is_remote(item):
                    continue

                title = item.get("name", "")
                description = _strip_html(item.get("contents", ""))

                if not is_social_work_job(title, description):
                    continue

                seen_ids.add(item_id)
                company = item.get("company", {}).get("name", "Unknown Company")
                job_url = item.get("refs", {}).get("landing_page", "")

                jobs.append({
                    "id": f"themuse:{item_id}",
                    "title": title,
                    "company": company,
                    "location": "Remote",
                    "url": job_url,
                    "description": description[:1500],
                    "salary": None,
                    "posted_at": item.get("publication_date"),
                    "source": "The Muse",
                    "tags": [t.get("name", "") for t in item.get("categories", [])],
                })

            total_pages = data.get("page_count", 1)
            if page >= total_pages - 1:
                break
            page += 1

    logger.info(f"The Muse: {len(jobs)} social work jobs found")
    return jobs
