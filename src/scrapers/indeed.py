"""
Indeed scraper via RSS feed — no API key required.
Searches for remote social work jobs using Indeed's public RSS endpoint.
"""

import feedparser
import logging
import re
from datetime import datetime
from email.utils import parsedate_to_datetime

logger = logging.getLogger(__name__)

SOCIAL_WORK_QUERIES = [
    "social worker",
    "LCSW",
    "LMSW",
    "case manager social work",
    "clinical social worker telehealth",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; job-digest-bot/1.0)",
}


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text or "").strip()


def _parse_posted_at(entry) -> str | None:
    try:
        return parsedate_to_datetime(entry.get("published", "")).isoformat()
    except Exception:
        return None


def fetch() -> list[dict]:
    import requests

    jobs = []
    seen_urls = set()

    for query in SOCIAL_WORK_QUERIES:
        # Indeed's current RSS format — fetch raw and pass to feedparser
        encoded = query.replace(" ", "+")
        url = f"https://www.indeed.com/rss?q={encoded}&l=remote"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            feed = feedparser.parse(resp.content)
            if not feed.entries:
                logger.debug(f"Indeed RSS empty for query '{query}'")
                continue

            for entry in feed.entries:
                job_url = entry.get("link", "")
                if not job_url or job_url in seen_urls:
                    continue
                seen_urls.add(job_url)

                description = _strip_html(entry.get("summary", ""))
                jobs.append({
                    "id": f"indeed:{job_url}",
                    "title": entry.get("title", "Unknown Title"),
                    "company": entry.get("source", {}).get("title", "Unknown Company"),
                    "location": "Remote",
                    "url": job_url,
                    "description": description[:1500],
                    "salary": None,
                    "posted_at": _parse_posted_at(entry),
                    "source": "Indeed",
                    "tags": [],
                })

            logger.info(f"Indeed [{query}]: {len(feed.entries)} entries")
        except Exception as e:
            logger.error(f"Indeed scraper error for query '{query}': {e}")

    return jobs
