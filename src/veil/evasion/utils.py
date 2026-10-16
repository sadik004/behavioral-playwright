"""
Native JavaScript WeakMap Spoofing Utilities & Log Sanitizer
"""
import sys
import re
import logging

NATIVE_SPOOF_JS = """
(() => {
    const originalToString = Function.prototype.toString;
    const nativeRegistry = new WeakMap();

    window.makeNative = (fn, name) => {
        // Set properties to mirror real Chromium functions
        Object.defineProperty(fn, 'name', {
            value: name,
            configurable: true,
            enumerable: false,
            writable: false
        });

        Object.defineProperty(fn, 'length', {
            value: 0,
            configurable: true,
            enumerable: false,
            writable: false
        });

        nativeRegistry.set(fn, `function ${name}() { [native code] }`);
        return fn;
    };

    // Override Function.prototype.toString natively
    const customToString = function() {
        if (nativeRegistry.has(this)) {
            return nativeRegistry.get(this);
        }
        if (this === Function.prototype.toString) {
            return 'function toString() { [native code] }';
        }
        return originalToString.apply(this, arguments);
    };

    nativeRegistry.set(customToString, 'function toString() { [native code] }');

    Object.defineProperty(Function.prototype, 'toString', {
        value: customToString,
        writable: true,
        configurable: true,
        enumerable: false
    });
})();
"""


class SanitizedLogFormatter(logging.Formatter):
    """
    Scrubs plaintext proxy passwords and sensitive bearer tokens from log messages
    before they are printed to stdout or saved to disk.
    """
    PROXY_CRED_REGEX = re.compile(r"([a-zA-Z0-9+.-]+://)([^:]+):([^@]+)@")
    AUTH_HEADER_REGEX = re.compile(r"(Authorization:\s*)(Bearer\s+[a-zA-Z0-9_\-\.]+)", re.IGNORECASE)

    def format(self, record: logging.LogRecord) -> str:
        original_msg = super().format(record)
        sanitized = self.PROXY_CRED_REGEX.sub(r"\1\2:******@", original_msg)
        sanitized = self.AUTH_HEADER_REGEX.sub(r"\1Bearer *****", sanitized)
        return sanitized


def setup_sanitized_logger(name: str = "BehavioralPlaywright.Enterprise") -> logging.Logger:
    """Configures and returns a logger with the SanitizedLogFormatter."""
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(SanitizedLogFormatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.INFO)
    return logging.getLogger(name)
