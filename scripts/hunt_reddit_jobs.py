"""Reddit Job Hunter CLI Script.

Scans technical hiring subreddits (r/forhire, r/webscraping, r/freelance_forhire)
for live paying scraping/automation/Python jobs and generates winning technical pitches.

Usage:
    python scripts/hunt_reddit_jobs.py
    python scripts/hunt_reddit_jobs.py --limit 15
"""

import asyncio
import sys
from behavioral_playwright.integrations.reddit import RedditAutomationClient

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


async def main() -> None:
    limit = 25
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        limit = int(sys.argv[1])

    print("=" * 70)
    print("[+] REDDIT HIGH-VALUE LEAD & CLIENT HUNTER (Behavioral Playwright)")
    print("=" * 70)
    print(f"[*] Scanning r/forhire, r/webscraping, r/freelance_forhire (limit: {limit})...\n")


    client = RedditAutomationClient()
    leads = await client.mine_hiring_leads(limit_per_sub=limit)

    if not leads:
        print("[-] No new matching client posts found at this moment.")
        print("[*] Tip: Re-run in a few hours or adjust intent keywords.")
        return

    print(f"[+] Found {len(leads)} potential client leads!\n")

    for idx, lead in enumerate(leads[:8], 1):
        print(f"[{idx}] {lead.title}")
        print(f"    Subreddit: r/{lead.subreddit} | Author: u/{lead.author or 'anonymous'}")
        if lead.budget_hint:
            print(f"    [$] Budget Hint: {lead.budget_hint}")
        print(f"    Keywords: {', '.join(lead.matched_keywords)}")
        print(f"    URL: {lead.url}")

        audit = client.analyze_lead_and_generate_pitch(lead)
        print(f"\n    [*] Winning Pitch Proposal Draft:")
        for line in audit.pitch_draft.split("\n"):
            print(f"       {line}")
        print("\n" + "-" * 70 + "\n")

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
