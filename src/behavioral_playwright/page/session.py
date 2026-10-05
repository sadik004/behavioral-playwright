"""High-level PageSession and BrowserSession abstractions."""

import uuid
from types import TracebackType
from typing import Any, Callable, Coroutine, Dict, List, Optional, Type, TypeVar

from behavioral_playwright.automation.keyboard import KeyboardController
from behavioral_playwright.automation.mouse import MouseController
from behavioral_playwright.automation.scroll import ScrollController
from behavioral_playwright.browser.base import BrowserProvider
from behavioral_playwright.browser.playwright_provider import PlaywrightProvider
from behavioral_playwright.config.settings import AutomationConfig
from behavioral_playwright.exceptions import NavigationError
from behavioral_playwright.extraction.dom import DOMExtractor
from behavioral_playwright.logging import get_logger
from behavioral_playwright.models.results import ExtractionRecord, ResolutionResult
from behavioral_playwright.resilience.circuit_breaker import CircuitBreaker
from behavioral_playwright.resilience.idempotency import OperationType
from behavioral_playwright.resilience.recovery import RecoveryManager
from behavioral_playwright.resilience.retry import RetryPolicy
from behavioral_playwright.resilience.state import StateTracker
from behavioral_playwright.resilience.taxonomy import classify_failure, is_recoverable_via_restart
from behavioral_playwright.selectors.resolver import SelfHealingResolver

logger = get_logger("page.session")

T = TypeVar("T")


