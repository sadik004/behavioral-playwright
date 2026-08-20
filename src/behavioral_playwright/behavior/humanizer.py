"""
Core Behavioral Humanizer controller orchestrating physiological clicks, typing, smooth cursor movements, and scrolling.
"""

import logging
import math
from typing import Any, List, Optional, Tuple

from ..config.root import AutomationConfig
from ..diagnostics.bridges import (
    AmbientSensorSpoofEngine,
    AudioFingerprintDeflectionEngine,
    BiometricLivenessSynthesizer,
    CognitiveInterferenceModel,
    EbpfTcpSpoofBridge,
    EnvironmentalTrustEngine,
    ExtensionCanaryShieldEngine,
    FontMetricCalibrationEngine,
    HardwareAttestationRelay,
    JSEngineDivergenceEmulator,
    LocalOSInputBridge,
    MFAOtpPollingBridge,
    MockChallengeSolver,
    MultimodalTimingCorrelation,
    VirtualCpuCacheTimingJitter,
    WebWorkerEvasionEngine,
)
from ..exceptions import AutomationError, InteractionError
from ..math_engine.bezier import BezierTrajectoryGenerator
from ..math_engine.chaos import AffineCoordinateMapper, LorenzAttractorGenerator
from ..math_engine.sigmadrift import SigmaDriftTrajectoryGenerator
from ..utils.clock_rng import SystemClock, SystemRandomSource
from ..utils.protocols import ChallengeSolverProtocol, Clock, PageProtocol, RandomSource
from .models import LinguisticKeystrokeDynamics, SelfHealingSelectorEngine


