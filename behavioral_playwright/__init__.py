"""Public import surface for the Behavioral-Playwright framework.

Thin, honest re-export of the canonical hardened implementation module
``behavioral_evasion_ten_patches_hardened_v15``. There is exactly ONE
implementation; this package adds a stable import path on top of it:

    from behavioral_playwright import BehavioralPlaywright
    # identical to:
    from behavioral_evasion_ten_patches_hardened_v15 import BehavioralPlaywright

Nothing here wraps, hides, re-implements, or fabricates anything. All public
framework-owned names (classes, exceptions, functions) are re-exported;
foreign names that merely leak into the implementation module's namespace
(typing/pydantic/datetime helpers) are deliberately excluded from __all__.
"""
from behavioral_evasion_ten_patches_hardened_v15 import *  # noqa: F401,F403
import behavioral_evasion_ten_patches_hardened_v15 as _impl

# NOTE: ``AsyncSession`` is deliberately excluded from __all__: when
# curl_cffi is installed it is a FOREIGN name (module curl_cffi.requests),
# when absent it is the implementation's honest loud-failure stub. Exporting
# it would make the public star-import surface environment-dependent.
# TLSJA4Spoofer (the capability that uses it) stays exported either way.
__all__ = [
    _name
    for _name in dir(_impl)
    if _name != "AsyncSession"
    and not _name.startswith("_")
    and getattr(getattr(_impl, _name), "__module__", None) == _impl.__name__
]
