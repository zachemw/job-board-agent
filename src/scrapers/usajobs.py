"""
USA Jobs scraper — free REST API, requires a free API key.
Great source for government social work positions (many are remote-eligible).
Register at: https://developer.usajobs.gov/
Set USAJOBS_API_KEY and USAJOBS_USER_AGENT in your .env file.
"""

import logging
import os
import re
import requests

logger = logging.getLogger(__name__)

USAJOBS_API = "https://data.usajobs.gov/api/search"

SOCIAL_WORK_SERIES = [
    "0185",  # Social Work series
    "0187",  # Social Services series
    "0101",  # Social Science series
    "0186",  # Social Services Aid/Assistant
]


def fetch() -> list[dict]:
    api_key = os.getenv("USAJOBS_API_KEY", "")
    user_agent = os.getenv("USAJOBS_USER_AGENT", "")

    if not api_key or not user_agent:
        logger.info("USA Jobs: skipping — USAJOBS_API_KEY or USAJOBS_USER_AGENT not set")
        return []

    jobs = []
    seen_ids = set()

    queries = [
        {"Keyword": "social worker", "RemoteIndicator": True},
        {"Keyword": "LCSW remote", "RemoteIndicator": True},
        {"Keyword": "case manager telehealth", "RemoteIndicator": True},
    ]

    headers = {
        "Authorization-Key": api_key,
        "User-Agent": user_agent,
        "Host": "data.usajobs.gov",
    }

    for query_params in queries:
        params = {**query_params, "ResultsPerPage": 25}
        try:
            resp = requests.get(USAJOBS_API, headers=headers, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error(f"USA Jobs fetch error: {e}")
            continue

        items = data.get("SearchResult", {}).get("SearchResultItems", [])
        for item in items:
            matched = item.get("MatchedObjectDescriptor", {})
            job_id = matched.get("PositionID", "")

            if job_id in seen_ids:
                continue
            seen_ids.add(job_id)

            # Check telecommute eligibility
            telework = matched.get("TeleworkSchedule", [])
            remote_ok = any(
                "full" in t.lower() or "100" in t for t in telework
            ) if telework else False
            if not remote_ok:
                # Still include if keyword search returned it
                pass

            locations = [loc.get("LocationName", "") for loc in matched.get("PositionLocation", [])]

            salary_min = matched.get("PositionRemuneration", [{}])[0].get("MinimumRange", "")
            salary_max = matched.get("PositionRemuneration", [{}])[0].get("MaximumRange", "")
            salary = None
            if salary_min and salary_max:
                salary = f"${float(salary_min):,.0f}–${float(salary_max):,.0f}/yr"

            description = matched.get("UserArea", {}).get("Details", {}).get("JobSummary", "")

            jobs.append({
                "id": f"usajobs:{job_id}",
                "title": matched.get("PositionTitle", ""),
                "company": matched.get("OrganizationName", "Federal Government"),
                "location": ", ".join(locations) or "Remote",
                "url": matched.get("ApplyURI", [""])[0],
                "description": description[:1500],
                "salary": salary,
                "posted_at": matched.get("PublicationStartDate"),
                "source": "USA Jobs",
                "tags": ["government", "federal"],
            })

    logger.info(f"USA Jobs: {len(jobs)} jobs found")
    return jobs
