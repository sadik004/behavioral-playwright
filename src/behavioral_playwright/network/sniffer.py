"""
Background XHR/Fetch API Sniffer.
Captures raw backend API JSON payloads during navigation, scrolling, or user interaction
without touching or querying DOM nodes.
"""

from __future__ import annotations

import asyncio
import fnmatch
import json
import re
import time
from typing import Any, Callable, Dict, List, Optional

from behavioral_playwright.logging import get_logger

logger = get_logger("network.sniffer")


class JSONResponseSniffer:
    """
    Asynchronous network response sniffer for intercepting and buffering JSON payloads.
    Hooks into Playwright page response events to capture backend REST/GraphQL data streams.
    """

    def __init__(self, page: Any) -> None:
        self.raw_page = getattr(page, "raw_page", None) or page
        self._captured: List[Dict[str, Any]] = []
        self._lock = asyncio.Lock()
        self._new_data_event = asyncio.Event()
        self._handler: Optional[Callable[[Any], Any]] = None
        self._is_attached = False

        self.attach()

    @property
    def captured_responses(self) -> List[Dict[str, Any]]:
        """Returns a copy of all buffered response payload records."""
        return list(self._captured)

    def attach(self) -> None:
        """Subscribes response interception handler to the underlying page."""
        if self._is_attached:
            return

        async def _on_response(response: Any) -> None:
            try:
                # Filter out obvious non-JSON resources early
                url = getattr(response, "url", "")
                headers = getattr(response, "headers", {}) or {}
                content_type = headers.get("content-type", "").lower()

                # Attempt JSON extraction if content-type indicates JSON or URL ends with json/api
                is_json_candidate = (
                    "application/json" in content_type
                    or "+json" in content_type
                    or "application/x-ndjson" in content_type
                    or "/api/" in url
                    or url.endswith(".json")
                )

                data: Any = None
                if is_json_candidate:
                    if hasattr(response, "json"):
                        try:
                            data = await response.json()
                        except Exception:
                            # Could be text containing json
                            if hasattr(response, "text"):
                                txt = await response.text()
                                if txt and (txt.startswith("{") or txt.startswith("[")):
                                    data = json.loads(txt)
                    elif hasattr(response, "text"):
                        txt = await response.text()
                        if txt and (txt.startswith("{") or txt.startswith("[")):
                            data = json.loads(txt)

                if data is not None:
                    async with self._lock:
                        self._captured.append({
                            "url": url,
                            "status": getattr(response, "status", 200),
                            "content_type": content_type,
                            "data": data,
                            "timestamp": time.time(),
                        })
                        self._new_data_event.set()
            except Exception as exc:
                logger.debug(f"[JSONResponseSniffer] Non-fatal response decode error: {exc}")

        self._handler = _on_response
        if hasattr(self.raw_page, "on"):
            try:
                self.raw_page.on("response", self._handler)
                self._is_attached = True
            except Exception as exc:
                logger.warning(f"[JSONResponseSniffer] Failed to attach page listener: {exc}")

    def detach(self) -> None:
        """Unsubscribes response interception listener."""
        if not self._is_attached or not self._handler:
            return
        if hasattr(self.raw_page, "remove_listener"):
            try:
                self.raw_page.remove_listener("response", self._handler)
            except Exception:
                pass
        self._is_attached = False

    def clear(self) -> None:
        """Clears all buffered response data."""
        self._captured.clear()
        self._new_data_event.clear()

    def _matches_any_pattern(self, url: str, patterns: List[str]) -> bool:
        """Evaluates whether URL satisfies substring, glob, or regex patterns."""
        if not patterns:
            return True
        for pattern in patterns:
            if pattern in url:
                return True
            if fnmatch.fnmatch(url, pattern):
                return True
            try:
                if re.search(pattern, url):
                    return True
            except re.error:
                pass
        return False

    async def intercept_json(
        self,
        url_patterns: List[str],
        timeout: float = 10.0,
    ) -> List[Dict[str, Any]]:
        """
        Captures and returns parsed JSON payloads from background XHR/Fetch API requests
        matching the provided URL patterns. Waits up to timeout seconds for matching requests.
        """
        start_time = time.time()
        deadline = start_time + max(0.1, timeout)

        while True:
            # 1. Search buffered responses
            async with self._lock:
                matches = [
                    item["data"]
                    for item in self._captured
                    if self._matches_any_pattern(item["url"], url_patterns)
                ]
                if matches:
                    return matches

            remaining = deadline - time.time()
            if remaining <= 0:
                break

            self._new_data_event.clear()
            try:
                await asyncio.wait_for(self._new_data_event.wait(), timeout=min(remaining, 0.5))
            except asyncio.TimeoutError:
                pass

        # Final check before return
        async with self._lock:
            return [
                item["data"]
                for item in self._captured
                if self._matches_any_pattern(item["url"], url_patterns)
            ]

    async def __aenter__(self) -> "JSONResponseSniffer":
        self.attach()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.detach()


__all__ = ["JSONResponseSniffer"]
