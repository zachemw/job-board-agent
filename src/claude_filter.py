"""
Claude API integration for filtering and summarizing job listings.

Sends jobs in batches to Claude, which:
1. Filters out non-genuine remote social work positions
2. Scores relevance (1–5) for a licensed social worker job-seeker
3. Writes a 1–2 sentence summary highlighting key info (requirements, salary, benefits)

Returns only jobs with relevance score >= MIN_SCORE, enriched with Claude's summary.
"""

import json
import logging
import re
import os
from anthropic import Anthropic

logger = logging.getLogger(__name__)

BATCH_SIZE = 20
MIN_SCORE = 3  # Filter out low-relevance results

client = Anthropic()  # uses ANTHROPIC_API_KEY env var automatically

SYSTEM_PROMPT = """You are a job search assistant helping a licensed social worker find remote positions.
Your task: evaluate job listings and return only genuinely relevant remote social work opportunities.

## What counts as relevant
A job MUST meet ALL of these:
1. **Direct practice role** — the person in this role does clinical work, counseling, case management, therapy, crisis intervention, or direct client services. NOT management, marketing, operations, IT, recruiting, finance, or executive leadership *at* a health org.
2. **Genuine remote** — telehealth, 100% WFH, or fully distributed. Hybrid (some days in office) is OK but note it. Exclude if the listing requires relocation or has a physical office requirement with no remote option.
3. **Social work / counseling field** — requires or strongly prefers credentials like MSW, LCSW, LMSW, LSW, BSW, LPC, LCPC, CADC, LADC, CADAC, SUDP, or similar; OR the role title is clearly a social work / counseling position.

## Scoring (1–5)
- **5 — Top Match**: Substance abuse, drug & alcohol, addiction recovery, or SUD counseling role that is remote. These are the highest priority.
- **4 — Strong Match**: Other direct clinical social work, mental health therapy/counseling, crisis services, or case management — remote and credentialed.
- **3 — Good Match**: Adjacent roles clearly in the SW field: peer support specialist, recovery coach, social work intern/trainee (if remote), patient care coordinator with SW focus.
- **2 — Weak**: Loosely related or uncertain fit — don't keep.
- **1 — Not relevant**: Clearly not a social work practice role — don't keep.

## Hard excludes (set keep=false immediately)
- VP, Director, C-suite, or Senior Manager titles — even at social service orgs
- Marketing, Sales, Recruiting, HR, Finance, Legal, IT, Engineering, DevOps, Product
- Operations roles without direct client contact
- Administrative assistant / coordinator with no clinical duties
- Research-only roles with no practice component
- Jobs requiring in-person work with no remote option stated

## License extraction
Scan the description carefully for any license or credential requirements. Extract them as short strings:
- Specific licenses: "LCSW", "CADC", "LPC", "LMSW", etc.
- State-specific: "CA license required", "Active NY license", "Licensed in Texas"
- General: "Active state license" if no specific type mentioned
- If no license mentioned: return []

## Output format
Return ONLY a JSON array. Each element:
{
  "id": "<exact id from input>",
  "score": <1-5>,
  "keep": <true if score >= 3>,
  "summary": "<1-2 sentences: lead with the most compelling detail — caseload type, pay, schedule, key requirement>",
  "licenses": ["<license string>", ...]
}

No markdown, no explanation, no other text — just the JSON array."""


def _make_user_prompt(batch: list[dict]) -> str:
    items = []
    for job in batch:
        items.append({
            "id": job["id"],
            "title": job["title"],
            "company": job["company"],
            "location": job["location"],
            "salary": job.get("salary"),
            "description": job.get("description", "")[:800],  # trim for token budget
            "tags": job.get("tags", []),
            "source": job["source"],
        })
    return f"Evaluate these {len(items)} job listings:\n\n{json.dumps(items, indent=2)}"


def filter_and_summarize(jobs: list[dict]) -> list[dict]:
    """
    Runs jobs through Claude in batches. Returns filtered, enriched job list.
    Each returned job has an added 'summary' and 'score' field.
    """
    if not jobs:
        return []

    enriched: list[dict] = []
    job_index = {job["id"]: job for job in jobs}

    for i in range(0, len(jobs), BATCH_SIZE):
        batch = jobs[i : i + BATCH_SIZE]
        logger.info(f"Claude filtering batch {i // BATCH_SIZE + 1} ({len(batch)} jobs)...")

        try:
            response = client.messages.create(
                model="claude-opus-4-7",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": _make_user_prompt(batch)}],
            )
            raw = response.content[0].text.strip()

            # Claude might wrap in markdown code blocks — strip them
            if raw.startswith("```"):
                raw = re.sub(r"^```(?:json)?\n?", "", raw)
                raw = re.sub(r"\n?```$", "", raw)

            results = json.loads(raw)
        except json.JSONDecodeError as e:
            logger.error(f"Claude returned invalid JSON: {e}")
            continue
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            continue

        for result in results:
            if not result.get("keep", False):
                continue
            job_id = result.get("id")
            if job_id not in job_index:
                continue

            enriched_job = {**job_index[job_id]}
            enriched_job["summary"] = result.get("summary", "")
            enriched_job["score"] = result.get("score", 3)
            enriched_job["licenses"] = result.get("licenses", [])
            enriched.append(enriched_job)

    # Sort by score descending so best matches appear first in email
    enriched.sort(key=lambda j: j.get("score", 0), reverse=True)

    logger.info(f"Claude kept {len(enriched)} of {len(jobs)} jobs after filtering")
    return enriched
