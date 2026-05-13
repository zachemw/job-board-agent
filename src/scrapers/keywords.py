"""
Shared pre-filter for social work job relevance.

Strategy: focus primarily on the job TITLE. Fall back to description only
for specific credential abbreviations. Explicitly exclude titles that signal
non-clinical roles (VP, Director, Marketing, Engineering, etc.) even if the
company is in the health/social services space.
"""

import re

# Matches titles that are clearly social work / counseling roles.
# Specific enough that false positives (Clinical Marketing Director, etc.) won't sneak through.
TITLE_MATCH = re.compile(
    r"\b("
    r"social.?work(er)?|"
    r"lcsw|lmsw|lsw|msw|cadc|ladc|cadac|sudp|lcpc|"
    r"licensed.?clinical.?(social|mental|counselor)|"
    r"licensed.?social.?work(er)?|"
    r"licensed.?professional.?counselor|"
    r"case.?manag(er|ment)|"
    r"substance.?abuse.?(counselor|therapist|specialist|worker)|"
    r"drug.?.?alcohol.?(counselor|therapist|specialist)|"
    r"addiction.?(counselor|therapist|specialist|recovery)|"
    r"mental.?health.?(counselor|therapist|clinician|specialist|worker)|"
    r"behavioral.?health.?(counselor|therapist|clinician|specialist|worker)|"
    r"clinical.?social.?work(er)?|"
    r"psychiatric.?social.?work(er)?|"
    r"medical.?social.?work(er)?|"
    r"recovery.?(coach|counselor|specialist)|"
    r"crisis.?(counselor|clinician|worker|specialist)|"
    r"therapist|"
    r"psychotherapist|"
    r"counselor"
    r")\b",
    re.IGNORECASE,
)

# If title doesn't match above, only include if description has a specific credential.
# Broader terms like "clinical", "behavioral health", "mental health" alone are NOT enough.
CREDENTIAL_IN_DESCRIPTION = re.compile(
    r"\b(lcsw|lmsw|lsw|cadc|ladc|cadac|sudp|lcpc|msw|bsw|"
    r"social.?work(er)?|substance.?abuse.?counselor|"
    r"addiction.?counselor|licensed.?counselor|licensed.?therapist)\b",
    re.IGNORECASE,
)

# Titles that indicate non-clinical roles — exclude even if description has SW keywords.
EXCLUDE_TITLE = re.compile(
    r"\b("
    r"vp\b|vice.?president|"
    r"chief\b|ceo|cto|coo|cmo|cfo|"
    r"director\b|"                       # Clinical Director is borderline but usually management
    r"marketing|"
    r"software|engineer(ing)?|devops|sre\b|"
    r"product.?manager|product.?owner|"
    r"data.?scien|machine.?learn|"
    r"copywriter|copy.?writer|"
    r"recruiter|talent.?acqui|"
    r"account.?exec|sales\b|"
    r"attorney|lawyer|paralegal|"
    r"financial.?analyst|accountant|"
    r"graphic.?design|ux.?design|ui.?design|"
    r"operations.?manager|operations.?director|"
    r"business.?develop|partnerships\b"
    r")\b",
    re.IGNORECASE,
)


def is_social_work_job(title: str, description: str = "", tags: list | None = None) -> bool:
    """
    Returns True if the job is plausibly a social work / counseling position.
    Claude does the final precise filtering; this just culls obvious non-matches
    so we don't waste Claude tokens on DevOps and Marketing Director listings.
    """
    tags = tags or []

    # Hard exclude: clearly non-clinical title
    if EXCLUDE_TITLE.search(title):
        return False

    # Strong include: title has a specific social work role term
    if TITLE_MATCH.search(title):
        return True

    # Soft include: description/tags contain specific credential abbreviations
    searchable = f"{description} {' '.join(tags)}"
    if CREDENTIAL_IN_DESCRIPTION.search(searchable):
        return True

    return False
