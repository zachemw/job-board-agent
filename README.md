# Remote Social Work Job Digest

An automated agent that scrapes remote social work jobs from multiple job boards every weekday morning, filters them using Claude AI, and emails a curated HTML digest. Tracks previously sent jobs to avoid duplicate sends and badges returning listings as "↩ Still Available."

---

## How It Works

```
[GitHub Actions — Mon–Fri 8am ET]
           ↓
   [9 Job Board Scrapers]        ← runs all in parallel
           ↓
   [Deduplication]               ← removes cross-board duplicates
           ↓
   [Claude API Filter]           ← keeps only genuine remote SW jobs,
                                    scores relevance, extracts license
                                    requirements, writes summaries
           ↓
   [History Check]               ← compares against sent_jobs.json;
                                    skips email if nothing is new
           ↓
   [Resend Email]                ← sends HTML digest to recipient
           ↓
   [Commit sent_jobs.json]       ← auto-committed back to repo
```

---

## Job Sources

| Source | Type | API Key Required |
|--------|------|-----------------|
| RemoteOK | Free JSON API | No |
| We Work Remotely | Free RSS | No |
| Remotive | Free REST API | No |
| Arbeitnow | Free REST API | No |
| Indeed | RSS | No |
| LinkedIn | RSS | No |
| The Muse | Free REST API | No |
| USA Jobs | REST API | Yes (free) |
| ZipRecruiter | Partner API | Yes (free) |

USA Jobs and ZipRecruiter are optional — the digest runs fine without them.

---

## Prerequisites

