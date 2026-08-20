"""
Unified Self-Test QA Suite maintaining backward-compatibility with SelfTestSuite.run_all_tests().
"""

import asyncio
import json
import logging
import math
import os
from typing import List

from behavioral_playwright import (
    ActionValidator,
    AffineCoordinateMapper,
    AIConfig,
    AmbientSensorSpoofEngine,
    AudioFingerprintDeflectionEngine,
    AutomationConfig,
    BehavioralHumanizer,
    BezierTrajectoryGenerator,
    BiometricLivenessSynthesizer,
    BrowserConfig,
    BrowserProviderFactory,
    CanvasGridMappingDriver,
    CircuitBreaker,
    CircuitState,
    ClickConfig,
    CognitiveInterferenceModel,
    DeterministicRandomSource,
    EbpfTcpSpoofBridge,
    EnvironmentalTrustEngine,
    ExploitPoCExporter,
    ExtensionCanaryShieldEngine,
    FontMetricCalibrationEngine,
    HardwareAttestationRelay,
    JA4TlsHandshakeEmulator,
    JSEngineDivergenceEmulator,
    KeyboardConfig,
    LinguisticKeystrokeDynamics,
    LLMProvider,
    LLMReasoning,
    LocalOSInputBridge,
    LorenzAttractorGenerator,
    MarkovLoopDetector,
    MFAOtpPollingBridge,
    MockChallengeSolver,
    MockPage,
    MouseConfig,
    MultimodalTimingCorrelation,
    NavigationManager,
    NetworkConfig,
    SelfHealingSelectorEngine,
    SystemClock,
    VirtualCpuCacheTimingJitter,
    VirtualTestClock,
    VisualElement,
    WebWorkerEvasionEngine,
)

logger = logging.getLogger("BehavioralAutomation.Tests")


