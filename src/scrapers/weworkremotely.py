"""
We Work Remotely scraper via RSS feeds — no auth required.
Covers multiple category feeds and filters for social work relevance.
"""

import feedparser
import logging
import re
from email.utils import parsedate_to_datetime

from .keywords import is_social_work_job

logger = logging.getLogger(__name__)

# WWR RSS feeds by category — all potentially relevant ones
WWR_FEEDS = {
    "All Other Remote Jobs": "https://weworkremotely.com/categories/remote-other-jobs.rss",
    "Customer Support": "https://weworkremotely.com/categories/remote-customer-support-jobs.rss",
    "All Remote Jobs": "https://weworkremotely.com/remote-jobs.rss",
}


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text or "").strip()


def _parse_posted_at(entry) -> str | None:
    try:
        return parsedate_to_datetime(entry.get("published", "")).isoformat()
    except Exception:
        return None


def fetch() -> list[dict]:
    jobs = []
    seen_urls = set()

    for category, feed_url in WWR_FEEDS.items():
        try:
            feed = feedparser.parse(feed_url)
            if feed.bozo and not feed.entries:
                logger.warning(f"WWR feed failed [{category}]: {feed.bozo_exception}")
                continue

            for entry in feed.entries:
                job_url = entry.get("link", "")
                if not job_url or job_url in seen_urls:
                    continue

                title = entry.get("title", "")
                description = _strip_html(entry.get("summary", ""))

                if not is_social_work_job(title, description):
                    continue

                seen_urls.add(job_url)

                # WWR title format is often "Company: Job Title"
                company = "Unknown Company"
                if ": " in title:
                    parts = title.split(": ", 1)
                    company = parts[0].strip()
                    title = parts[1].strip()

                jobs.append({
                    "id": f"wwr:{job_url}",
                    "title": title,
                    "company": company,
                    "location": "Remote",
                    "url": job_url,
                    "description": description[:1500],
                    "salary": None,
                    "posted_at": _parse_posted_at(entry),
                    "source": "We Work Remotely",
                    "tags": [],
                })

            logger.info(f"WWR [{category}]: {len(feed.entries)} entries parsed")
        except Exception as e:
            logger.error(f"WWR scraper error [{category}]: {e}")

    logger.info(f"WWR: {len(jobs)} social work jobs found")
    return jobs
