"""Functional Validation: Real Input Automation & Interactions (Click, Type, Scroll).
Tests observable DOM state mutations from biomechanical mouse, keyboard, and scroll controllers.
"""

from __future__ import annotations

import pytest
from behavioral_playwright.facade import BP


INTERACTION_HTML = """<!DOCTYPE html>
<html>
<head><title>Interactions Test</title></head>
<body>
    <div style="padding: 20px;">
        <button id="counter-btn" onclick="
            var c = document.getElementById('count');
            c.innerText = parseInt(c.innerText) + 1;
        ">Click Me</button>
        <span id="count">0</span>
    </div>

    <div style="padding: 20px;">
        <label for="username">Username</label>
        <input id="username" name="username" type="text" placeholder="Your username" />
    </div>

    <div style="padding: 20px;">
        <input placeholder="Enter your email" type="email" />
    </div>

    <div style="height: 2500px; padding: 20px;">
        <p>Tall spacer content...</p>
    </div>
    
    <div id="footer-element">Page Footer</div>
</body>
</html>
"""


@pytest.mark.asyncio
async def test_mouse_click_real_state_mutation():
    """Verify bp.click() triggers real DOM event listeners and mutates innerText."""
    async with BP() as bp:
        await bp.open(f"data:text/html,{INTERACTION_HTML}")
        
        # Initial state
        initial_val = await bp.page.evaluate("() => document.getElementById('count').innerText")
        assert initial_val == "0"
        
        # First click
        await bp.click("#counter-btn")
        val_after_1 = await bp.page.evaluate("() => document.getElementById('count').innerText")
        assert val_after_1 == "1"
        
        # Second click
        await bp.click("#counter-btn")
        val_after_2 = await bp.page.evaluate("() => document.getElementById('count').innerText")
        assert val_after_2 == "2"


@pytest.mark.asyncio
async def test_keyboard_type_real_value_mutation():
    """Verify bp.type() fills text into input element and mutates DOM value attribute."""
    async with BP() as bp:
        await bp.open(f"data:text/html,{INTERACTION_HTML}")
        
        test_text = "Alice_Automation_User"
        await bp.type("#username", test_text)
        
        real_value = await bp.page.evaluate("() => document.getElementById('username').value")
        assert real_value == test_text


@pytest.mark.asyncio
async def test_type_healed_on_semantic_target():
    """Verify page.type_healed resolves target by placeholder and inputs text."""
    async with BP() as bp:
        await bp.open(f"data:text/html,{INTERACTION_HTML}")
        
        test_email = "test@company.org"
        res = await bp.page.type_healed("Enter your email", test_email)
        assert res.success is True
        
        # Read back value from input with placeholder
        real_value = await bp.page.evaluate(
            "() => document.querySelector('input[placeholder=\"Enter your email\"]').value"
        )
        assert real_value == test_email


@pytest.mark.asyncio
async def test_scroll_controller_viewport_mutation():
    """Verify scroll controller changes window scrollY position in the real browser."""
    async with BP() as bp:
        await bp.open(f"data:text/html,{INTERACTION_HTML}")
        
        # Initial scroll pos
        initial_y = await bp.page.evaluate("() => window.scrollY")
        assert initial_y == 0
        
        # Scroll down 600px
        await bp.page.scroll.down(600, smooth=False)
        scrolled_y = await bp.page.evaluate("() => window.scrollY")
        assert scrolled_y >= 500
        
        # Scroll back to top
        await bp.page.scroll.to_top(smooth=False)
        top_y = await bp.page.evaluate("() => window.scrollY")
        assert top_y == 0
