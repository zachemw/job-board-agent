"""
Remote Social Work Job Digest — main orchestrator.

Runs all scrapers in parallel, deduplicates results, filters/summarizes
via Claude, then sends an HTML digest email via Resend.

Usage:
    python src/main.py                    # run digest
    python src/main.py --dry-run          # run without sending email
    python src/main.py --preview          # save HTML preview to preview.html
"""

import argparse
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")

# ── Scrapers ─────────────────────────────────────────────────────────────────
from scrapers import (  # noqa: E402
    indeed,
    remoteok,
    weworkremotely,
    remotive,
    arbeitnow,
    themuse,
    usajobs,
    ziprecruiter,
    linkedin,
)
from dedup import deduplicate  # noqa: E402
from claude_filter import filter_and_summarize  # noqa: E402
from email_sender import send_digest, build_html  # noqa: E402
from history import mark_seen, save_sent, count_new  # noqa: E402

SCRAPERS = {
    "Indeed": indeed.fetch,
    "RemoteOK": remoteok.fetch,
    "We Work Remotely": weworkremotely.fetch,
    "Remotive": remotive.fetch,
    "Arbeitnow": arbeitnow.fetch,
    "The Muse": themuse.fetch,
    "USA Jobs": usajobs.fetch,
    "ZipRecruiter": ziprecruiter.fetch,
    "LinkedIn": linkedin.fetch,
}


def run_scrapers() -> tuple[list[dict], dict]:
    """Run all scrapers concurrently. Returns (all_jobs, source_counts)."""
    all_jobs: list[dict] = []
    source_counts: dict = {name: 0 for name in SCRAPERS}

    with ThreadPoolExecutor(max_workers=len(SCRAPERS)) as executor:
        futures = {executor.submit(fn): name for name, fn in SCRAPERS.items()}
        for future in as_completed(futures):
            name = futures[future]
            try:
                jobs = future.result()
                source_counts[name] = len(jobs)
                all_jobs.extend(jobs)
                logger.info(f"✓ {name}: {len(jobs)} jobs")
            except Exception as e:
                logger.error(f"✗ {name} failed: {e}")

    return all_jobs, source_counts


def main():
    parser = argparse.ArgumentParser(description="Remote Social Work Job Digest")
    parser.add_argument("--dry-run", action="store_true", help="Skip sending email")
    parser.add_argument("--preview", action="store_true", help="Save HTML preview to preview.html")
    parser.add_argument("--no-claude", action="store_true", help="Skip Claude filtering (faster, raw results)")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info(f"  Remote Social Work Job Digest — {datetime.now().strftime('%Y-%m-%d')}")
    logger.info("=" * 60)

    # Validate required env vars
    missing = []
    for var in ["ANTHROPIC_API_KEY", "RESEND_API_KEY", "RECIPIENT_EMAIL"]:
        if not os.getenv(var):
            missing.append(var)
    if missing and not args.dry_run and not args.preview:
        logger.error(f"Missing required environment variables: {', '.join(missing)}")
        sys.exit(1)
    elif missing:
        logger.warning(f"Missing env vars (OK for dry-run/preview): {', '.join(missing)}")

    # Step 1: Scrape
    logger.info("\n📡 Step 1: Running scrapers...")
    all_jobs, source_counts = run_scrapers()
    logger.info(f"   Total raw jobs: {len(all_jobs)}")

    # Step 2: Deduplicate
    logger.info("\n🔍 Step 2: Deduplicating...")
    deduped = deduplicate(all_jobs)
    removed = len(all_jobs) - len(deduped)
    logger.info(f"   After dedup: {len(deduped)} jobs ({removed} duplicates removed)")

    # Step 3: Claude filtering
    if args.no_claude or not os.getenv("ANTHROPIC_API_KEY"):
        logger.info("\n🤖 Step 3: Skipping Claude filter (--no-claude or no API key)")
        filtered = deduped
    else:
        logger.info(f"\n🤖 Step 3: Claude filtering {len(deduped)} jobs...")
        filtered = filter_and_summarize(deduped)
        logger.info(f"   Claude kept: {len(filtered)} jobs")

    # Step 4: Check history — mark returning jobs and count what's new
    logger.info("\n📋 Step 4: Checking history...")
    filtered = mark_seen(filtered)
    new_count = count_new(filtered)
    returning_count = len(filtered) - new_count
    logger.info(f"   New: {new_count} | Returning (still available): {returning_count}")

    # Step 5: Send / preview
    total_scraped = len(all_jobs)

    if args.preview or args.dry_run:
        html = build_html(filtered, total_scraped, source_counts)
        out_path = Path(__file__).parent.parent / "preview.html"
        out_path.write_text(html, encoding="utf-8")
        logger.info(f"\n📄 Preview saved to: {out_path.absolute()}")

    if not args.dry_run and not args.preview:
        if new_count == 0:
            logger.info("\n⏭  Step 5: No new jobs since last send — skipping email")
        else:
            logger.info(f"\n📧 Step 5: Sending digest ({new_count} new + {returning_count} returning)...")
            success = send_digest(filtered, total_scraped, source_counts)
            if success:
                save_sent(filtered)
                logger.info("   ✅ Email sent and history updated!")
            else:
                logger.error("   ❌ Email send failed")
                sys.exit(1)
    elif args.dry_run:
        logger.info("\n⏭  Dry run — email not sent")

    logger.info("\n✅ Done.")
    logger.info(f"   Scraped: {total_scraped} | Deduped: {len(deduped)} | New: {new_count} | Returning: {returning_count}")


if __name__ == "__main__":
    main()
