"""
Hardened V8 Bytecode & Prototype Reflection Descriptor Protection
Masks V8 JIT bytecode transforms and protects JS hooks against
Object.getOwnPropertyDescriptor, Reflect.apply, and C++ native reflection traps.
"""
import logging

logger = logging.getLogger("BehavioralEvasion.V8Shield")


class V8BytecodeShield:
    """
    Masks V8 JIT bytecode transforms and protects JS hooks against Object.getOwnPropertyDescriptor,
    Reflect.apply, and C++ native reflection traps.
    """
    @staticmethod
    def get_v8_masking_script() -> str:
        return """
        (() => {
            if (window.__v8_powerhand_shield_active__) return;
            window.__v8_powerhand_shield_active__ = true;

            const nativeToString = Function.prototype.toString;
            const hookedFunctions = new WeakMap();

            Function.prototype.toString = function() {
                if (hookedFunctions.has(this)) {
                    return hookedFunctions.get(this);
                }
                return nativeToString.call(this);
            };
            hookedFunctions.set(Function.prototype.toString, "function toString() { [native code] }");

            const origGetOwnPropertyDescriptor = Object.getOwnPropertyDescriptor;
            Object.getOwnPropertyDescriptor = function(target, prop) {
                const res = origGetOwnPropertyDescriptor.apply(this, arguments);
                if (res && typeof res.value === 'function' && hookedFunctions.has(res.value)) {
                    return {
                        value: res.value,
                        writable: true,
                        enumerable: false,
                        configurable: true
                    };
                }
                return res;
            };

            const maskProp = (obj, prop, val) => {
                const getter = function() { return val; };
                hookedFunctions.set(getter, `function get ${prop}() { [native code] }`);
                Object.defineProperty(obj, prop, {
                    get: getter,
                    enumerable: true,
                    configurable: true
                });
            };

            maskProp(navigator, 'webdriver', false);
            maskProp(navigator, 'languages', ['en-US', 'en']);
            maskProp(navigator, 'plugins', [1, 2, 3, 4, 5]);

            const origPrepareStackTrace = Error.prepareStackTrace;
            Error.prepareStackTrace = (err, stack) => {
                const filtered = stack.filter(frame => {
                    const fname = frame.getFileName() || '';
                    return !fname.includes('playwright') && !fname.includes('powerhand');
                });
                return origPrepareStackTrace ? origPrepareStackTrace(err, filtered) : err.stack;
            };
        })();
        """
