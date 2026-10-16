"""Behavioral Playwright module execution entry point (python -m behavioral_playwright)."""

import sys
from behavioral_playwright.cli.main import main

if __name__ == "__main__":
    sys.exit(main())
