"""Behavioral Playwright Command Line Interface (CLI)."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any, List, Optional

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
    parser.add_argument(
        "--api-key",
        help="Shared API key (or set BP_API_KEY environment variable)",
    )
    parser.add_argument(
        "--token",
        help="Shared Bearer token (or set BP_BEARER_TOKEN environment variable)",
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

    # 5. MCP Server command
    subparsers.add_parser("mcp-server", help="Launch standard JSON-RPC 2.0 stdio MCP server")

    # 6. MCP Config command
    cfg_p = subparsers.add_parser("mcp-config", help="Generate Claude Desktop JSON configuration")
    cfg_p.add_argument("--python-path", default="python", help="Python binary path to use in config")

    # 7. Extract-meta command (Zero-latency Next.js / Nuxt hydration & JSON-LD metadata extractor)
    meta_p = subparsers.add_parser("extract-meta", help="Extract Next.js / Nuxt hydration & JSON-LD metadata zero-latency")
    meta_p.add_argument("url", help="Target URL to inspect")
    meta_p.add_argument("--output", "-o", help="Output file path (e.g. meta.json)")

    # 8. Mine-paa command (Recursively mine Google People Also Ask tree)
    paa_p = subparsers.add_parser("mine-paa", help="Recursively mine Google People Also Ask tree")
    paa_p.add_argument("query", help="Seed search query")
    paa_p.add_argument("--depth", "-d", type=int, default=2, help="PAA expansion depth (1 to 5)")
    paa_p.add_argument("--output", "-o", help="Output file path (e.g. paa.json)")

    # 9. Check-overlap command (Check search intent cannibalization Jaccard Overlap)
    overlap_p = subparsers.add_parser("check-overlap", help="Check search intent cannibalization (Jaccard Overlap)")
    overlap_p.add_argument("query_a", help="First query")
    overlap_p.add_argument("query_b", help="Second query")
    overlap_p.add_argument("--threshold", "-t", type=float, default=0.40, help="Jaccard merge threshold (default 0.40)")
    overlap_p.add_argument("--urls-a", nargs="*", default=None, help="Explicit URLs for query A")
    overlap_p.add_argument("--urls-b", nargs="*", default=None, help="Explicit URLs for query B")
    overlap_p.add_argument("--output", "-o", help="Output file path")

    # 10. Mine-suggest command (Google wildcard & alphabet suggest drilldown)
    suggest_p = subparsers.add_parser("mine-suggest", help="Run Google wildcard & alphabet suggest drilldown")
    suggest_p.add_argument("query", help="Root search query (e.g. 'fastapi vs')")
    suggest_p.add_argument("--alphabet", "-a", action="store_true", help="Perform A-Z alphabet drilldown expansion")
    suggest_p.add_argument("--lang", default="en", help="Language code (default: en)")
    suggest_p.add_argument("--country", default="us", help="Country code (default: us)")
    suggest_p.add_argument("--output", "-o", help="Output file path")

    # 11. Audit-drift command (CSR Rendering Drift Auditor)
    drift_p = subparsers.add_parser("audit-drift", help="Audit CSR vs SSR rendering drift")
    drift_p.add_argument("url", help="Target URL to audit")
    drift_p.add_argument("--output", "-o", help="Output file path")

    return parser


def resolve_cli_config(parsed: argparse.Namespace) -> Any:
    from behavioral_playwright.config.settings import AuthConfig, AutomationConfig
    auth = AuthConfig(
        api_key=getattr(parsed, "api_key", None),
        bearer_token=getattr(parsed, "token", None),
    ).resolve()
    return AutomationConfig(auth=auth)


async def run_scrape(url: str, output: Optional[str] = None, target: str = "links", config: Optional[Any] = None) -> int:
    async with BP(config=config) as bp:
        await bp.goto(url)
        records = await bp.extract(target=target)
        raw = [r.to_dict() if hasattr(r, "to_dict") else vars(r) for r in records]
        
        if output:
            saved = DataStorageManager().export(raw, output)
            print(f"[+] Saved {len(raw)} records to {saved}")
        else:
            print(json.dumps(raw, indent=2, default=str))
    return 0


async def run_crawl(url: str, max_pages: int = 5, depth: int = 2, output: Optional[str] = None, config: Optional[Any] = None) -> int:
    async with BP(config=config) as bp:
        records = await bp.crawl(url, max_pages=max_pages)
        raw = [r.to_dict() if hasattr(r, "to_dict") else vars(r) for r in records]
        
        if output:
            saved = DataStorageManager().export(raw, output)
            print(f"[+] Crawled and saved {len(raw)} records to {saved}")
        else:
            print(json.dumps(raw, indent=2, default=str))
    return 0


def run_matrix(config: Optional[Any] = None) -> int:
    bp = BP(config=config)
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


def run_qa_report(db_path: str, config: Optional[Any] = None) -> int:
    bp = BP(config=config)
    report = bp.observability.generate_qa_report(db_path=db_path)
    if isinstance(report, dict):
        print(json.dumps(report, indent=2))
    else:
        print(report)
    return 0


def run_mcp_config(python_path: str = "python") -> int:
    from behavioral_playwright.mcp.server import McpServer
    cfg = McpServer.generate_claude_config(python_path=python_path)
    print(json.dumps(cfg, indent=2))
    return 0


async def run_extract_meta(url: str, output: Optional[str] = None, config: Optional[Any] = None) -> int:
    from behavioral_playwright.extraction.dom import (
        extract_next_data,
        extract_nuxt_data,
        extract_json_ld,
        extract_open_graph,
    )
    html = ""
    try:
        from curl_cffi.requests import AsyncSession
        async with AsyncSession(impersonate="chrome120") as s:
            resp = await s.get(url, timeout=8.0)
            if resp.status_code == 200:
                html = resp.text
    except Exception:
        pass

    if not html:
        try:
            import urllib.request
            def _fetch():
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                with urllib.request.urlopen(req, timeout=8.0) as r:
                    return r.read().decode("utf-8", errors="ignore")
            html = await asyncio.to_thread(_fetch)
        except Exception:
            pass

    next_data = await extract_next_data(html) if html else None
    nuxt_data = await extract_nuxt_data(html) if html else None
    json_ld = await extract_json_ld(html) if html else []
    open_graph = await extract_open_graph(html) if html else {}

    # If no metadata extracted from static HTML and browser is available, fallback to live evaluation
    if not next_data and not nuxt_data and not json_ld and not open_graph:
        try:
            async with BP(config=config) as bp:
                await bp.goto(url)
                next_data = await bp.mining.extract_next_data()
                nuxt_data = await bp.mining.extract_nuxt_data()
                json_ld = await bp.mining.extract_json_ld()
                open_graph = await bp.mining.extract_open_graph()
        except Exception:
            pass

    result = {
        "url": url,
        "next_data": next_data,
        "nuxt_data": nuxt_data,
        "json_ld": json_ld,
        "open_graph": open_graph,
    }

    if output:
        DataStorageManager().export([result], output)
        print(f"[+] Saved metadata to {output}")
    else:
        print(json.dumps(result, indent=2, default=str))
    return 0


async def run_mine_paa(query: str, depth: int = 2, output: Optional[str] = None, config: Optional[Any] = None) -> int:
    from behavioral_playwright.mining.paa_miner import PAAMiner
    from urllib.parse import quote_plus

    miner = PAAMiner(max_depth=depth)
    nodes = []

    # 1. Attempt zero-latency static SERP extraction via curl_cffi
    try:
        from curl_cffi.requests import AsyncSession
        async with AsyncSession(impersonate="chrome120") as s:
            resp = await s.get(f"https://www.google.com/search?q={quote_plus(query)}&hl=en", timeout=8.0)
            if resp.status_code == 200:
                nodes = miner.parse_from_html(resp.text, depth=1)
    except Exception:
        pass

    # 2. Browser-driven interactive expansion fallback
    if not nodes:
        try:
            async with BP(config=config) as bp:
                nodes = await bp.mining.mine_paa(query=query, max_depth=depth)
        except Exception:
            pass

    # 3. Resilient question discovery fallback via Suggest API if SERP CAPTCHA triggered
    if not nodes:
        try:
            from behavioral_playwright.mining.suggest_miner import GoogleSuggestMiner
            from behavioral_playwright.models.seo_dtos import PAANode
            sug_miner = GoogleSuggestMiner()
            prefixes = ["is", "which", "what", "how", "why"]
            for pfx in prefixes:
                sugs = await sug_miner.fetch_suggestions(f"{pfx} {query}")
                for s in sugs[:depth]:
                    q_text = s if s.endswith("?") else f"{s}?"
                    nodes.append(PAANode(
                        question=q_text[0].upper() + q_text[1:],
                        snippet_text="",
                        source_title="",
                        source_url="",
                        depth=1,
                    ))
                if len(nodes) >= depth * 2:
                    break
        except Exception:
            pass

    raw = [n.model_dump() if hasattr(n, "model_dump") else vars(n) for n in nodes]
    if output:
        DataStorageManager().export(raw, output)
        print(f"[+] Saved {len(raw)} PAA questions to {output}")
    else:
        print(json.dumps(raw, indent=2, default=str))
    return 0


async def run_check_overlap(
    query_a: str,
    query_b: str,
    threshold: float = 0.40,
    urls_a: Optional[List[str]] = None,
    urls_b: Optional[List[str]] = None,
    output: Optional[str] = None,
    config: Optional[Any] = None,
) -> int:
    bp = BP(config=config)
    report = await bp.mining.check_overlap(
        query_a=query_a,
        query_b=query_b,
        urls_a=urls_a,
        urls_b=urls_b,
        threshold=threshold,
    )
    raw = report.model_dump() if hasattr(report, "model_dump") else vars(report)
    if output:
        DataStorageManager().export([raw], output)
        print(f"[+] Saved cannibalization report to {output}")
    else:
        print(json.dumps(raw, indent=2, default=str))
    return 0


async def run_mine_suggest(
    query: str,
    alphabet: bool = False,
    lang: str = "en",
    country: str = "us",
    output: Optional[str] = None,
    config: Optional[Any] = None,
) -> int:
    from behavioral_playwright.mining.suggest_miner import GoogleSuggestMiner

    miner = GoogleSuggestMiner(default_lang=lang, default_country=country)
    result = await miner.mine(query=query, alphabet=alphabet, lang=lang, country=country)
    raw = result.model_dump() if hasattr(result, "model_dump") else vars(result)

    if output:
        DataStorageManager().export([raw], output)
        print(f"[+] Saved {raw.get('total_unique', 0)} suggestions to {output}")
    else:
        print(json.dumps(raw, indent=2, default=str))
    return 0


async def run_audit_drift(url: str, output: Optional[str] = None, config: Optional[Any] = None) -> int:
    from behavioral_playwright.verification.rendering_auditor import CSRRenderingDriftAuditor

    auditor = CSRRenderingDriftAuditor()
    report = await auditor.audit_url_drift(url=url)
    raw = report.model_dump() if hasattr(report, "model_dump") else vars(report)

    if output:
        DataStorageManager().export([raw], output)
        print(f"[+] Saved CSR drift report to {output}")
    else:
        print(json.dumps(raw, indent=2, default=str))
    return 0


def main(args: Optional[List[str]] = None) -> int:
    parser = build_parser()
    parsed = parser.parse_args(args)

    if not parsed.command:
        parser.print_help()
        return 0

    config = resolve_cli_config(parsed)

    if parsed.command == "matrix":
        return run_matrix(config=config)
    elif parsed.command == "qa-report":
        return run_qa_report(parsed.db, config=config)
    elif parsed.command == "mcp-server":
        from behavioral_playwright.mcp.server import McpServer
        server = McpServer(config=config)
        asyncio.run(server.run_stdio())
        return 0
    elif parsed.command == "mcp-config":
        return run_mcp_config(parsed.python_path)
    elif parsed.command == "scrape":
        return asyncio.run(run_scrape(parsed.url, parsed.output, parsed.target, config=config))
    elif parsed.command == "crawl":
        return asyncio.run(run_crawl(parsed.url, parsed.max_pages, parsed.depth, parsed.output, config=config))
    elif parsed.command == "extract-meta":
        return asyncio.run(run_extract_meta(parsed.url, parsed.output, config=config))
    elif parsed.command == "mine-paa":
        return asyncio.run(run_mine_paa(parsed.query, parsed.depth, parsed.output, config=config))
    elif parsed.command == "check-overlap":
        return asyncio.run(
            run_check_overlap(
                parsed.query_a,
                parsed.query_b,
                threshold=parsed.threshold,
                urls_a=parsed.urls_a,
                urls_b=parsed.urls_b,
                output=parsed.output,
                config=config,
            )
        )
    elif parsed.command == "mine-suggest":
        return asyncio.run(
            run_mine_suggest(
                parsed.query,
                alphabet=parsed.alphabet,
                lang=parsed.lang,
                country=parsed.country,
                output=parsed.output,
                config=config,
            )
        )
    elif parsed.command == "audit-drift":
        return asyncio.run(run_audit_drift(parsed.url, parsed.output, config=config))

    return 0


if __name__ == "__main__":
    sys.exit(main())
