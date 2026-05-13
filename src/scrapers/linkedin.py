"""
LinkedIn job scraper via their Jobs RSS feeds.
LinkedIn provides public RSS feeds for job searches — no API key required.
Note: These feeds may be rate-limited or blocked. If you need reliable LinkedIn
access, consider the LinkedIn Jobs API (requires company partnership application).
"""

import feedparser
import logging
import re
from email.utils import parsedate_to_datetime
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

LINKEDIN_RSS_BASE = "https://www.linkedin.com/jobs/search"

SOCIAL_WORK_QUERIES = [
    {"keywords": "social worker", "f_WT": "2"},         # f_WT=2 is remote
    {"keywords": "LCSW remote", "f_WT": "2"},
    {"keywords": "LMSW remote", "f_WT": "2"},
    {"keywords": "clinical social worker", "f_WT": "2"},
    {"keywords": "case manager MSW", "f_WT": "2"},
    {"keywords": "behavioral health counselor remote", "f_WT": "2"},
]


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

    for params in SOCIAL_WORK_QUERIES:
        # LinkedIn exposes an RSS feed for job searches
        rss_url = f"https://www.linkedin.com/jobs/search?{urlencode(params)}&trk=public_jobs_jobs-search-bar_search-submit&position=1&pageNum=0"
        # Use the RSS variant
        feed_url = f"https://www.linkedin.com/jobs/search/?{urlencode({**params, 'format': 'json'})}"

        # LinkedIn's actual RSS endpoint
        rss_feed_url = (
            f"https://www.linkedin.com/jobs/search/?keywords={params['keywords'].replace(' ', '%20')}"
            f"&f_WT=2&f_JT=F&sortBy=DD"
        )

        try:
            feed = feedparser.parse(rss_feed_url)
            if not feed.entries:
                logger.debug(f"LinkedIn RSS returned no entries for: {params['keywords']}")
                continue

            for entry in feed.entries:
                job_url = entry.get("link", "")
                if not job_url or job_url in seen_urls:
                    continue
                seen_urls.add(job_url)

                description = _strip_html(entry.get("summary", ""))
                jobs.append({
                    "id": f"linkedin:{job_url}",
                    "title": entry.get("title", "Unknown Title"),
                    "company": entry.get("author", "Unknown Company"),
                    "location": "Remote",
                    "url": job_url,
                    "description": description[:1500],
                    "salary": None,
                    "posted_at": _parse_posted_at(entry),
                    "source": "LinkedIn",
                    "tags": [],
                })

        except Exception as e:
            logger.error(f"LinkedIn RSS error [{params['keywords']}]: {e}")

    logger.info(f"LinkedIn: {len(jobs)} jobs found")
    return jobs
