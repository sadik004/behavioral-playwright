"""Canonical Release Smoke Demonstration: Behavioral Playwright Framework.

Demonstrates the unified 7-pillar workflow:
    Browser -> PageSession -> Resolve -> Interact -> Extract -> Map -> Verify -> Workflow -> Final result
"""

from __future__ import annotations

import asyncio
from decimal import Decimal
from urllib.parse import quote

from behavioral_playwright import (
    ActionType,
    AutomationConfig,
    BrowserConfig,
    BrowserSession,
    WorkflowDefinition,
    WorkflowOrchestrator,
    WorkflowResult,
    WorkflowStatus,
    WorkflowStep,
)
from behavioral_playwright.extraction.normalizer import parse_price
from behavioral_playwright.mapping.schema_mapper import PageSchemaMapper

DEMO_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>Canonical Release Smoke Test</title>
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": "Behavioral Playwright Pro",
        "price": "499.00"
    }
    </script>
</head>
<body>
    <h1 id="title">Enterprise Automation Suite</h1>
    <div id="status">INITIAL</div>
    <input id="target-input" type="text" placeholder="Command input" />
    <button id="exec-btn" onclick="
        var txt = document.getElementById('target-input').value;
        document.getElementById('status').innerText = 'EXECUTED: ' + txt;
    ">Execute</button>
    <div id="price-tag">$499.00</div>
</body>
</html>
"""


async def main() -> None:
    print("[1/6] Launching isolated BrowserSession...")
    config = AutomationConfig(browser=BrowserConfig(headless=True))
    data_url = f"data:text/html;charset=utf-8,{quote(DEMO_HTML)}"

    async with BrowserSession(config=config) as session:
        # 1. PageSession
        print("[2/6] Spawning PageSession and navigating...")
        page = await session.new_page()
        await page.goto(data_url)

        # 2. Resolve target element with self-healing cascade
        print("[3/6] Resolving UI target through self-healing resolver...")
        res = await page.resolve("#exec-btn")
        assert res.success is True, "Failed to resolve #exec-btn"
        print(f"       Resolved selector: {res.selector} (strategy: {res.strategy})")

        # 3. Plan & Execute Workflow through Orchestrator
        print("[4/6] Executing orchestrated multi-step workflow...")
        wf = WorkflowDefinition.create(
            session_id=page.session_id,
            steps=[
                WorkflowStep.create(
                    step_id="step_type",
                    action="type",
                    action_type=ActionType.DOM_INTERACTION,
                    input_data={"selector": "#target-input", "text": "CANONICAL_SMOKE_PASS"},
                ),
                WorkflowStep.create(
                    step_id="step_click",
                    action="click",
                    action_type=ActionType.STATE_MUTATION,
                    input_data={"selector": "#exec-btn"},
                ),
                WorkflowStep.create(
                    step_id="step_extract",
                    action="extract",
                    action_type=ActionType.DATA_EXTRACTION,
                    input_data={"selector": "#status", "target": "text"},
                ),
            ],
            name="canonical_smoke_workflow",
            require_verification=True,
        )

        orchestrator = WorkflowOrchestrator()
        result: WorkflowResult = await orchestrator.execute_workflow(wf, session=page)
        assert result.status == WorkflowStatus.COMPLETED
        assert result.is_verified is True
        print(f"       Workflow execution verified: {result.is_verified} (status: {result.status})")

        # 4. Extract and Normalize Data
        print("[5/6] Extracting and normalizing financial precision data...")
        price_raw = await page.raw_page.inner_text("#price-tag")
        normalized_price = parse_price(price_raw)
        assert normalized_price == Decimal("499.00"), f"Unexpected price: {normalized_price}"
        print(f"       Extracted & normalized price: {normalized_price} (type: {type(normalized_price).__name__})")

        # 5. Semantic Page Intelligence & Schema Mapping
        print("[6/6] Mapping page intelligence schema (DOM > JSON-LD)...")
        mapper = PageSchemaMapper(confidence_threshold=0.50)
        mapped = await mapper.map_schema(page.raw_page, {"name": str, "price": Decimal})
        assert mapped.success is True
        print(f"       Mapped product: {mapped.data.get('name')}")
        print(f"       Mapped price: {mapped.data.get('price')}")

        print("\n============================================================")
        print("CANONICAL RELEASE SMOKE TEST COMPLETED SUCCESSFULLY (EXIT 0)")
        print("============================================================")


if __name__ == "__main__":
    asyncio.run(main())
