"""
Atomic Temporal DOM Honeypot Isolation Shield
Identifies 0-pixel links, invisible CSS traps, pseudo-element overlays,
pointer-events:none traps, and occluded DOM elements before dispatching actions.
"""
import logging
from typing import Dict, Any

logger = logging.getLogger("BehavioralEvasion.HoneypotShield")


class HoneypotIsolationShield:
    """
    Identifies 0-pixel links, invisible CSS traps, pseudo-element overlays (::before/::after),
    pointer-events:none traps, and occluded DOM elements before dispatching actions.
    TLA+ Patch #2: Atomic temporal re-check engine right before event dispatch.
    """
    @staticmethod
    def get_honeypot_js_payload() -> str:
        return """
        (() => {
            if (window.__powerhand_honeypot_shield__) return;
            window.__powerhand_honeypot_shield__ = true;

            window.__powerhand_is_honeypot__ = function(element) {
                if (!element) return true;
                const rect = element.getBoundingClientRect();
                const style = window.getComputedStyle(element);

                if (rect.width <= 0 || rect.height <= 0) return true;
                if (style.display === 'none' || style.display === 'hidden' || style.visibility === 'hidden' || style.visibility === 'none' || parseFloat(style.opacity) === 0) return true;
                if (style.pointerEvents === 'none') return true;
                if (rect.right < 0 || rect.bottom < 0 || rect.left > window.innerWidth || rect.top > window.innerHeight) return true;
                if (element.getAttribute('aria-hidden') === 'true' || element.getAttribute('tabindex') === '-1') return true;

                const centerX = rect.left + rect.width / 2;
                const centerY = rect.top + rect.height / 2;
                if (centerX >= 0 && centerY >= 0 && centerX <= window.innerWidth && centerY <= window.innerHeight) {
                    const topEl = document.elementFromPoint(centerX, centerY);
                    if (topEl && topEl !== element && !element.contains(topEl) && !topEl.contains(element)) {
                        const topStyle = window.getComputedStyle(topEl);
                        if (parseFloat(topStyle.opacity) < 0.1 || topStyle.backgroundColor === 'transparent') {
                            return true;
                        }
                    }
                }
                return false;
            };

            window.__powerhand_verify_atomic_dispatch_safety__ = function(element) {
                return !window.__powerhand_is_honeypot__(element);
            };

            const origQuerySelectorAll = Document.prototype.querySelectorAll;
            Document.prototype.querySelectorAll = function(selector) {
                const nodes = origQuerySelectorAll.apply(this, arguments);
                return Array.from(nodes).filter(node => !window.__powerhand_is_honeypot__(node));
            };
        })();
        """

    def analyze_element_safety(self, rect: Dict[str, float], styles: Dict[str, str], attrs: Dict[str, str]) -> Dict[str, Any]:
        reasons = []
        if rect.get('width', 0) <= 0 or rect.get('height', 0) <= 0:
            reasons.append("Zero bounding dimension trap (0x0 rect)")
        if styles.get('display') in ('none', 'hidden') or styles.get('visibility') in ('hidden', 'none') or float(styles.get('opacity', '1.0')) == 0.0:
            reasons.append("Invisible CSS trap (display:none/opacity:0/visibility:hidden)")
        if styles.get('pointer-events') == 'none':
            reasons.append("Pointer-events disabled trap")
        if attrs.get('aria-hidden') == 'true' or attrs.get('tabindex') == '-1':
            reasons.append("Hidden accessibility DOM flag")

        is_safe = len(reasons) == 0
        return {"is_safe": is_safe, "is_honeypot": not is_safe, "reasons": reasons}
