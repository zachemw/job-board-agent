"""
Deduplication logic for jobs collected across multiple boards.

Two jobs are considered duplicates if:
1. They share the exact same URL (after normalizing tracking params), OR
2. Their title+company combination is highly similar (≥0.85 ratio),
   suggesting the same role posted on multiple boards.
"""

import re
from difflib import SequenceMatcher
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse


# URL query params that are tracking noise and should be stripped before comparison
_TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term",
    "trk", "src", "ref", "referer", "source", "via", "campaign",
}


def _normalize_url(url: str) -> str:
    try:
        parsed = urlparse(url)
        qs = parse_qs(parsed.query, keep_blank_values=False)
        clean_qs = {k: v for k, v in qs.items() if k.lower() not in _TRACKING_PARAMS}
        clean_query = urlencode(clean_qs, doseq=True)
        return urlunparse(parsed._replace(query=clean_query, fragment=""))
    except Exception:
        return url


def _normalize_text(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace for fuzzy comparison."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def deduplicate(jobs: list[dict]) -> list[dict]:
    """
    Remove duplicate jobs. Keeps the first occurrence when a duplicate is found,
    preferring the source with the most complete data (description, salary).
    Returns deduplicated list.
    """
    seen_urls: set[str] = set()
    # Each entry: (normalized_title, normalized_company)
    seen_title_company: list[tuple[str, str]] = []
    result: list[dict] = []

    # Sort so jobs with more data come first (salary > no salary, longer description wins)
    def completeness_score(job: dict) -> int:
        score = 0
        if job.get("salary"):
            score += 2
        if job.get("description") and len(job["description"]) > 200:
            score += 1
        if job.get("posted_at"):
            score += 1
        return score

    sorted_jobs = sorted(jobs, key=completeness_score, reverse=True)

    for job in sorted_jobs:
        # URL-based dedup
        norm_url = _normalize_url(job.get("url", ""))
        if norm_url and norm_url in seen_urls:
            continue

        # Title+company fuzzy dedup
        norm_title = _normalize_text(job.get("title", ""))
        norm_company = _normalize_text(job.get("company", ""))

        is_dup = False
        for seen_title, seen_company in seen_title_company:
            title_sim = _similarity(norm_title, seen_title)
            company_sim = _similarity(norm_company, seen_company)
            # Same company + very similar title → duplicate
            if company_sim >= 0.80 and title_sim >= 0.85:
                is_dup = True
                break

        if is_dup:
            continue

        if norm_url:
            seen_urls.add(norm_url)
        seen_title_company.append((norm_title, norm_company))
        result.append(job)

    return result