class SelfTestSuite:
    """Rigorously validates mathematical boundaries, keyboard typing accuracy, and distribution bounds."""

    @classmethod
    async def run_all_tests(cls) -> bool:
        logger.info("=== STARTING MODULAR MATHEMATICAL SELF-TEST SUITE ===")
        try:
            cls.test_smoothstep_boundaries()
            cls.test_bezier_trajectory_envelope()
            await cls.test_keyboard_human_typing_reconstruction()
            cls.test_click_timing_statistical_distribution()
            await cls.test_circuit_breaker_state_transitions()
            cls.test_canvas_grid_mapping()
            cls.test_markov_loop_detector()
            cls.test_affine_coordinate_mapping()
            cls.test_lorenz_attractor_chaos_generation()
            cls.test_human_idle_drift_neuromuscular()
            cls.test_self_healing_selector_engine()
            cls.test_fatigue_modeling_scaling()
            cls.test_qwerty_kde_typing_delay()
            cls.test_ebpf_tcp_spoofing()
            cls.test_linguistic_keystroke_dynamics()
            cls.test_biometric_liveness_synthesizer()
            cls.test_hardware_attestation_relay()
            await cls.test_mouse_sequence_chaining()
            await cls.test_inertial_scroll_dynamic()
            cls.test_ambient_sensor_noise()
            cls.test_acoustic_waveform_jitter()
            cls.test_font_metric_calibration()
            cls.test_extension_canary_shield()
            cls.test_cognitive_interference_stroop()
            cls.test_environmental_trust_profile()
            cls.test_ja4_tls_emulation()
            await cls.test_mfa_otp_polling()
            cls.test_local_os_input_dispatch()
            await cls.test_challenge_solver_bridge()
            cls.test_exploit_poc_exporter()
            cls.test_js_engine_divergence()
            cls.test_worker_telemetry_isolation()
            cls.test_vcpu_cache_timing()
            await cls.test_ai_cv_ocr()
            cls.test_ai_coordinate_mapping()
            await cls.test_ai_llm_mocking()
            await cls.test_ai_llm_malformed_response()
            await cls.test_ai_timeout_retry()
            await cls.test_ai_selector_self_healing()
            cls.test_ai_confidence_validation()
            await cls.test_ai_visual_verification()
            await cls.test_complete_ai_mock_e2e_pipeline()
            cls.test_multimodal_timing_correlation()
            await cls.test_real_or_mock_integration_pipeline()
            logger.info("=== ALL MODULAR SELF-TESTS COMPLETED SUCCESSFULLY! ===")
            return True
        except AssertionError as ae:
            logger.error(f"=== SELF-TEST FAILURE DETECTED: {ae} ===")
            return False
        except Exception as ex:
            logger.critical(f"=== UNEXPECTED SYSTEM ERROR DURING UNIT-TESTS: {ex} ===", exc_info=True)
            return False

    @staticmethod
    def test_smoothstep_boundaries() -> None:
        assert BezierTrajectoryGenerator.smoothstep(0.0) == 0.0
        assert BezierTrajectoryGenerator.smoothstep(1.0) == 1.0
        assert BezierTrajectoryGenerator.smoothstep(0.5) == 0.5
        assert BezierTrajectoryGenerator.smoothstep(-0.5) == 0.0
        assert BezierTrajectoryGenerator.smoothstep(1.5) == 1.0

    @staticmethod
    def test_bezier_trajectory_envelope() -> None:
        start = (10.0, 20.0)
        end = (500.0, 400.0)
        config = MouseConfig()
        rng = DeterministicRandomSource(42)
        path = BezierTrajectoryGenerator.generate_path(start, end, 50, config, rng)
        assert len(path) == 50
        assert path[0][0] == start[0] and path[0][1] == start[1]
        assert abs(path[-1][0] - end[0]) < 1e-4 and abs(path[-1][1] - end[1]) < 1e-4
        for x, y in path:
            assert not math.isnan(x) and not math.isinf(x)
            assert not math.isnan(y) and not math.isinf(y)

    @staticmethod
    async def test_keyboard_human_typing_reconstruction() -> None:
        mock_page = MockPage()
        test_kb_cfg = KeyboardConfig(
            mistake_probability=1.0,
            avg_delay_mean=0.001,
            avg_delay_std=0.0,
            min_delay=0.001,
            correction_delay_min=0.001,
            correction_delay_max=0.001,
        )
        test_cfg = AutomationConfig(keyboard=test_kb_cfg)
        rng = DeterministicRandomSource(42)
        clock = VirtualTestClock()
        humanizer = BehavioralHumanizer(mock_page, test_cfg, rng=rng, clock=clock)
        await humanizer.human_type("#test-input", "VerifyMe")
        reconstructed = mock_page.keyboard.reconstruct_typed_output()
        assert reconstructed == "VerifyMe"

    @staticmethod
    def test_click_timing_statistical_distribution() -> None:
        rng = DeterministicRandomSource(42)
        config = ClickConfig()
        samples: List[float] = []
        for _ in range(1000):
            val = rng.gauss(config.duration_mean, config.duration_std)
            samples.append(max(config.duration_min, val))
        sample_mean = sum(samples) / len(samples)
        sample_variance = sum((x - sample_mean) ** 2 for x in samples) / (len(samples) - 1)
        sample_std = math.sqrt(sample_variance)
        assert abs(sample_mean - config.duration_mean) < 0.003
        assert abs(sample_std - config.duration_std) < 0.002
        for duration in samples:
            assert duration >= config.duration_min

    @staticmethod
    async def test_circuit_breaker_state_transitions() -> None:
        clock = VirtualTestClock()
        cb = CircuitBreaker(failure_threshold=2, recovery_cooldown=1.0, clock=clock)
        nav_cfg = AutomationConfig(network=NetworkConfig(initial_delay=0.001, backoff_factor=1.0))
        manager = NavigationManager(nav_cfg, cb)
        mock_page = MockPage()

        assert cb.state == CircuitState.CLOSED
        assert cb.allow_request() is True

        mock_page.should_fail_goto = True
        await manager.safe_goto(mock_page, "invalid_protocol_url")
        await manager.safe_goto(mock_page, "invalid_protocol_url")
        assert cb.state == CircuitState.OPEN
        assert cb.allow_request() is False

        await clock.sleep(1.2)
        assert cb.allow_request() is True
        assert cb.state == CircuitState.HALF_OPEN

        mock_page.should_fail_goto = False
        success = await manager.safe_goto(mock_page, "https://valid-url.com")
        assert success is True
        assert cb.state == CircuitState.CLOSED

    @staticmethod
    def test_canvas_grid_mapping() -> None:
        canvas_box = {"x": 150.0, "y": 200.0, "width": 400.0, "height": 300.0}
        abs_x, abs_y = CanvasGridMappingDriver.map_canvas_coordinates(canvas_box, 0.5, 0.5)
        assert abs_x == 350.0
        assert abs_y == 350.0

    @staticmethod
    def test_markov_loop_detector() -> None:
        detector = MarkovLoopDetector(history_limit=8, entropy_threshold=1.15)
        for i in range(5):
            detector.record_transition(f"https://target.com/page/{i}")
        assert not detector.is_loop_detected()
        for _ in range(6):
            detector.record_transition("https://target.com/page/loop-a")
            detector.record_transition("https://target.com/page/loop-b")
        assert detector.is_loop_detected()

    @staticmethod
    def test_affine_coordinate_mapping() -> None:
        mapper = AffineCoordinateMapper(matrix_a=1.5, matrix_tx=100.0, matrix_d=1.5, matrix_ty=150.0)
        sx, sy = mapper.map_viewport_to_screen(10.0, 20.0)
        assert sx == 115.0
        assert sy == 180.0

    @staticmethod
    def test_lorenz_attractor_chaos_generation() -> None:
        lorenz = LorenzAttractorGenerator(sigma=10.0, rho=28.0, beta=2.6667, dt=0.001)
        x1, y1, _ = lorenz.x, lorenz.y, lorenz.z
        x2, y2, _ = lorenz.next_step()
        assert x1 != x2
        assert y1 != y2

    @staticmethod
    def test_human_idle_drift_neuromuscular() -> None:
        rng = DeterministicRandomSource(42)
        assert rng.gauss(0.0, 0.4) != 0.0

    @staticmethod
    def test_self_healing_selector_engine() -> None:
        healer = SelfHealingSelectorEngine()
        candidates = ["#btn-login", "input[name='login']", "#submit-button"]
        healed = healer.heal_selector("#login", candidates)
        assert healed == "#btn-login"

    @staticmethod
    def test_fatigue_modeling_scaling() -> None:
        config = AutomationConfig()
        mock_page = MockPage()
        humanizer = BehavioralHumanizer(mock_page, config, rng=DeterministicRandomSource(42), clock=VirtualTestClock())
        assert humanizer.get_fatigue_multiplier() == 1.0
        humanizer.session_start -= 1800.0
        assert humanizer.get_fatigue_multiplier() == 1.35

    @staticmethod
    def test_qwerty_kde_typing_delay() -> None:
        dist_qp = BehavioralHumanizer.get_qwerty_key_distance("q", "p")
        dist_qw = BehavioralHumanizer.get_qwerty_key_distance("q", "w")
        assert dist_qp > dist_qw
        assert BehavioralHumanizer.get_qwerty_key_distance("q", "$") == 2.5

    @staticmethod
    def test_ebpf_tcp_spoofing() -> None:
        bridge = EbpfTcpSpoofBridge(target_os="Windows")
        params = bridge.enable_tcp_option_spoofing()
        assert params["ttl"] == 128
        assert "TS" in params["tcp_options"]

    @staticmethod
    def test_linguistic_keystroke_dynamics() -> None:
        dynamics = LinguisticKeystrokeDynamics()
        assert dynamics.calculate_linguistic_factor("t", "h") == 0.70
        assert dynamics.calculate_linguistic_factor("h", "e", "t") == 0.55
        assert dynamics.calculate_linguistic_factor("q", "x") == 1.0

    @staticmethod
    def test_biometric_liveness_synthesizer() -> None:
        synth = BiometricLivenessSynthesizer()
        gx, gy = synth.update_gaze_gimbal(960.0, 540.0)
        assert gx == 0.5
        assert gy == 0.5

    @staticmethod
    def test_hardware_attestation_relay() -> None:
        relay = HardwareAttestationRelay()
        response = relay.relay_cryptographic_sign("assertion_challenge_xyz", "https://bank.com")
        assert "sig_assertion" in response["signature"]
        assert response["authenticator_data"] == "auth_data_registered_aged_device"

    @staticmethod
    async def test_mouse_sequence_chaining() -> None:
        config = AutomationConfig()
        mock_page = MockPage()
        humanizer = BehavioralHumanizer(mock_page, config, rng=DeterministicRandomSource(42), clock=VirtualTestClock())
        await humanizer.move_mouse_sequence([(100.0, 150.0), (200.0, 300.0)])
        assert humanizer.current_position == (200.0, 300.0)

    @staticmethod
    async def test_inertial_scroll_dynamic() -> None:
        config = AutomationConfig()
        mock_page = MockPage()
        humanizer = BehavioralHumanizer(mock_page, config, rng=DeterministicRandomSource(42), clock=VirtualTestClock())
        await humanizer.human_scroll(50.0)
        assert len(mock_page.mouse.wheels) > 0
        total_scroll = sum(w[1] for w in mock_page.mouse.wheels)
        assert abs(total_scroll - 50.0) < 1.0

    @staticmethod
    def test_ambient_sensor_noise() -> None:
        engine = AmbientSensorSpoofEngine(initial_battery_percent=80.0)
        res = engine.simulate_sensor_noise(elapsed_seconds=120.0)
        assert res["battery_level"] < 0.80

    @staticmethod
    def test_acoustic_waveform_jitter() -> None:
        engine = AudioFingerprintDeflectionEngine()
        assert engine.deflect_audio_fingerprint() is True

    @staticmethod
    def test_font_metric_calibration() -> None:
        engine = FontMetricCalibrationEngine()
        assert engine.calibrate_font_metrics() is True

    @staticmethod
    def test_extension_canary_shield() -> None:
        engine = ExtensionCanaryShieldEngine()
        assert engine.sanitize_extension_probes() is True

    @staticmethod
    def test_cognitive_interference_stroop() -> None:
        assert CognitiveInterferenceModel.calculate_stroop_penalty("RED CANCEL BUTTON") == 0.35
        assert CognitiveInterferenceModel.calculate_stroop_penalty("Normal submit") == 0.0

    @staticmethod
    def test_environmental_trust_profile() -> None:
        engine = EnvironmentalTrustEngine("./stealth_profile")
        state = engine.generate_legitimate_profile_state()
        assert state["trust_score"] == 0.98
        assert len(state["visited_warmup_nodes"]) == 4

    @staticmethod
    def test_ja4_tls_emulation() -> None:
        conf = JA4TlsHandshakeEmulator.configure_tls_session()
        assert conf["ja4_fingerprint"] == "t13d1516h2_8a2d39234"
        assert conf["http2_settings"]["ENABLE_PUSH"] == 0

    @staticmethod
    async def test_mfa_otp_polling() -> None:
        bridge = MFAOtpPollingBridge()
        code_val = await bridge.poll_one_time_password("Google Auth")
        assert code_val == "729481"

    @staticmethod
    def test_local_os_input_dispatch() -> None:
        mapper = AffineCoordinateMapper(matrix_a=1.0, matrix_tx=120.0, matrix_d=1.0, matrix_ty=150.0)
        bridge = LocalOSInputBridge(mapper)
        assert bridge.dispatch_os_level_click(10.0, 20.0) is True

    @staticmethod
    async def test_challenge_solver_bridge() -> None:
        solver = MockChallengeSolver(clock=VirtualTestClock(), rng=DeterministicRandomSource(42))
        mock_page = MockPage()
        assert await solver.solve(mock_page, "Cloudflare Turnstile") is True

    @staticmethod
    def test_exploit_poc_exporter() -> None:
        poc = ExploitPoCExporter.export_poc(
            url="https://target.com/api/v1/user",
            method="POST",
            headers={"Content-Type": "application/json", "Authorization": "Bearer admin123"},
            cookies={"session": "active"},
            payload='{"id": 42}',
            output_path="./scratch/test_poc_export.py",
        )
        assert "requests.request" in poc
        assert "admin123" in poc

    @staticmethod
    def test_js_engine_divergence() -> None:
        emu = JSEngineDivergenceEmulator(target_engine="SpiderMonkey")
        config = emu.configure_engine_divergence()
        assert config["max_call_stack_exceeded_msg"] == "too much recursion"

    @staticmethod
    def test_worker_telemetry_isolation() -> None:
        engine = WebWorkerEvasionEngine(is_enabled=True)
        assert engine.shield_worker_telemetry() is True

    @staticmethod
    def test_vcpu_cache_timing() -> None:
        jitter_engine = VirtualCpuCacheTimingJitter(is_virtualized=True)
        assert jitter_engine.calculate_timing_jitter(12.34) >= 12.34

    @staticmethod
    def test_multimodal_timing_correlation() -> None:
        correlation = MultimodalTimingCorrelation(base_delay_ms=200.0)
        rng = DeterministicRandomSource(42)
        assert correlation.calculate_interaction_gap(rng, 1.0) > 0.0

    @staticmethod
    async def test_ai_cv_ocr() -> None:
        config = AutomationConfig(ai=AIConfig(enabled=True, ocr_cv_enabled=True))
        mock_page = MockPage()
        humanizer = BehavioralHumanizer(mock_page, config, rng=DeterministicRandomSource(42), clock=VirtualTestClock())
        assert humanizer.vision_engine is not None
        elements = await humanizer.vision_engine.capture_and_analyze(mock_page)
        assert len(elements) > 0
        assert elements[0].confidence > 0.80

    @staticmethod
    def test_ai_coordinate_mapping() -> None:
        ve = VisualElement(
            text="ClickMe", bounding_box={"x": 150.0, "y": 250.0, "width": 100.0, "height": 50.0}, confidence=0.99
        )
        cx = ve.bounding_box["x"] + ve.bounding_box["width"] / 2.0
        cy = ve.bounding_box["y"] + ve.bounding_box["height"] / 2.0
        assert cx == 200.0
        assert cy == 275.0

    @staticmethod
    async def test_ai_llm_mocking() -> None:
        config = AutomationConfig(ai=AIConfig(enabled=True))
        os.environ["STEALTH_TEST_MODE"] = "true"
        provider = LLMProvider(config)
        res_login = await provider.generate_response("Reason about login button")
        parsed = json.loads(res_login)
        assert parsed["action"] == "click"
        assert parsed["confidence"] == 0.95

    @staticmethod
    async def test_ai_llm_malformed_response() -> None:
        config = AutomationConfig(ai=AIConfig(enabled=True))
        os.environ["STEALTH_TEST_MODE"] = "true"
        provider = LLMProvider(config)
        reasoning = LLMReasoning(provider)
        res = await reasoning.propose_healing_action("btn", "<div>", [])
        assert "selector" in res

    @staticmethod
    async def test_ai_timeout_retry() -> None:
        config = AutomationConfig(ai=AIConfig(enabled=True, retry=1, timeout=0.1))
        os.environ["STEALTH_LLM_API_KEY"] = "dummy_invalid_key_to_force"
        os.environ["STEALTH_LLM_BASE_URL"] = "http://127.0.0.1:9999/invalid"
        os.environ["STEALTH_TEST_MODE"] = "false"
        provider = LLMProvider(config)
        res = await provider.generate_response("test_retry")
        assert len(res) > 0
        parsed = json.loads(res)
        assert "action" in parsed
        os.environ["STEALTH_TEST_MODE"] = "true"
        os.environ.pop("STEALTH_LLM_API_KEY", None)

    @staticmethod
    async def test_ai_selector_self_healing() -> None:
        config = AutomationConfig(ai=AIConfig(enabled=True, self_healing_enabled=True, ocr_cv_enabled=True))
        mock_page = MockPage()
        humanizer = BehavioralHumanizer(mock_page, config, rng=DeterministicRandomSource(42), clock=VirtualTestClock())
        assert humanizer.ai_resolver is not None

        resolved_l1 = await humanizer.ai_resolver.resolve_element(mock_page, "#btn-login-dynamic")
        assert resolved_l1 is not None
        assert resolved_l1["strategy"] == "deterministic_levenshtein"
        assert resolved_l1["selector"] == "#btn-login"

        resolved_l2 = await humanizer.ai_resolver.resolve_element(
            mock_page, "completely_different_selector_that_fails_levenshtein_but_contains_textbox"
        )
        assert resolved_l2 is not None
        assert resolved_l2["strategy"] == "dom_accessibility"
        assert resolved_l2["selector"] == "#text-input"

    @staticmethod
    def test_ai_confidence_validation() -> None:
        config = AutomationConfig(ai=AIConfig(enabled=True, confidence_threshold=0.80))
        validator = ActionValidator(config)
        low_confidence = {"selector": "#btn", "confidence": 0.50, "strategy": "llm_reasoning"}
        high_confidence = {"selector": "#btn", "confidence": 0.90, "strategy": "llm_reasoning"}
        assert not validator.validate_proposal(low_confidence)
        assert validator.validate_proposal(high_confidence)

    @staticmethod
    async def test_ai_visual_verification() -> None:
        config = AutomationConfig(ai=AIConfig(enabled=True, ocr_cv_enabled=True))
        mock_page = MockPage()
        humanizer = BehavioralHumanizer(mock_page, config, rng=DeterministicRandomSource(42), clock=VirtualTestClock())
        assert humanizer.ai_verification is not None

        state_before = await humanizer.ai_verification.record_state_before(mock_page)
        assert state_before["url"] == mock_page.url
        res = await humanizer.ai_verification.verify_state_after(mock_page, state_before, "Mocked DOM Content")
        assert res["success"] is True
        assert res["text_verified"] is True

    @staticmethod
    async def test_complete_ai_mock_e2e_pipeline() -> None:
        config = AutomationConfig(ai=AIConfig(enabled=True, self_healing_enabled=True, ocr_cv_enabled=True))
        mock_page = MockPage()
        humanizer = BehavioralHumanizer(mock_page, config, rng=DeterministicRandomSource(42), clock=VirtualTestClock())
        click_ok = await humanizer.execute_safe_click("#btn-login", "Mocked DOM Content")
        assert click_ok is True
        click_healed = await humanizer.execute_safe_click("#broken-selector-dynamic", "Mocked DOM Content")
        assert click_healed is True
        type_healed = await humanizer.execute_safe_type("#username-broken", "my_user", "Mocked DOM Content")
        assert type_healed is True

    @staticmethod
    async def test_real_or_mock_integration_pipeline() -> None:
        config = AutomationConfig(
            browser=BrowserConfig(headless=True),
            network=NetworkConfig(max_attempts=1),
        )
        context, provider = await BrowserProviderFactory.launch_stabilized_lifecycle(config)
        try:
            page = context.pages[0] if context.pages else await context.new_page()
            cb = CircuitBreaker(clock=SystemClock())
            navigator = NavigationManager(config, cb)
            success = await navigator.safe_goto(page, "https://bot-detector.rebrowser.net")
            assert success is True

            humanizer = BehavioralHumanizer(page, config)
            try:
                await humanizer.human_type("#text-input", "GoldTest")
            except Exception:
                await humanizer.move_mouse_to(150.0, 250.0, steps=10)
        finally:
            await provider.shutdown()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(SelfTestSuite.run_all_tests())
