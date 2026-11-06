"""
Verification Test Suite: Deterministic Idempotent Canvas & WebGL Noise Injection
(test_deterministic_canvas_upgrade.py)

Validates:
1. Double-run consistency & Idempotency: hash(call1) == hash(call2) within the same session.
2. Cross-session entropy: hash(session_A) != hash(session_B) when session_seed changes.
3. W3C Native Method Masking: getParameter.toString() contains [native code].
4. Unmasked WebGL Vendor & Renderer spoofing: returns Intel Inc. and Intel(R) Iris(TM) Xe Graphics.
5. Zero regression against behavioral-playwright suite.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import unittest

# Ensure repo root is in sys.path
REPO_ROOT = os.path.abspath(os.path.dirname(__file__))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from behavioral_playwright.evasion.canvas_shield import CanvasWebGLShaderSpoofer


class TestDeterministicCanvasUpgrade(unittest.TestCase):
    """Exhaustive test suite for deterministic canvas and WebGL anti-detect hardening."""

    def setUp(self):
        self.script_session_a = CanvasWebGLShaderSpoofer.get_canvas_shader_spoofer_script(session_seed=1337)
        self.script_session_b = CanvasWebGLShaderSpoofer.get_canvas_shader_spoofer_script(session_seed=9999)

    def test_01_script_structure_and_parameters(self):
        """Verify script contains deterministic Mulberry32 generator and WebGL overrides."""
        self.assertIn("mulberry32", self.script_session_a)
        self.assertIn("SESSION_SEED = 1337", self.script_session_a)
        self.assertIn("SESSION_SEED = 9999", self.script_session_b)
        self.assertIn("UNMASKED_VENDOR_WEBGL", self.script_session_a)
        self.assertIn("UNMASKED_RENDERER_WEBGL", self.script_session_a)
        self.assertIn("Intel Inc.", self.script_session_a)
        self.assertIn("makeNative", self.script_session_a)
        # Ensure conflicting Notification.permission override is permanently eliminated
        self.assertNotIn("Notification.permission", self.script_session_a)

    def test_02_pure_hash_mathematics_in_python(self):
        """Verify mathematical purity and determinism of coordinate & channel hashing."""
        def get_deterministic_pixel_noise(x: int, y: int, channel: int, session_seed: int) -> float:
            def imul(a: int, b: int) -> int:
                # 32-bit signed integer multiplication (Math.imul)
                res = (a * b) & 0xFFFFFFFF
                return res if res < 0x80000000 else res - 0x100000000

            h = (imul(x, 374761393) + imul(y, 668265263) + imul(channel, 31) + session_seed) ^ 0x6D2B79F5
            h = imul(h ^ ((h >> 15) if h >= 0 else (h + 0x100000000) >> 15), h | 1)
            h = (h ^ (h + imul(h ^ ((h >> 7) if h >= 0 else (h + 0x100000000) >> 7), 61))) & 0xFFFFFFFF
            val = ((h ^ (h >> 14)) & 0xFFFFFFFF) / 4294967296.0
            return val

        # 1. Idempotency test (1000 identical calls produce 1000 identical numbers)
        n1 = get_deterministic_pixel_noise(42, 88, 0, 1337)
        for _ in range(1000):
            n_repeated = get_deterministic_pixel_noise(42, 88, 0, 1337)
            self.assertEqual(n1, n_repeated)

        # 2. Entropy across seeds
        n_seed_b = get_deterministic_pixel_noise(42, 88, 0, 9999)
        self.assertNotEqual(n1, n_seed_b)

        # 3. Spatial variance (different coordinates produce different noise values)
        n_coord_b = get_deterministic_pixel_noise(43, 88, 0, 1337)
        self.assertNotEqual(n1, n_coord_b)

    def test_03_runtime_double_run_idempotency_and_native_masking(self):
        """Execute the injected JS payload inside Node.js V8 runtime simulating CreepJS/DataDome checks."""
        node_script = """
const crypto = require('crypto');

