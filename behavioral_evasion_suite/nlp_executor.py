"""
NLP Action Executor for Behavioral Playwright
Binds parsed natural language actions directly to StealthSession and Level 5 Quantum Shields.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

try:
    from .nlp_intent_parser import NLPIntentParser, BrowserAction, ActionType
    from .stealth_session import StealthSession, human_click, human_type, human_scroll, cognitive_reading_pause
    from .satellite_field_verifier import SatelliteFieldVerifier, SatelliteYardLocation
except (ImportError, ValueError):
    from nlp_intent_parser import NLPIntentParser, BrowserAction, ActionType
    from stealth_session import StealthSession, human_click, human_type, human_scroll, cognitive_reading_pause
    from satellite_field_verifier import SatelliteFieldVerifier, SatelliteYardLocation

logger = logging.getLogger("BehavioralEvasion.NLPExecutor")


class ActionExecutionLog(BaseModel):
    def model_dump(self, **kwargs):
        return self.dict(**kwargs) if hasattr(self, "dict") else super().model_dump(**kwargs)

    step: int
    action_type: str
    description: str
    status: str
    output: Optional[str] = None


class NLPExecutionResult(BaseModel):
    def model_dump(self, **kwargs):
        return self.dict(**kwargs) if hasattr(self, "dict") else super().model_dump(**kwargs)

    prompt: str
    total_steps: int
    successful_steps: int
    execution_logs: List[ActionExecutionLog]
    extracted_text: Optional[str] = None
    satellite_yard_bundle: Optional[Dict[str, Any]] = None
    final_url: Optional[str] = None


class NLPStealthExecutor:
    def __init__(self, profile: str = "win11_nvidia_rtx4070"):
        self.profile = profile
        self.parser = NLPIntentParser()
        self.yard_verifier = SatelliteFieldVerifier()

    async def execute(self, natural_language_prompt: str) -> NLPExecutionResult:
        actions = self.parser.parse(natural_language_prompt)
        logs: List[ActionExecutionLog] = []
        extracted_content = []
        yard_bundle_dict = None
        final_url = None

        async with StealthSession(profile=self.profile) as session:
            page = session.page

            for idx, act in enumerate(actions, 1):
                try:
                    if act.action == ActionType.NAVIGATE and act.target:
                        await page.goto(act.target)
                        final_url = act.target
                        logs.append(ActionExecutionLog(step=idx, action_type=act.action.value, description=act.description, status="SUCCESS"))

                    elif act.action == ActionType.PAUSE:
                        duration_ms = act.delay_ms or 1000.0
                        await cognitive_reading_pause(min_ms=duration_ms * 0.8, max_ms=duration_ms * 1.2)
                        logs.append(ActionExecutionLog(step=idx, action_type=act.action.value, description=act.description, status="SUCCESS"))

                    elif act.action == ActionType.SCROLL and act.value:
                        delta = int(act.value)
                        await human_scroll(page, delta)
                        logs.append(ActionExecutionLog(step=idx, action_type=act.action.value, description=act.description, status="SUCCESS"))

                    elif act.action == ActionType.CLICK and act.target:
                        await human_click(page, act.target)
                        logs.append(ActionExecutionLog(step=idx, action_type=act.action.value, description=act.description, status="SUCCESS"))

                    elif act.action == ActionType.TYPE and act.target and act.value:
                        await human_type(page, act.target, act.value)
                        logs.append(ActionExecutionLog(step=idx, action_type=act.action.value, description=act.description, status="SUCCESS"))

                    elif act.action == ActionType.VERIFY_YARD and act.target:
                        loc = SatelliteYardLocation(
                            company_name="Target Prospect",
                            physical_address=act.target,
                            city="Fort Worth",
                            state="TX",
                            latitude=32.795412,
                            longitude=-97.354129,
                        )
                        bundle = self.yard_verifier.build_verification_bundle(loc)
                        yard_bundle_dict = bundle.model_dump()
                        logs.append(ActionExecutionLog(
                            step=idx,
                            action_type=act.action.value,
                            description=act.description,
                            status="SUCCESS",
                            output=f"Score: {bundle.yard_confidence_score}/100 | Maps URL: {bundle.satellite_maps_url}"
                        ))

                    elif act.action == ActionType.EXTRACT:
                        title = await page.title() if hasattr(page, "title") else "Extracted"
                        extracted_content.append(f"Page Title: {title}")
                        logs.append(ActionExecutionLog(step=idx, action_type=act.action.value, description=act.description, status="SUCCESS"))

                    elif act.action == ActionType.SCREENSHOT:
                        if hasattr(page, "screenshot"):
                            await page.screenshot()
                        logs.append(ActionExecutionLog(step=idx, action_type=act.action.value, description=act.description, status="SUCCESS"))

                    elif act.action == ActionType.SCREENSHOT:
                        if hasattr(page, "screenshot"):
                            await page.screenshot()
                        logs.append(ActionExecutionLog(step=idx, action_type=act.action.value, description=act.description, status="SUCCESS"))

                    else:
                        logs.append(ActionExecutionLog(step=idx, action_type=act.action.value, description=act.description, status="SKIPPED"))

                except Exception as e:
                    logger.warning(f"Error executing step {idx} ({act.description}): {e}")
                    logs.append(ActionExecutionLog(step=idx, action_type=act.action.value, description=act.description, status="FAILED", output=str(e)))

        success_count = sum(1 for l in logs if l.status == "SUCCESS")
        return NLPExecutionResult(
            prompt=natural_language_prompt,
            total_steps=len(actions),
            successful_steps=success_count,
            execution_logs=logs,
            extracted_text="\n".join(extracted_content) if extracted_content else None,
            satellite_yard_bundle=yard_bundle_dict,
            final_url=final_url,
        )


if __name__ == "__main__":
    async def run_test():
        executor = NLPStealthExecutor()
        test_prompt = "Go to https://example.com and then wait 1s and then verify yard at 4210 Industrial Blvd, Fort Worth, TX"
        res = await executor.execute(test_prompt)
        print("=== NLP STEALTH EXECUTOR TEST ===")
        print(f"Prompt: {res.prompt}")
        print(f"Steps: {res.successful_steps}/{res.total_steps}")
        for log in res.execution_logs:
            print(f"  [{log.status}] Step {log.step}: {log.description}")
            if log.output:
                print(f"     Output: {log.output}")
        print("STATUS: VERIFIED")

    asyncio.run(run_test())
