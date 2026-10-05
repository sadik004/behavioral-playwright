"""Precondition and postcondition verification logic for workflow steps."""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

from behavioral_playwright.orchestration.exceptions import (
    PostconditionFailedError,
    PreconditionFailedError,
)
from behavioral_playwright.orchestration.models import Condition, WorkflowStep
from behavioral_playwright.orchestration.state import WorkflowState


class ConditionEvaluator:
    """Evaluates preconditions and postconditions against live session and workflow state."""

    @classmethod
    async def evaluate_precondition(
        cls,
        condition: Condition,
        session: Any,
        state: WorkflowState,
        step: WorkflowStep,
    ) -> bool:
        """Evaluates a single precondition prior to step execution."""
        ok = await cls._evaluate(condition, session, state, step)
        if not ok:
            raise PreconditionFailedError(
                f"Precondition '{condition.name}' ({condition.condition_type}) FAILED for step '{step.step_id}'. "
                f"Params: {condition.params}"
            )
        return True

    @classmethod
    async def evaluate_postcondition(
        cls,
        condition: Condition,
        session: Any,
        state: WorkflowState,
        step: WorkflowStep,
    ) -> bool:
        """Evaluates a single postcondition following step execution."""
        ok = await cls._evaluate(condition, session, state, step)
        if not ok:
            raise PostconditionFailedError(
                f"Postcondition '{condition.name}' ({condition.condition_type}) FAILED for step '{step.step_id}'. "
                f"Params: {condition.params}"
            )
        return True

    @classmethod
    async def _evaluate(
        cls,
        condition: Condition,
        session: Any,
        state: WorkflowState,
        step: WorkflowStep,
    ) -> bool:
        ctype = condition.condition_type.lower()
        params = condition.params

        # 1. Custom callable evaluator
        if condition.evaluator is not None and callable(condition.evaluator):
            res = condition.evaluator(session, state, step)
            if hasattr(res, "__await__"):
                return bool(await res)
            return bool(res)

        # 2. Page open check
        if ctype == "page_open":
            if session is None:
                return False
            page = getattr(session, "raw_page", None)
            if page is None:
                return False
            if hasattr(page, "is_closed") and callable(page.is_closed):
                return not page.is_closed()
            return True

        # 3. Element exists check (unique live resolution)
        if ctype == "element_exists":
            selector = params.get("selector", "")
            if not selector:
                return False
            if hasattr(session, "resolve"):
                try:
                    res = await session.resolve(selector)
                    if res is not None and (res.success or getattr(res, "matched_element", None) is not None or getattr(res, "element", None) is not None):
                        return True
                except Exception:
                    pass
            page = getattr(session, "raw_page", None)
            if page and hasattr(page, "query_selector"):
                try:
                    el = await page.query_selector(selector)
                    return el is not None
                except Exception:
                    return False
            return False

        # 4. URL matching check
        if ctype == "url_matches":
            pattern = params.get("pattern", "")
            page = getattr(session, "raw_page", None)
            current_url = getattr(page, "url", "") if page else ""
            if not current_url and hasattr(session, "get_url"):
                current_url = await session.get_url()
            return bool(re.search(pattern, current_url))

        # 5. Variable present in workflow state
        if ctype == "variable_present":
            var_name = params.get("variable", "")
            return var_name in state.variables

        # 6. Data valid / non-empty check
        if ctype == "data_valid":
            field_name = params.get("field")
            if step.result is None:
                return False
            if field_name:
                if isinstance(step.result, dict):
                    return bool(step.result.get(field_name))
                return bool(getattr(step.result, field_name, None))
            return True

        # 7. Default fallback: True if unspecified
        return True