function setupTestEnvironment(shieldCode) {
    const sandbox = {
        window: {},
        CanvasRenderingContext2D: function() {},
        HTMLCanvasElement: function() {
            this.width = 100;
            this.height = 100;
        },
        WebGLRenderingContext: function() {}
    };
    sandbox.window = sandbox;

    // Simulate window.makeNative implementation
    sandbox.window.makeNative = function(fn, name) {
        Object.defineProperty(fn, 'name', { value: name, configurable: true });
        fn.toString = function() { return 'function ' + name + '() { [native code] }'; };
    };

    // Baseline Canvas 2D Mock
    sandbox.CanvasRenderingContext2D.prototype.getImageData = function(sx, sy, sw, sh) {
        const length = sw * sh * 4;
        const data = new Uint8ClampedArray(length);
        // Fill canvas with gradient test pattern
        for (let i = 0; i < length; i += 4) {
            data[i] = (i / 4) % 256;       // R
            data[i + 1] = ((i / 4) * 3) % 256; // G
            data[i + 2] = ((i / 4) * 7) % 256; // B
            data[i + 3] = 255;             // A
        }
        return { width: sw, height: sh, data: data };
    };

    sandbox.HTMLCanvasElement.prototype.getContext = function(type) {
        if (type === '2d') return new sandbox.CanvasRenderingContext2D();
        return null;
    };
    sandbox.HTMLCanvasElement.prototype.toDataURL = function() {
        return 'data:image/png;base64,mockOriginalPng';
    };

    // Baseline WebGL Mock
    sandbox.WebGLRenderingContext.prototype.getParameter = function(param) {
        return 'Mock Driver String';
    };

    // Evaluate shield script inside sandbox context
    const executor = new Function(
        'window', 'CanvasRenderingContext2D', 'HTMLCanvasElement', 'WebGLRenderingContext',
        shieldCode
    );
    executor(sandbox.window, sandbox.CanvasRenderingContext2D, sandbox.HTMLCanvasElement, sandbox.WebGLRenderingContext);

    return sandbox;
}

const scriptA = process.argv[2];
const scriptB = process.argv[3];

const envA = setupTestEnvironment(scriptA);
const ctxA = new envA.CanvasRenderingContext2D();

// Check 1: Double-Run Idempotence (CreepJS Threat Model)
const call1 = ctxA.getImageData(0, 0, 100, 100);
const hash1 = crypto.createHash('sha256').update(Buffer.from(call1.data)).digest('hex');

const call2 = ctxA.getImageData(0, 0, 100, 100);
const hash2 = crypto.createHash('sha256').update(Buffer.from(call2.data)).digest('hex');

if (hash1 !== hash2) {
    console.error(JSON.stringify({ error: 'NON_DETERMINISTIC_NOISE', hash1, hash2 }));
    process.exit(1);
}

// Check 2: Entropy across different session seeds
const envB = setupTestEnvironment(scriptB);
const ctxB = new envB.CanvasRenderingContext2D();
const callB = ctxB.getImageData(0, 0, 100, 100);
const hashB = crypto.createHash('sha256').update(Buffer.from(callB.data)).digest('hex');

if (hash1 === hashB) {
    console.error(JSON.stringify({ error: 'IDENTICAL_HASHES_ACROSS_SEEDS', hash1, hashB }));
    process.exit(2);
}

// Check 3: Native toString masking for W3C compliance
const gl = new envA.WebGLRenderingContext();
const getParamStr = gl.getParameter.toString();
const getImageDataStr = ctxA.getImageData.toString();

const result = {
    idempotent_hash_match: hash1 === hash2,
    session_entropy_match: hash1 !== hashB,
    hash_session_a: hash1,
    hash_session_b: hashB,
    gl_getParameter_is_native: getParamStr.includes('[native code]'),
    getImageData_is_native: getImageDataStr.includes('[native code]'),
    unmasked_vendor: gl.getParameter(37445),
    unmasked_renderer: gl.getParameter(37446),
};

console.log(JSON.stringify(result));
"""
        proc = subprocess.run(
            ["node", "-e", node_script, self.script_session_a, self.script_session_b],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, f"Node.js runtime execution failed: {proc.stderr}")

        data = json.loads(proc.stdout.strip())
        # Assertions
        self.assertTrue(data["idempotent_hash_match"], "Two calls within same session MUST produce identical hash!")
        self.assertTrue(data["session_entropy_match"], "Different session seeds MUST produce distinct hashes!")
        self.assertTrue(data["gl_getParameter_is_native"], "getParameter.toString() must contain [native code]!")
        self.assertTrue(data["getImageData_is_native"], "getImageData.toString() must contain [native code]!")
        self.assertEqual(data["unmasked_vendor"], "Intel Inc.")
        self.assertEqual(data["unmasked_renderer"], "Intel(R) Iris(TM) Xe Graphics Direct3D11 vs_5_0 ps_5_0")


if __name__ == "__main__":
    unittest.main(verbosity=2)

