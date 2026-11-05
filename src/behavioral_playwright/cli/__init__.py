"""CLI package for Behavioral Playwright."""

def main(*args, **kwargs):
    from behavioral_playwright.cli.main import main as _main
    return _main(*args, **kwargs)

__all__ = ["main"]

