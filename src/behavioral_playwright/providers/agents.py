"""AI browser-agent provider adapters: Browser-Use and Stagehand.

Verified APIs (official PyPI metadata):
  * browser-use: ``from browser_use import Agent, Browser``;
    ``Agent(task=..., llm=..., browser=...)`` then ``await agent.run()``.
    Requires an LLM instance; Python >= 3.11.
  * stagehand: ``from stagehand import Stagehand, local_browser``;
    ``await Stagehand.create(browser=..., model=..., model_api_key=...)``;
    async page methods (act/extract/observe).

Both are provider-gated and LLM/API-key dependent; absence or missing
configuration raises explicit errors. No fabricated agent results.
"""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Optional

from .base import ProviderInfo, ProviderUnavailableError, detect_provider


class BrowserUseProvider:
    display_name = "browser_use"
    module = "browser_use"
    install_hint = "pip install browser-use"

    def __init__(self, agent_factory: Optional[Callable[..., Any]] = None) -> None:
        # Documented test seam: replaces Agent construction+execution.
        self._agent_factory = agent_factory
        self._info: Optional[ProviderInfo] = None

    def info(self) -> ProviderInfo:
        if self._info is None:
            self._info = detect_provider(self.display_name, self.module)
        return self._info

    def is_available(self) -> bool:
        return self.info().installed

    def require_available(self) -> None:
        if not self.info().installed:
            raise ProviderUnavailableError(self.display_name, self.module, self.install_hint)

    def run_task(self, task: str, llm: Any = None, browser: Any = None,
                 **kwargs: Any) -> Any:
        """Run a Browser-Use agent task synchronously.

        ``llm`` is mandatory (the real Agent requires one); this adapter never
        invents an LLM or a result. The agent's genuine run output is returned.
        """
        if not task or not isinstance(task, str):
            raise ValueError("task must be a non-empty string")
        if llm is None:
            raise ValueError(
                "browser_use requires an LLM instance (e.g. langchain_openai."
                "ChatOpenAI). The adapter will not fabricate one."
            )
        if self._agent_factory is not None:
            return self._agent_factory(task=task, llm=llm, browser=browser, **kwargs)
        self.require_available()
        from browser_use import Agent

        agent = Agent(task=task, llm=llm, browser=browser, **kwargs)
        try:
            return asyncio.run(agent.run())
        except RuntimeError as exc:
            if "event loop" in str(exc).lower():
                raise RuntimeError(
                    "browser_use Agent.run() is async: use the sync run_task() "
                    "outside a running event loop, or drive the Agent directly "
                    "inside your own loop."
                ) from exc
            raise


class StagehandProvider:
    display_name = "stagehand"
    module = "stagehand"
    install_hint = "pip install stagehand"

    def __init__(self, stagehand_factory: Optional[Callable[..., Any]] = None) -> None:
        # Documented test seam: replaces Stagehand.create.
        self._stagehand_factory = stagehand_factory
        self._info: Optional[ProviderInfo] = None

    def info(self) -> ProviderInfo:
        if self._info is None:
            self._info = detect_provider(self.display_name, self.module)
        return self._info

    def is_available(self) -> bool:
        return self.info().installed

    def require_available(self) -> None:
        if not self.info().installed:
            raise ProviderUnavailableError(self.display_name, self.module, self.install_hint)

    async def start(self, browser: Any = None, model: Optional[str] = None,
                    model_api_key: Optional[str] = None, **config: Any) -> Any:
        """Async-create a real Stagehand session (verified API)."""
        if model is None or model_api_key is None:
            raise ValueError(
                "stagehand requires 'model' and 'model_api_key' (verified "
                "Stagehand.create signature); the adapter will not fabricate them."
            )
        if self._stagehand_factory is not None:
            return await self._stagehand_factory(
                browser=browser, model=model, model_api_key=model_api_key, **config
            )
        self.require_available()
        from stagehand import Stagehand

        return await Stagehand.create(
            browser=browser, model=model, model_api_key=model_api_key, **config
        )
