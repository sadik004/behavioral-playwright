"""Automation controllers for mouse, keyboard, and scrolling."""

from behavioral_playwright.automation.keyboard import KeyboardController
from behavioral_playwright.automation.mouse import MouseController
from behavioral_playwright.automation.scroll import ScrollController

__all__ = [
    "KeyboardController",
    "MouseController",
    "ScrollController",
]
