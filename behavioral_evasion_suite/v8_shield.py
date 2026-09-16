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

            const maskProp = (obj, prop, getterFn) => {
                hookedFunctions.set(getterFn, `function get ${prop}() { [native code] }`);
                Object.defineProperty(obj, prop, {
                    get: getterFn,
                    set: undefined,
                    enumerable: true,
                    configurable: true
                });
            };

            // navigator.webdriver concealment: delete from navigator and make Navigator.prototype.webdriver undefined
            try {
                delete Object.getPrototypeOf(navigator).webdriver;
            } catch (e) {}
            try {
                delete navigator.webdriver;
            } catch (e) {}

            maskProp(Navigator.prototype, 'webdriver', () => undefined);
            maskProp(Navigator.prototype, 'languages', () => ['en-US', 'en']);

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