- Python 3.11+
- A free [Resend](https://resend.com) account (for sending email)
- An [Anthropic API key](https://console.anthropic.com) with credits (costs ~$0.01–0.03 per daily run)
- A GitHub account (for automated scheduling)

---

## Project Structure

```
job-board-agent/
├── src/
│   ├── main.py                  # Orchestrator — run this
│   ├── dedup.py                 # Cross-board deduplication
│   ├── claude_filter.py         # Claude API filtering & summarization
│   ├── email_sender.py          # HTML digest builder + Resend sender
│   ├── history.py               # Tracks sent job IDs (sent_jobs.json)
│   └── scrapers/
│       ├── keywords.py          # Shared keyword filter logic
│       ├── remoteok.py
│       ├── weworkremotely.py
│       ├── remotive.py
│       ├── arbeitnow.py
│       ├── indeed.py
│       ├── linkedin.py
│       ├── themuse.py
│       ├── usajobs.py           # Optional — needs USAJOBS_API_KEY
│       └── ziprecruiter.py      # Optional — needs ZIPRECRUITER_API_KEY
├── .github/
│   └── workflows/
│       └── daily-digest.yml     # GitHub Actions cron schedule
├── sent_jobs.json               # Persistent history of sent job IDs
├── .env.example                 # Template for environment variables
├── .env                         # Your actual secrets — never commit this
├── .gitignore
└── requirements.txt
```

---

## Setup From Scratch

### 1. Clone the repo

```bash
git clone https://github.com/zachemw/job-board-agent.git
cd job-board-agent
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Get your API keys

**Anthropic (required)**
1. Go to [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys)
2. Create a new key and copy it
3. Add a few dollars of credit at [console.anthropic.com/settings/billing](https://console.anthropic.com/settings/billing) — each run costs ~$0.01–0.03

**Resend (required)**
1. Sign up at [resend.com](https://resend.com) — free tier is plenty
2. Go to **API Keys** → Create API Key → copy it
3. On the free tier, the sender address must be `onboarding@resend.dev` unless you verify your own domain

**USA Jobs (optional)**
1. Register at [developer.usajobs.gov](https://developer.usajobs.gov/)
2. You'll receive an API key by email
3. Use your email address as `USAJOBS_USER_AGENT`

**ZipRecruiter (optional)**
1. Apply at [ziprecruiter.com/jobs-api](https://www.ziprecruiter.com/jobs-api/docs)
2. Copy the API key once approved

### 4. Create your `.env` file

```bash
cp .env.example .env
```

Edit `.env` and fill in your values:

```env
# Required
ANTHROPIC_API_KEY=sk-ant-...
RESEND_API_KEY=re_...
RECIPIENT_EMAIL=recipient@email.com
SENDER_EMAIL=Remote Social Work Digest <onboarding@resend.dev>

# Optional — adds more job sources if set
USAJOBS_API_KEY=
USAJOBS_USER_AGENT=your-email@example.com
ZIPRECRUITER_API_KEY=
```

> **Never commit `.env`** — it's already in `.gitignore`.

### 5. Test locally

```bash
cd src

# Fast test — skips Claude and email, just checks scrapers work
python main.py --dry-run --no-claude

# Full test with Claude filtering, no email sent, saves preview.html
python main.py --dry-run

# Full live run — sends actual email
python main.py
```

---

## Deploy to GitHub Actions

### 1. Create a private GitHub repo

```bash
gh repo create job-board-agent --private --source=. --remote=origin --push
```

Or create it manually on GitHub and push:

```bash
git remote add origin https://github.com/YOUR_USERNAME/job-board-agent.git
git push -u origin main
```

### 2. Add secrets to GitHub

Go to your repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Add each of these:

| Secret name | Value |
|-------------|-------|
| `ANTHROPIC_API_KEY` | Your Anthropic key |
| `RESEND_API_KEY` | Your Resend key |
| `RECIPIENT_EMAIL` | Recipient's email address |
| `SENDER_EMAIL` | e.g. `Remote Social Work Digest <onboarding@resend.dev>` |
| `USAJOBS_API_KEY` | *(optional)* |
| `USAJOBS_USER_AGENT` | *(optional)* |
| `ZIPRECRUITER_API_KEY` | *(optional)* |

Or add them all at once using the GitHub CLI:

```bash
gh secret set ANTHROPIC_API_KEY --body "sk-ant-..."
gh secret set RESEND_API_KEY --body "re_..."
gh secret set RECIPIENT_EMAIL --body "recipient@email.com"
gh secret set SENDER_EMAIL --body "Remote Social Work Digest <onboarding@resend.dev>"
```

### 3. Trigger a manual test run

In GitHub → **Actions** → **Remote Social Work Job Digest** → **Run workflow**

Or via CLI:

```bash
gh workflow run daily-digest.yml
gh run list --limit 1   # check status
```

The workflow runs automatically **Monday–Friday at 8:00 AM Eastern** from that point on.

---

## How the History System Works

`sent_jobs.json` at the repo root tracks every job ID that has been emailed. Each morning:

- Jobs **not** in the history → treated as new (✨ New badge in email)
- Jobs **already** in the history → treated as returning (↩ Still Available badge)
- If **zero** new jobs exist → email is skipped entirely
- If **any** new jobs exist → email is sent with all jobs (new first, returning below), and the new IDs are added to history

After a successful send, the workflow automatically commits the updated `sent_jobs.json` back to the repo so the next run remembers what was sent.

**To reset history** (e.g. if you change recipients and want them to see all current listings fresh):

```bash
echo '{"sent": {}}' > sent_jobs.json
git add sent_jobs.json && git commit -m "chore: reset job history" && git push
```

---

## Changing the Schedule

Edit `.github/workflows/daily-digest.yml`:

```yaml
on:
  schedule:
    - cron: "0 13 * * 1-5"   # Mon–Fri 13:00 UTC = 8:00 AM ET
```

Cron format: `minute hour day-of-month month day-of-week`

Common times (all ET → UTC offset is +5 in winter, +4 in summer):
- 7:00 AM ET → `0 12 * * 1-5`
- 8:00 AM ET → `0 13 * * 1-5`
- 9:00 AM ET → `0 14 * * 1-5`

---

## Changing the Recipient Email

Update the `RECIPIENT_EMAIL` secret in GitHub:

```bash
gh secret set RECIPIENT_EMAIL --body "newemail@example.com"
```

Then reset the history so they see all current listings as new:

```bash
echo '{"sent": {}}' > sent_jobs.json
git add sent_jobs.json && git commit -m "chore: reset history for new recipient" && git push
```

---

## Adjusting What Jobs Get Through

**Keyword pre-filter** (`src/scrapers/keywords.py`):
Controls which jobs are even sent to Claude. Edit `TITLE_MATCH` to add role terms, or `EXCLUDE_TITLE` to block more non-clinical titles. This runs before Claude to save API costs.

**Claude scoring** (`src/claude_filter.py`):
Edit `SYSTEM_PROMPT` to change priorities. Currently:
- Score 5 (Top Match): Substance abuse / SUD / drug & alcohol roles
- Score 4 (Strong Match): Clinical social work, mental health therapy, crisis services
- Score 3 (Good Match): Adjacent roles — peer support, recovery coach, etc.
- Score < 3: Filtered out

Change `MIN_SCORE` at the top of the file to raise or lower the bar.

---

## Costs

| Service | Cost |
|---------|------|
| GitHub Actions | Free (public & private repos get 2,000 min/month free) |
| Resend | Free up to 3,000 emails/month |
| Anthropic API | ~$0.01–0.03 per daily run (~$0.25–0.65/month) |
| USA Jobs API | Free |
| ZipRecruiter API | Free |

Total: **essentially free** aside from a few cents/month in Claude API usage.
