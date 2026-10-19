"""CLI package for Behavioral Playwright."""

def main(*args, **kwargs):
    from veil.cli.main import main as _main
    return _main(*args, **kwargs)

__all__ = ["main"]

