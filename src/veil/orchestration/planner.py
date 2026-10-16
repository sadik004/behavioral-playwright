"""Planner abstractions translating high-level goals into declarative workflow plans."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional

from behavioral_playwright.orchestration.exceptions import PlanError
from behavioral_playwright.orchestration.models import (
    ActionType,
    Condition,
    WorkflowStep,
)


class BasePlanner(ABC):
    """Abstract base planner interface.
    
    Invariant: Planner output is strictly a proposed PLAN, never execution evidence.
    """

    @abstractmethod
    async def plan(self, goal: str, context: Optional[Dict[str, Any]] = None) -> List[WorkflowStep]:
        """Synthesizes an ordered sequence of WorkflowSteps to achieve the given goal."""
        pass


class DeterministicPlanner(BasePlanner):
    """Deterministic, rule-based planner operating without external LLM dependencies.
    
    Maps canonical intent templates (e.g. scrape, search, map_schema, form_submit)
    into robust, self-healing workflow step graphs.
    """

    async def plan(self, goal: str, context: Optional[Dict[str, Any]] = None) -> List[WorkflowStep]:
        ctx = context or {}
        g = goal.strip().lower()

        # 1. Scrape / Extraction Plan
        if g in ("scrape", "extract", "extract_data"):
            url = ctx.get("url")
            selector = ctx.get("selector")
            steps = []
            if url:
                steps.append(
                    WorkflowStep.create(
                        action="navigate",
                        action_type=ActionType.NAVIGATION,
                        input_data={"url": url},
                        preconditions=[Condition(name="page_open", condition_type="page_open")],
                        postconditions=[Condition(name="url_matches", condition_type="url_matches", params={"pattern": url})],
                    )
                )
            if selector:
                steps.append(
                    WorkflowStep.create(
                        action="resolve",
                        action_type=ActionType.READ_ONLY,
                        input_data={"selector": selector},
                        postconditions=[Condition(name="target_found", condition_type="element_exists", params={"selector": selector})],
                    )
                )
            steps.append(
                WorkflowStep.create(
                    action="extract",
                    action_type=ActionType.DATA_EXTRACTION,
                    input_data={"selector": selector} if selector else {},
                )
            )
            return steps

        # 2. Schema Mapping Plan
        if g in ("map_schema", "page_intelligence"):
            url = ctx.get("url")
            schema_cls = ctx.get("schema")
            steps = []
            if url:
                steps.append(
                    WorkflowStep.create(
                        action="navigate",
                        action_type=ActionType.NAVIGATION,
                        input_data={"url": url},
                    )
                )
            steps.append(
                WorkflowStep.create(
                    action="map_schema",
                    action_type=ActionType.DATA_EXTRACTION,
                    input_data={"schema": schema_cls},
                )
            )
            return steps

        # 3. Search Plan
        if g in ("search", "site_search"):
            query = ctx.get("query", "")
            if not query:
                raise PlanError("Planner Error: Search goal requires 'query' in context.")
            url = ctx.get("url")
            steps = []
            if url:
                steps.append(
                    WorkflowStep.create(
                        action="navigate",
                        action_type=ActionType.NAVIGATION,
                        input_data={"url": url},
                    )
                )
            steps.append(
                WorkflowStep.create(
                    action="search",
                    action_type=ActionType.DOM_INTERACTION,
                    input_data={"query": query},
                )
            )
            return steps

        # 4. Click & Verify Plan
        if g in ("click", "click_element"):
            selector = ctx.get("selector", "")
            if not selector:
                raise PlanError("Planner Error: Click goal requires 'selector' in context.")
            url = ctx.get("url")
            steps = []
            if url:
                steps.append(
                    WorkflowStep.create(
                        action="navigate",
                        action_type=ActionType.NAVIGATION,
                        input_data={"url": url},
                    )
                )
            steps.append(
                WorkflowStep.create(
                    action="resolve",
                    action_type=ActionType.READ_ONLY,
                    input_data={"selector": selector},
                    postconditions=[Condition(name="target_found", condition_type="element_exists", params={"selector": selector})],
                )
            )
            steps.append(
                WorkflowStep.create(
                    action="click",
                    action_type=ActionType.DOM_INTERACTION,
                    input_data={"selector": selector},
                )
            )
            return steps

        # 5. Form Fill & Submit Plan
        if g in ("form_submit", "login", "fill_form"):
            url = ctx.get("url")
            inputs = ctx.get("inputs", {})            # Dict[selector, text]
            submit_selector = ctx.get("submit_selector")
            steps = []
            if url:
                steps.append(
                    WorkflowStep.create(
                        action="navigate",
                        action_type=ActionType.NAVIGATION,
                        input_data={"url": url},
                    )
                )
            for sel, val in inputs.items():
                steps.append(
                    WorkflowStep.create(
                        action="type",
                        action_type=ActionType.STATE_MUTATION,
                        input_data={"selector": sel, "text": val},
                    )
                )
            if submit_selector:
                steps.append(
                    WorkflowStep.create(
                        action="click",
                        action_type=ActionType.STATE_MUTATION,
                        input_data={"selector": submit_selector},
                    )
                )
            return steps

        # Unrecognized goal
        raise PlanError(f"Planner Error: Unable to synthesize plan for unrecognized goal '{goal}'.")


class ExternalAgentPlanner(BasePlanner):
    """Integrates external agents / LLMs while strictly gating and validating their proposed plans."""

    def __init__(self, external_fn: Callable[[str, Dict[str, Any]], Any]) -> None:
        self._external_fn = external_fn

    async def plan(self, goal: str, context: Optional[Dict[str, Any]] = None) -> List[WorkflowStep]:
        ctx = context or {}
        raw_plan = self._external_fn(goal, ctx)
        if hasattr(raw_plan, "__await__"):
            raw_plan = await raw_plan

        if not isinstance(raw_plan, list):
            raise PlanError("External Agent Planner returned invalid non-list plan.")

        steps: List[WorkflowStep] = []
        for item in raw_plan:
            if isinstance(item, WorkflowStep):
                steps.append(item)
            elif isinstance(item, dict):
                act = item.get("action", "")
                act_type_str = item.get("action_type", "READ_ONLY")
                try:
                    act_type = ActionType(act_type_str)
                except ValueError:
                    act_type = ActionType.READ_ONLY
                step = WorkflowStep.create(
                    action=act,
                    action_type=act_type,
                    input_data=item.get("input_data", {}),
                    step_id=item.get("step_id"),
                    timeout_s=float(item.get("timeout_s", 30.0)),
                )
                steps.append(step)
            else:
                raise PlanError(f"Unsupported plan step type: {type(item)}")

        if not steps:
            raise PlanError("External Agent Planner returned empty plan.")

        return steps
