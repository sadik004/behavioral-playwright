"""
LLM API Provider supporting OpenAI/Ollama compatible REST endpoints with deterministic offline mock modes.
"""

import asyncio
import json
import logging
import os
import urllib.request
from typing import Any, Optional, Protocol, runtime_checkable

logger = logging.getLogger("BehavioralAutomation.AI.LLMProvider")


@runtime_checkable
class LLMProviderProtocol(Protocol):
    async def generate_response(self, prompt: str, system_prompt: Optional[str] = None) -> str: ...


class LLMProvider:
    """Async provider for Ollama, OpenAI, or local API gateways."""

    def __init__(self, config: Any) -> None:
        self.config = config
        self.logger = logger
        self.api_key = os.environ.get("STEALTH_LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
        self.base_url = os.environ.get("STEALTH_LLM_BASE_URL") or "https://api.openai.com/v1"
        self.model = os.environ.get("STEALTH_LLM_MODEL") or "gpt-4o"

    async def generate_response(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        if hasattr(self.config, "ai") and not self.config.ai.enabled:
            return ""

        is_test = os.environ.get("STEALTH_TEST_MODE") == "true"
        is_offline = not self.api_key and "localhost" not in self.base_url and "127.0.0.1" not in self.base_url

        if is_test or is_offline:
            return self._generate_structured_mock_response(prompt)

        retries = self.config.ai.retry if hasattr(self.config, "ai") else 2
        timeout = self.config.ai.timeout if hasattr(self.config, "ai") else 5.0

        for attempt in range(retries + 1):
            try:
                headers = {"Content-Type": "application/json"}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"

                payload = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt or "You are an AI selector healing agent."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.1,
                }

                req = urllib.request.Request(
                    f"{self.base_url.rstrip('/')}/chat/completions",
                    data=json.dumps(payload).encode("utf-8"),
                    headers=headers,
                    method="POST",
                )

                def _sync_post() -> str:
                    with urllib.request.urlopen(req, timeout=timeout) as response:
                        res_json = json.loads(response.read().decode("utf-8"))
                        return str(res_json["choices"][0]["message"]["content"])

                return await asyncio.to_thread(_sync_post)
            except Exception as e:
                self.logger.warning(f"[LLM] Retry attempt {attempt + 1} failed: {e}")
                if attempt == retries:
                    return self._generate_structured_mock_response(prompt)
                await asyncio.sleep(1.0)

        return ""

    def _generate_structured_mock_response(self, prompt: str) -> str:
        p_lower = prompt.lower()
        if "trigger_malformed_json" in p_lower:
            return "This is not valid JSON string."
        if "login" in p_lower or "submit" in p_lower:
            return json.dumps(
                {
                    "action": "click",
                    "selector": "button[type='submit']",
                    "confidence": 0.95,
                    "reason": "Submit button selected.",
                }
            )
        elif "input" in p_lower or "username" in p_lower:
            return json.dumps(
                {
                    "action": "type",
                    "selector": "#text-input",
                    "confidence": 0.88,
                    "reason": "Input element matched.",
                }
            )
        return json.dumps(
            {
                "action": "wait",
                "selector": "body",
                "confidence": 0.50,
                "reason": "Fallback matched.",
            }
        )
