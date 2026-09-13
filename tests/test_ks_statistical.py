#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hardened Statistical KS-Test & Heuristic CreepJS/Sannysoft Audit
Verifies Weibull keystroke distributions, sub-pixel tremor uniformity, and stealth JS patches.
"""
import sys
import os
import numpy as np
from scipy import stats

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from behavioral_evasion_suite.powerhand_master import PowerHandMaster
from behavioral_evasion_suite.keystroke_engine import CognitiveKeystrokeEngine


def test_keystroke_weibull_cadence():
    print("\n[TEST 1] Keystroke Flight-Time Weibull KS-Test...")
    keystroke_delays = []
    engine = CognitiveKeystrokeEngine(base_wpm=65.0, typo_probability=0.05)
    sample_text = "The quick brown fox jumps over the lazy dog. Continuous automated test execution."

    for _ in range(50):
        plan = engine.generate_human_keystroke_plan(sample_text)
        for ev in plan:
            if ev["action"] == "type":
                keystroke_delays.append(ev["delay"])

    keystroke_delays = np.array(keystroke_delays)
    params = stats.weibull_min.fit(keystroke_delays)
    ks_stat, p_val = stats.kstest(keystroke_delays, "weibull_min", args=params)

    print(f"    • Sample Size: {len(keystroke_delays)}")
    print(f"    • Mean Flight Time: {np.mean(keystroke_delays)*1000:.2f} ms")
    print(f"    • KS Stat (D): {ks_stat:.4f}, p-val: {p_val:.4f}")
    assert p_val >= 0.01, f"Keystroke cadence failed Weibull test (p-val: {p_val:.4f})"
    print("    ✅ PASSED: Keystroke cadence fits human Weibull distribution.")


def test_subpixel_tremor_uniformity():
    print("\n[TEST 2] CreepJS Sub-Pixel Tremor Uniformity KS-Test...")
    master = PowerHandMaster(seed=42069)
    tremors = []
    path = master.get_saccade_path((0, 0), (500, 500), steps=100)
    for pt in path:
        tremors.append(pt["x"] % 1.0)

    ks_stat, p_val = stats.kstest(tremors, "uniform")
    print(f"    • Tremor KS Stat (D): {ks_stat:.4f}, p-val: {p_val:.4f}")
    assert p_val >= 0.01, f"Sub-pixel tremor failed uniformity test (p-val: {p_val:.4f})"
    print("    ✅ PASSED: Sub-pixel tremor passes CreepJS Uniformity KS-Test.")


def test_stealth_scripts_heuristics():
    print("\n[TEST 3] Bot.sannysoft & CreepJS Heuristic Checks...")
    master = PowerHandMaster(seed=42069)
    stealth_js = master.get_all_stealth_scripts()

    assert "Notification.permission" in stealth_js, "Missing Notification.permission patch"
    assert "UNMASKED_VENDOR_WEBGL" in stealth_js, "Missing UNMASKED_VENDOR_WEBGL patch"
    assert "webdriver" in stealth_js, "Missing navigator.webdriver mask"
    print("    ✅ PASSED: All critical stealth patches verified in JS payload.")


if __name__ == "__main__":
    print("=" * 70)
    print("📊 RUNNING HARDENED STATISTICAL & HEURISTIC AUDIT")
    print("=" * 70)
    test_keystroke_weibull_cadence()
    test_subpixel_tremor_uniformity()
    test_stealth_scripts_heuristics()
    print("\n" + "=" * 70)
    print("🏆 ALL STATISTICAL AND HEURISTIC AUDITS PASSED!")
    print("=" * 70)
