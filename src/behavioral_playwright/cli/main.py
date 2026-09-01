"""Behavioral Playwright Command Line Interface (CLI)."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import List, Optional

import behavioral_playwright
from behavioral_playwright import BP
from behavioral_playwright.storage.exporters import DataStorageManager


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bp",
        description="Behavioral Playwright - Resilient & Stealth Automation Framework CLI",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"behavioral-playwright {behavioral_playwright.__version__}",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # 1. Scrape command
    scrape_p = subparsers.add_parser("scrape", help="Scrape a URL and extract links/text")
    scrape_p.add_argument("url", help="Target URL to scrape")
    scrape_p.add_argument("--output", "-o", help="Output file path (e.g., out.json, out.csv)")
    scrape_p.add_argument("--target", default="links", choices=["links", "articles"], help="Extraction target")

    # 2. Crawl command
    crawl_p = subparsers.add_parser("crawl", help="Recursively crawl a URL")
    crawl_p.add_argument("url", help="Start URL to crawl")
    crawl_p.add_argument("--max-pages", "-m", type=int, default=5, help="Max pages to crawl")
    crawl_p.add_argument("--depth", "-d", type=int, default=2, help="Crawl depth")
    crawl_p.add_argument("--output", "-o", help="Output file path (e.g. data.ndjson)")

    # 3. Matrix command
    subparsers.add_parser("matrix", help="Display provider availability matrix")

    # 4. QA Report command
    qa_p = subparsers.add_parser("qa-report", help="Generate QA compliance summary from metrics DB")
    qa_p.add_argument("--db", default="bp_metrics.db", help="Path to metrics SQLite database")

    return parser


async def run_scrape(url: str, output: Optional[str] = None, target: str = "links") -> int:
    async with BP() as bp:
        await bp.goto(url)
        records = await bp.extract(target=target)
        raw = [r.to_dict() if hasattr(r, "to_dict") else vars(r) for r in records]
        
        if output:
            saved = DataStorageManager().export(raw, output)
            print(f"[+] Saved {len(raw)} records to {saved}")
        else:
            print(json.dumps(raw, indent=2, default=str))
    return 0


async def run_crawl(url: str, max_pages: int = 5, depth: int = 2, output: Optional[str] = None) -> int:
    async with BP() as bp:
        records = await bp.crawl(url, max_pages=max_pages)
        raw = [r.to_dict() if hasattr(r, "to_dict") else vars(r) for r in records]
        
        if output:
            saved = DataStorageManager().export(raw, output)
            print(f"[+] Crawled and saved {len(raw)} records to {saved}")
        else:
            print(json.dumps(raw, indent=2, default=str))
    return 0


def run_matrix() -> int:
    bp = BP()
    matrix = bp.providers.matrix()
    print("\n=======================================================")
    print("      BEHAVIORAL PLAYWRIGHT: PROVIDER MATRIX          ")
    print("=======================================================")
    print(f"{'Provider ID':<28} | {'Type':<10} | {'Status':<12} | {'Installed':<10}")
    print("-" * 65)
    for p_id, info in matrix.items():
        inst = "YES" if info.installed else "NO"
        stat = "AVAILABLE" if info.installed else "GATED"
        print(f"{p_id:<28} | {info.provider:<10} | {stat:<12} | {inst:<10}")
    print("-" * 65 + "\n")
    return 0


def run_qa_report(db_path: str) -> int:
    bp = BP()
    report = bp.observability.generate_qa_report(db_path=db_path)
    if isinstance(report, dict):
        print(json.dumps(report, indent=2))
    else:
        print(report)
    return 0


def main(args: Optional[List[str]] = None) -> int:
    parser = build_parser()
    parsed = parser.parse_args(args)

    if not parsed.command:
        parser.print_help()
        return 0

    if parsed.command == "matrix":
        return run_matrix()
    elif parsed.command == "qa-report":
        return run_qa_report(parsed.db)
    elif parsed.command == "scrape":
        return asyncio.run(run_scrape(parsed.url, parsed.output, parsed.target))
    elif parsed.command == "crawl":
        return asyncio.run(run_crawl(parsed.url, parsed.max_pages, parsed.depth, parsed.output))
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