class BehavioralHumanizer:
    """
    Orchestrates physiological click/typing events over any Protocol Page.
    Fully DI-oriented, injecting configurable clocks and randomness sources.
    """

    def __init__(
        self,
        page: PageProtocol,
        config: AutomationConfig,
        rng: RandomSource = SystemRandomSource(),
        clock: Clock = SystemClock(),
        solver: Optional[ChallengeSolverProtocol] = None,
        custom_logger: Optional[logging.Logger] = None,
    ) -> None:
        self.page = page
        self.cfg = config
        self.rng = rng
        self.clock = clock
        self.solver = solver or MockChallengeSolver(clock, rng)
        self.healer = SelfHealingSelectorEngine(custom_logger)
        self.logger = custom_logger or logging.getLogger("BehavioralAutomation")
        self.current_position: Tuple[float, float] = (0.0, 0.0)
        self.affine_mapper = AffineCoordinateMapper()
        self.session_start = self.clock.time()
        self.cognitive_model = CognitiveInterferenceModel()
        self.trust_engine = EnvironmentalTrustEngine(self.cfg.browser.user_data_dir)
        self.os_input_bridge = LocalOSInputBridge(self.affine_mapper)
        self.mfa_bridge = MFAOtpPollingBridge()
        self.engine_divergence = JSEngineDivergenceEmulator()
        self.worker_evasion = WebWorkerEvasionEngine()
        self.vcpu_timing = VirtualCpuCacheTimingJitter()
        self.ambient_sensors = AmbientSensorSpoofEngine()
        self.audio_deflection = AudioFingerprintDeflectionEngine()
        self.font_calibration = FontMetricCalibrationEngine()
        self.canary_shield = ExtensionCanaryShieldEngine()
        base_multimodal_delay = (
            self.cfg.click.pre_click_delay_max * 1000.0
            if hasattr(self.cfg, "click") and hasattr(self.cfg.click, "pre_click_delay_max")
            else 150.0
        )
        self.multimodal_timing = MultimodalTimingCorrelation(base_delay_ms=base_multimodal_delay)
        self.ebpf_bridge = EbpfTcpSpoofBridge()
        self.linguistic_model = LinguisticKeystrokeDynamics()
        self.liveness_synthesizer = BiometricLivenessSynthesizer()
        self.tpm_relay = HardwareAttestationRelay()

        # Modular AI & Computer Vision engines
        self.vision_engine: Optional[Any] = None
        self.llm_provider: Optional[Any] = None
        self.llm_reasoning: Optional[Any] = None
        self.ai_resolver: Optional[Any] = None
        self.ai_validator: Optional[Any] = None
        self.ai_verification: Optional[Any] = None
        self.ai_orchestrator: Optional[Any] = None

        self._init_ai_subsystems()

    def _init_ai_subsystems(self) -> None:
        try:
            from ..ai.llm.provider import LLMProvider
            from ..ai.llm.reasoning import LLMReasoning
            from ..ai.orchestrator import AIOrchestrator
            from ..ai.self_healing.resolver import SelfHealingResolver
            from ..ai.self_healing.validator import ActionValidator, VisualVerification
            from ..ai.vision.engine import VisionEngine

            self.vision_engine = VisionEngine(self.cfg)
            self.llm_provider = LLMProvider(self.cfg)
            self.llm_reasoning = LLMReasoning(self.llm_provider)
            self.ai_resolver = SelfHealingResolver(self.cfg, self.healer, self.vision_engine, self.llm_reasoning)
            self.ai_validator = ActionValidator(self.cfg)
            self.ai_verification = VisualVerification(self.cfg)
            self.ai_orchestrator = AIOrchestrator(
                self.cfg, self, self.ai_resolver, self.ai_validator, self.ai_verification
            )
        except Exception as e:
            self.logger.debug(f"AI sub-systems initialization deferred: {e}")

    def get_fatigue_multiplier(self) -> float:
        """Simulates muscle fatigue and cognitive deceleration over continuous operation time."""
        elapsed = self.clock.time() - self.session_start
        multiplier = 1.0 + (elapsed / 1800.0) * 0.35
        return min(1.35, multiplier)

    @staticmethod
    def get_qwerty_key_distance(char1: str, char2: str) -> float:
        """Mathematical QWERTY layout grid modeling physical inter-key travel distances."""
        qwerty_grid = {
            "q": (0, 0),
            "w": (0, 1),
            "e": (0, 2),
            "r": (0, 3),
            "t": (0, 4),
            "y": (0, 5),
            "u": (0, 6),
            "i": (0, 7),
            "o": (0, 8),
            "p": (0, 9),
            "a": (1, 0.5),
            "s": (1, 1.5),
            "d": (1, 2.5),
            "f": (1, 3.5),
            "g": (1, 4.5),
            "h": (1, 5.5),
            "j": (1, 6.5),
            "k": (1, 7.5),
            "l": (1, 8.5),
            "z": (2, 1.0),
            "x": (2, 2.0),
            "c": (2, 3.0),
            "v": (2, 4.0),
            "b": (2, 5.0),
            "n": (2, 6.0),
            "m": (2, 7.0),
            " ": (3, 4.0),
        }
        c1 = char1.lower()
        c2 = char2.lower()
        if c1 not in qwerty_grid or c2 not in qwerty_grid:
            return 2.5
        p1 = qwerty_grid[c1]
        p2 = qwerty_grid[c2]
        return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)

    async def move_mouse_sequence(self, targets: List[Tuple[float, float]]) -> None:
        """Coordinates sequential mouse gestures across multiple waypoints."""
        if not targets:
            return
        self.logger.info(f"[COGNITIVE] Executing chained sequential pointer sweep across {len(targets)} coordinates...")

        for idx, (tx, ty) in enumerate(targets):
            is_last = idx == len(targets) - 1
            start_x, start_y = self.current_position

            path = SigmaDriftTrajectoryGenerator.generate_biomechanical_path(
                (start_x, start_y), (tx, ty), self.cfg.mouse, self.rng
            )

            for x, y, _ in path:
                try:
                    await self.page.mouse.move(x, y)
                    speed_factor = 0.70 if not is_last else 1.0
                    delay = (
                        self.rng.uniform(self.cfg.mouse.micro_delay_min, self.cfg.mouse.micro_delay_max) * speed_factor
                    )
                    await self.clock.sleep(delay)
                except Exception as e:
                    self.logger.warning(f"Chained coordinate move skipped: {e}")
                    raise InteractionError(f"Sequential trajectory chain ruptured: {e}") from e

            self.current_position = (tx, ty)

            if not is_last:
                await self.clock.sleep(self.rng.uniform(0.04, 0.08))

    async def move_mouse_to(self, target_x: float, target_y: float, steps: Optional[int] = None) -> None:
        """Moves virtual pointer utilizing C1 smoothstep and Sine Jitter calculations."""
        start_x, start_y = self.current_position

        if steps is not None:
            path = BezierTrajectoryGenerator.generate_path(
                (start_x, start_y), (target_x, target_y), steps, self.cfg.mouse, self.rng
            )
            for x, y in path:
                try:
                    await self.page.mouse.move(x, y)
                    await self.clock.sleep(
                        self.rng.uniform(self.cfg.mouse.micro_delay_min, self.cfg.mouse.micro_delay_max)
                    )
                except Exception as e:
                    self.logger.warning(f"Coordinate move skipped at ({x:.1f}, {y:.1f}): {e}")
                    raise InteractionError(f"Mouse trajectory broke execution flow: {e}") from e
        else:
            path_3d = SigmaDriftTrajectoryGenerator.generate_biomechanical_path(
                (start_x, start_y), (target_x, target_y), self.cfg.mouse, self.rng
            )
            for x, y, _ in path_3d:
                try:
                    await self.page.mouse.move(x, y)
                    await self.clock.sleep(
                        self.rng.uniform(self.cfg.mouse.micro_delay_min, self.cfg.mouse.micro_delay_max)
                    )
                except Exception as e:
                    self.logger.warning(f"Coordinate move skipped at ({x:.1f}, {y:.1f}): {e}")
                    raise InteractionError(f"Biomechanical trajectory broke execution: {e}") from e

        self.current_position = (target_x, target_y)
        sx, sy = self.affine_mapper.map_viewport_to_screen(target_x, target_y)
        self.logger.info(
            f"[PHYSICAL ENVELOPE] Mapped Viewport ({target_x:.2f}, {target_y:.2f}) to Screen ({sx:.2f}, {sy:.2f})"
        )

    async def human_scroll(self, distance_y: float) -> None:
        """Simulates human mouse-wheel or touchpad scrolling using Newtonian Deceleration."""
        if distance_y == 0.0:
            return
        self.logger.info(f"[OS INPUT] Initiating Newtonian inertial scroll of {distance_y:.1f}px on Y-axis...")

        remaining = distance_y
        direction = 1.0 if distance_y > 0.0 else -1.0
        speed = 12.0 * direction
        deceleration = 0.40 * direction

        while abs(remaining) > 0.5:
            dt_ms = self.rng.gamma(2.0, 4.0)
            dt_s = dt_ms / 1000.0
            step_y = speed * dt_ms

            if abs(step_y) >= abs(remaining):
                step_y = remaining
                remaining = 0.0
            else:
                remaining -= step_y

            speed -= deceleration * dt_ms
            if (speed * direction) <= 0.2:
                step_y = remaining
                remaining = 0.0

            try:
                if hasattr(self.page.mouse, "wheel"):
                    await self.page.mouse.wheel(0.0, step_y)
                await self.clock.sleep(dt_s)
            except Exception as e:
                self.logger.warning(f"Scroll step skipped: {e}")
                break

    async def human_click(self, selector: str) -> None:
        """Clicks element utilizing randomized bounding coordinates and hold timing."""
        try:
            try:
                element = await self.page.wait_for_selector(selector, timeout=2.0)
            except Exception:
                mock_candidates = ["#btn-login", "input[name='login']", "button[type='submit']"]
                healed = self.healer.heal_selector(selector, mock_candidates)
                if healed:
                    try:
                        element = await self.page.wait_for_selector(healed, timeout=2.0)
                    except Exception:
                        element = None
                else:
                    raise InteractionError(
                        f"Target selector '{selector}' not visible, and Self-Healing was unable to resolve."
                    )

            if not element:
                raise InteractionError(f"Target selector '{selector}' was not visible.")

            box = await element.bounding_box()
            if not box:
                raise InteractionError(f"Could not calculate bounding coordinates for selector: {selector}")

            target_x = box["x"] + (box["width"] * self.rng.uniform(0.15, 0.85))
            target_y = box["y"] + (box["height"] * self.rng.uniform(0.15, 0.85))

            await self.move_mouse_to(target_x, target_y)

            self.liveness_synthesizer.update_gaze_gimbal(target_x, target_y)

            if "login" in selector or "submit" in selector:
                self.tpm_relay.relay_cryptographic_sign("auth_chal_9901", "https://bot-detector.rebrowser.net")

            self.worker_evasion.shield_worker_telemetry()
            self.engine_divergence.configure_engine_divergence()

            elapsed = self.clock.time() - self.session_start
            self.ambient_sensors.simulate_sensor_noise(elapsed)
            self.audio_deflection.deflect_audio_fingerprint()
            self.font_calibration.calibrate_font_metrics()
            self.canary_shield.sanitize_extension_probes()

            fatigue_mult = self.get_fatigue_multiplier()
            gap = self.multimodal_timing.calculate_interaction_gap(self.rng, fatigue_mult)
            gap = self.vcpu_timing.calculate_timing_jitter(gap)
            await self.clock.sleep(gap)

            stroop_delay = self.cognitive_model.calculate_stroop_penalty(selector)
            if stroop_delay > 0.0:
                await self.clock.sleep(stroop_delay)

            self.os_input_bridge.dispatch_os_level_click(target_x, target_y)

            await self.clock.sleep(
                self.rng.uniform(self.cfg.click.pre_click_delay_min, self.cfg.click.pre_click_delay_max) * fatigue_mult
            )

            await self.page.mouse.down()
            hold_time = self.rng.weibull(self.cfg.click.weibull_scale, self.cfg.click.weibull_shape) * fatigue_mult
            await self.clock.sleep(max(self.cfg.click.duration_min, hold_time))
            await self.page.mouse.up()

            await self.clock.sleep(
                self.rng.uniform(self.cfg.click.post_click_delay_min, self.cfg.click.post_click_delay_max)
                * fatigue_mult
            )
        except Exception as e:
            if not isinstance(e, AutomationError):
                raise InteractionError(f"Behavioral click failed on '{selector}': {e}") from e
            raise

    async def human_type(self, selector: str, text: str) -> None:
        """Simulates human typing rhythms incorporating custom typing entropy and backspace corrections."""
        try:
            await self.human_click(selector)
            await self.clock.sleep(self.rng.uniform(0.1, 0.2))

            self.logger.info(f"Typing string of length {len(text)} into selector '{selector}'")
            prev_char: Optional[str] = None
            fatigue = self.get_fatigue_multiplier()

            gap = self.multimodal_timing.calculate_interaction_gap(self.rng, fatigue)
            gap = self.vcpu_timing.calculate_timing_jitter(gap)
            await self.clock.sleep(gap)

            for char in text:
                if self.rng.random() < self.cfg.keyboard.mistake_probability and len(text) > 1:
                    typo_char = self.rng.choice("abcdefghijklmnopqrstuvwxyz")
                    await self.page.keyboard.type(typo_char)
                    await self.clock.sleep(
                        self.rng.uniform(self.cfg.keyboard.correction_delay_min, self.cfg.keyboard.correction_delay_max)
                        * fatigue
                    )

                    await self.page.keyboard.press("Backspace")
                    await self.clock.sleep(
                        self.rng.uniform(self.cfg.keyboard.correction_delay_min, self.cfg.keyboard.correction_delay_max)
                        * fatigue
                    )

                await self.page.keyboard.type(char)
                base_delay = self.rng.weibull(self.cfg.keyboard.weibull_alpha, self.cfg.keyboard.weibull_beta)

                if prev_char:
                    dist = self.get_qwerty_key_distance(prev_char, char)
                    distance_penalty = 1.0 + (dist * self.cfg.keyboard.qwerty_distance_multiplier)
                else:
                    distance_penalty = 1.0

                third_prev = text[text.index(char) - 2] if text.index(char) >= 2 else None
                linguistic_factor = (
                    self.linguistic_model.calculate_linguistic_factor(prev_char, char, third_prev) if prev_char else 1.0
                )

                delay = base_delay * distance_penalty * fatigue * linguistic_factor
                await self.clock.sleep(max(self.cfg.keyboard.min_delay, delay))
                prev_char = char

            await self.clock.sleep(self.rng.uniform(0.15, 0.35))
        except Exception as e:
            if not isinstance(e, AutomationError):
                raise InteractionError(f"Behavioral typing failed on '{selector}': {e}") from e
            raise

    async def human_idle_drift(self, duration: float) -> None:
        """Simulates human hand resting or looking at page using chaotic Lorenz attractor micro-drift."""
        self.logger.info(f"Initiating neuromuscular human idle drift for {duration:.2f}s...")
        start_time = self.clock.time()
        start_x, start_y = self.current_position
        lorenz = LorenzAttractorGenerator(
            sigma=self.cfg.mouse.lorenz_sigma,
            rho=self.cfg.mouse.lorenz_rho,
            beta=self.cfg.mouse.lorenz_beta,
            dt=self.cfg.mouse.lorenz_dt,
        )

        while self.clock.time() - start_time < duration:
            lx, ly, _ = lorenz.next_step()
            drift_x = lx * 0.1
            drift_y = ly * 0.1

            target_x = start_x + (drift_x * 0.8)
            target_y = start_y + (drift_y * 0.8)

            try:
                await self.page.mouse.move(target_x, target_y)
                await self.clock.sleep(self.rng.uniform(0.05, 0.10))
            except Exception as e:
                self.logger.warning(f"Micro-drift move skipped: {e}")
                break

    async def execute_safe_click(self, selector: str, expected_text: Optional[str] = None) -> bool:
        """Executes a secure humanized click with optional AI-driven healing and state verification."""
        if self.ai_orchestrator:
            return bool(await self.ai_orchestrator.execute_safe_click(self.page, selector, expected_text))
        await self.human_click(selector)
        return True

    async def execute_safe_type(self, selector: str, text: str, expected_text: Optional[str] = None) -> bool:
        """Executes secure humanized typing with optional AI-driven healing and state verification."""
        if self.ai_orchestrator:
            return bool(await self.ai_orchestrator.execute_safe_type(self.page, selector, text, expected_text))
        await self.human_type(selector, text)
        return True