class PageSession:
    """
    High-level facade over an active browser page.
    Binds SelfHealingResolver, automation controllers, resilience, and extraction.
    """

    def __init__(
        self,
        raw_page: Any,
        provider: BrowserProvider,
        config: AutomationConfig,
        session_id: Optional[str] = None,
    ) -> None:
        self.session_id = session_id or str(uuid.uuid4())
        self.raw_page = raw_page
        self.provider = provider
        self.config = config

        # PowerPlay Mathematical & Biometric Engines
        from behavioral_playwright.powerplay.biomechanics import BiomechanicalTremorEngine
        from behavioral_playwright.powerplay.keystrokes import LinguisticKeystrokeDynamicsEngine
        from behavioral_playwright.powerplay.captcha import ResolvedCAPTCHAInfiniteLoopDetector
        from behavioral_playwright.powerplay.schema_guard import ResolvedSchemaIntegrityGuard
        from behavioral_playwright.powerplay.vision_guard import UltimateVisionLanguageActionGuard

        self.biomechanics = BiomechanicalTremorEngine()
        self.keystrokes = LinguisticKeystrokeDynamicsEngine()
        self.loop_detector = ResolvedCAPTCHAInfiniteLoopDetector()
        self.schema_guard = ResolvedSchemaIntegrityGuard()
        self.vision_guard = UltimateVisionLanguageActionGuard()

        # Automation Controllers with Biomechanical Wiring
        self.mouse = MouseController(raw_page, biomechanics=self.biomechanics, vision_guard=self.vision_guard)
        self.keyboard = KeyboardController(raw_page, keystrokes=self.keystrokes)
        self.scroll = ScrollController(raw_page)

        # Extraction & Resolution
        self.resolver = SelfHealingResolver(config.resolver)
        self.extractor = DOMExtractor()

        # Resilience & Recovery Primitives
        self.state_tracker = StateTracker()
        self.retry_policy = RetryPolicy(config.retry)
        self.circuit_breaker = CircuitBreaker(config.circuit_breaker)
        self.recovery_manager = RecoveryManager(session_id=self.session_id)

    async def goto(self, url: str, wait_until: str = "domcontentloaded", timeout_ms: Optional[int] = None, audit_page: bool = True) -> None:
        """Navigates to URL and records the page state in StateTracker, LoopDetector, and SchemaGuard."""
        # 1. Evaluate Markov navigation cycle and 3-state circuit breaker
        nav_eval = self.loop_detector.record_navigation(url)
        if nav_eval.get("circuit_state") == self.loop_detector.STATE_OPEN:
            logger.warning(f"[Security] CAPTCHA loop or challenge storm detected at {url}. Action: ROTATE_PROXY")

        # 2. Execute underlying navigation directly on this page instance
        to = timeout_ms if timeout_ms is not None else self.config.browser.timeout_ms
        try:
            if hasattr(self.raw_page, "goto") and callable(self.raw_page.goto):
                await self.raw_page.goto(url, wait_until=wait_until, timeout=to)
            else:
                await self.provider.goto(url, wait_until=wait_until, timeout_ms=to)
        except Exception as e:
            if isinstance(e, NavigationError):
                raise
            raise NavigationError(f"Failed to navigate to '{url}': {e}") from e

        title = await self.get_title()
        self.state_tracker.record_state(url=url, title=title)

        # 3. Dynamic DOM audit for Honeypots and Blank/Challenge Pages
        if audit_page:
            try:
                content = await self.evaluate("() => document.documentElement ? document.documentElement.outerHTML : ''")
                if content and isinstance(content, str):
                    audit_res = self.schema_guard.audit_content_entropy(content)
                    if audit_res.get("decision") == "CAPTCHA_WALL":
                        self.loop_detector.record_navigation(url, is_challenge=True)
            except Exception as exc:
                logger.debug(f"Dynamic DOM audit skipped/failed for {url}: {exc}")

    async def get_title(self) -> str:
        """Returns active page title."""
        if hasattr(self.raw_page, "title") and callable(self.raw_page.title):
            return await self.raw_page.title()
        return await self.provider.get_title()

    async def get_url(self) -> str:
        """Returns active page URL."""
        if hasattr(self.raw_page, "url"):
            url_val = self.raw_page.url
            return url_val() if callable(url_val) else url_val
        return await self.provider.get_url()

    async def evaluate(self, script: str, arg: Any = None) -> Any:
        """Evaluates JavaScript expression."""
        if hasattr(self.raw_page, "evaluate") and callable(self.raw_page.evaluate):
            return await self.raw_page.evaluate(script, arg)
        return await self.provider.evaluate(script, arg)

    async def screenshot(self, path: Optional[str] = None) -> bytes:
        """Captures page screenshot."""
        if hasattr(self.raw_page, "screenshot") and callable(self.raw_page.screenshot):
            return await self.raw_page.screenshot(path=path)
        return await self.provider.screenshot(path=path)

    async def resolve(self, target: str) -> ResolutionResult:
        """Resolves target element using SelfHealingResolver cascade."""
        return await self.resolver.resolve(self.raw_page, target)

    async def click_healed(self, target: str) -> ResolutionResult:
        """Resolves and clicks on target element using self-healing."""
        return await self.resolver.resolve_and_click(self.raw_page, target)

    async def type_healed(self, target: str, text: str) -> ResolutionResult:
        """Resolves and fills text into target element using self-healing."""
        return await self.resolver.resolve_and_type(self.raw_page, target, text)

    async def extract_links(self, container_selector: Optional[str] = None) -> List[ExtractionRecord]:
        """Extracts structured hyperlinks from page."""
        return await self.extractor.extract_links(self.raw_page, container_selector)

    async def extract_articles(self, container_selector: Optional[str] = None) -> List[ExtractionRecord]:
        """Extracts structured article blocks from page."""
        return await self.extractor.extract_articles(self.raw_page, container_selector)

    async def extract_table(self, table_selector: str, has_headers: bool = True) -> List[Dict[str, Any]]:
        """Extracts table rows from page."""
        return await self.extractor.extract_table(self.raw_page, table_selector, has_headers=has_headers)

    async def extract_text(self, selector: str, normalize: bool = True, visible_only: bool = True) -> str:
        """Extracts text content from selector."""
        return await self.extractor.extract_text(self.raw_page, selector, normalize=normalize, visible_only=visible_only)

    async def extract_attributes(self, selector: str, attributes: Optional[List[str]] = None) -> Dict[str, Optional[str]]:
        """Extracts attributes from selector."""
        return await self.extractor.extract_attributes(self.raw_page, selector, attributes=attributes)

    async def extract_html(self, selector: str, outer: bool = True) -> str:
        """Extracts inner/outer HTML from selector."""
        return await self.extractor.extract_html(self.raw_page, selector, outer=outer)

    async def extract_images(self, container_selector: Optional[str] = None) -> List[ExtractionRecord]:
        """Extracts images from page or container."""
        return await self.extractor.extract_images(self.raw_page, container_selector)

    async def extract_list(self, list_selector: str, normalize: bool = True) -> List[str]:
        """Extracts list items from page."""
        return await self.extractor.extract_list(self.raw_page, list_selector, normalize=normalize)

    async def extract_cards(self, item_selector: str, schema: Dict[str, str], container_selector: Optional[str] = None) -> List[Dict[str, Any]]:
        """Extracts structured repeated cards."""
        return await self.extractor.extract_cards(self.raw_page, item_selector, schema, container_selector=container_selector)

    async def extract_next_data(self) -> Optional[Dict[str, Any]]:
        """Extracts Next.js state dictionary."""
        return await self.extractor.extract_next_data(self.raw_page)

    async def extract_nuxt_data(self) -> Optional[Dict[str, Any]]:
        """Extracts Nuxt state dictionary."""
        return await self.extractor.extract_nuxt_data(self.raw_page)

    async def extract_json_ld(self) -> List[Dict[str, Any]]:
        """Extracts JSON-LD schema objects."""
        return await self.extractor.extract_json_ld(self.raw_page)

    async def extract_open_graph(self) -> Dict[str, str]:
        """Extracts OpenGraph metadata tags."""
        return await self.extractor.extract_open_graph(self.raw_page)

    async def map_schema(
        self,
        schema: Any,
        confidence_threshold: float = 0.60,
        strict_ambiguity: bool = False,
        require_all_fields: bool = False,
    ) -> Any:
        """Extracts and maps live page evidence to target schema."""
        from behavioral_playwright.mapping.schema_mapper import PageSchemaMapper
        mapper = PageSchemaMapper(confidence_threshold=confidence_threshold)
        return await mapper.map_schema(
            self,
            schema,
            strict_ambiguity=strict_ambiguity,
            require_all_fields=require_all_fields,
        )

    async def map_site(self, url: Optional[str] = None) -> Dict[str, Any]:
        """Maps structural links, articles, and heading hierarchies."""
        from behavioral_playwright.mapping.mapper import SiteMapper
        target_url = url or await self.get_url()
        mapper = SiteMapper(self)
        return await mapper.map(target_url)

    async def search(
        self,
        query: str,
        search_input_selector: str = "input[type='search'], input[name='q']",
        submit_selector: str = "button[type='submit']",
        results_container_selector: Optional[str] = None,
    ) -> List[ExtractionRecord]:
        """Executes a search query and extracts results."""
        from behavioral_playwright.search.engine import SearchEngine
        engine = SearchEngine(self)
        return await engine.search(
            query,
            search_input_selector=search_input_selector,
            submit_selector=submit_selector,
            results_container_selector=results_container_selector,
        )

    async def recover(self, reason: Optional[str] = None, restore_url: bool = True) -> bool:
        """Executes coordinated recovery of the page instance, invalidating stale state and verifying new page."""
        return await self.recovery_manager.execute_recovery(
            self,
            error=RuntimeError(reason or "Manual page recovery requested"),
            restore_url=restore_url,
        )

    async def execute_resilient(
        self,
        coro_fn: Callable[[], Coroutine[Any, Any, T]],
        operation_name: str = "operation",
        operation_type: OperationType = OperationType.READ,
        timeout_budget_s: Optional[float] = None,
        auto_recover: bool = True,
        explicit_idempotent: Optional[bool] = None,
    ) -> T:
        """Executes an operation protected by circuit breaker, retry policy with timeout budget/idempotency, and recovery."""
        async def _run_with_retry() -> T:
            return await self.retry_policy.execute(
                coro_fn,
                operation_name=operation_name,
                operation_type=operation_type,
                timeout_budget_s=timeout_budget_s,
                explicit_idempotent=explicit_idempotent,
            )

        try:
            return await self.circuit_breaker.execute(_run_with_retry, operation_name=operation_name)
        except Exception as exc:
            category = classify_failure(exc)
            if auto_recover and is_recoverable_via_restart(category):
                logger.warning(
                    f"[PageSession:{self.session_id}] Operation '{operation_name}' failed with {category.value}. "
                    "Initiating architectural recovery..."
                )
                recovered = await self.recovery_manager.execute_recovery(self, error=exc, restore_url=True)
                if recovered:
                    logger.info(f"[PageSession:{self.session_id}] Session recovered and verified. Re-executing '{operation_name}'...")
                    return await coro_fn()
            raise

    async def run_workflow(
        self,
        workflow: Optional[Any] = None,
        planner: Optional[Any] = None,
        goal: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Executes an orchestrated, verification-driven workflow on this PageSession."""
        from behavioral_playwright.orchestration.models import WorkflowDefinition
        from behavioral_playwright.orchestration.orchestrator import WorkflowOrchestrator
        from behavioral_playwright.orchestration.planner import DeterministicPlanner

        orchestrator = WorkflowOrchestrator()
        if workflow is None and goal is not None:
            active_planner = planner or DeterministicPlanner()
            steps = await active_planner.plan(goal=goal, context=context)
            workflow = WorkflowDefinition.create(
                session_id=self.session_id,
                steps=steps,
                name=goal,
            )
        elif not isinstance(workflow, WorkflowDefinition):
            raise ValueError("Must provide either a WorkflowDefinition or a goal string.")

        return await orchestrator.execute_workflow(workflow, session=self)

    async def close(self) -> None:
        """Closes this page."""
        await self.provider.close_page(self.raw_page)

    def is_closed(self) -> bool:
        """Returns True if the underlying raw page is closed or None."""
        if self.raw_page is None:
            return True
        if hasattr(self.raw_page, "is_closed"):
            return self.raw_page.is_closed()
        return False



class BrowserSession:
    """
    High-level async context manager managing browser lifecycle.
    Example:
        async with BrowserSession() as session:
            page = await session.new_page()
            await page.goto("https://example.com")
    """

    def __init__(
        self,
        config: Optional[AutomationConfig] = None,
        provider: Optional[BrowserProvider] = None,
        session_id: Optional[str] = None,
    ) -> None:
        self.session_id = session_id or str(uuid.uuid4())
        self.config = config or AutomationConfig()
        self.provider = provider or PlaywrightProvider(self.config.browser)
        self._is_active: bool = False

    async def __aenter__(self) -> "BrowserSession":
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType]
    ) -> None:
        await self.close()

    async def start(self) -> None:
        """Launches the underlying browser backend."""
        logger.info("[Session] Starting BrowserSession lifecycle...")
        await self.provider.launch(self.config.browser)
        self._is_active = True

    async def new_page(self, session_id: Optional[str] = None) -> PageSession:
        """Spawns a new PageSession wrapped with self-healing and automation facade."""
        raw_page = await self.provider.new_page()
        return PageSession(
            raw_page=raw_page,
            provider=self.provider,
            config=self.config,
            session_id=session_id or f"{self.session_id}:{uuid.uuid4().hex[:6]}",
        )

    async def close(self) -> None:
        """Terminates the browser session and releases all resources."""
        if self._is_active:
            logger.info("[Session] Closing BrowserSession...")
            await self.provider.close()
            self._is_active = False

    def is_closed(self) -> bool:
        """Returns True if the browser session is closed/inactive."""
        return not self._is_active
