"""
Domain-specific configuration dataclasses for mouse, keyboard, clicks, browser, network, locale, and rendering.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class MouseConfig:
    min_steps: int = 15
    lorenz_sigma: float = 10.0  # Lorenz system chaotic parameter sigma
    lorenz_rho: float = 28.0  # Lorenz system chaotic parameter rho
    lorenz_beta: float = 2.6667  # Lorenz system chaotic parameter beta
    lorenz_dt: float = 0.005  # Lorenz integration step dt
    fbm_hurst: float = 0.75  # Fractional Brownian Motion Hurst exponent (0.7-0.9)
    fbm_phi: float = 0.82  # Muscle tremor AR(1) correlation factor
    distance_divisor: float = 12.0
    jitter_std: float = 0.15
    micro_delay_min: float = 0.003
    micro_delay_max: float = 0.008
    p1_offset_min: float = -0.15
    p1_offset_max: float = 0.65
    p2_offset_min: float = 0.35
    p2_offset_max: float = 1.15
    # Biomechanical SigmaDrift Configs
    fitts_a: float = 50.0  # Fitts's Law scale intercept (ms)
    fitts_b: float = 150.0  # Fitts's Law logarithmic multiplier
    target_width: float = 20.0  # Target bounding diameter width
    ou_theta: float = 0.15  # Ornstein-Uhlenbeck mean-reversion rate
    ou_sigma: float = 1.2  # Lateral drift intensity scale
    sdn_k: float = 0.04  # Signal-Dependent Noise coefficient
    tremor_amp_max: float = 0.55  # Physiological hand tremor limit
    tremor_freq: float = 10.0  # Tremor band peak frequency (Hz)
    gamma_shape: float = 4.0  # Gamma distributed interval shape parameter
    gamma_scale: float = 2.0  # Gamma distributed interval scale parameter


@dataclass(frozen=True)
class KeyboardConfig:
    mistake_probability: float = 0.012  # 1.2% chance of simulating typing error
    weibull_alpha: float = 0.095  # Scale parameter representing mean latency
    weibull_beta: float = 1.85  # Shape parameter representing human asymmetric right tail
    avg_delay_mean: float = 0.095
    avg_delay_std: float = 0.035  # Deviation bounds (35ms)
    min_delay: float = 0.025  # Hard floor for keypresses (25ms)
    correction_delay_min: float = 0.12  # Delay before typo correction (120ms)
    correction_delay_max: float = 0.30  # Delay after typo correction (300ms)
    qwerty_distance_multiplier: float = 0.15  # Key distance delay penalty factor


@dataclass(frozen=True)
class ClickConfig:
    weibull_scale: float = 0.080  # Weibull hold scale
    weibull_shape: float = 2.10  # Weibull hold shape
    duration_mean: float = 0.080
    duration_std: float = 0.012  # Deviation (12ms)
    duration_min: float = 0.040  # Hard click floor (40ms)
    pre_click_delay_min: float = 0.08  # Eye-hand coordination pause min (80ms)
    pre_click_delay_max: float = 0.15  # Max pause (150ms)
    post_click_delay_min: float = 0.10  # Muscle recovery delay min (100ms)
    post_click_delay_max: float = 0.25  # Max delay (250ms)


@dataclass(frozen=True)
class BrowserConfig:
    user_data_dir: str = "./stealth_profile"
    headless: bool = True
    width: int = 1920
    height: int = 1080
    license_key: Optional[str] = None
    remote_cdp_url: Optional[str] = None  # CDP remote debug bridge


@dataclass(frozen=True)
class NetworkConfig:
    proxy_url: Optional[str] = None
    markov_entropy_limit: float = 1.10  # Lower boundary of transition entropy to trigger escape
    markov_history_limit: int = 12  # Total size of historical states tracked by Markov loop detector
    max_attempts: int = 3
    initial_delay: float = 2.0
    backoff_factor: float = 2.0
    navigation_timeout_ms: int = 30000
    socks5_dns_leak_prevention: bool = True  # SOCKS5 DNS Leak prevention
    ja4_tls_emulation: bool = True  # HTTP/2 Settings and TLS Emulation
    burp_suite_ca_inject: bool = False  # Private Burp Suite CA cert Trust-Anchor Injection


@dataclass(frozen=True)
class LocaleConfig:
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    locale: str = "en-US"
    timezone_id: str = "America/New_York"
    latitude: float = 40.7128
    longitude: float = -74.0060
    permissions: List[str] = field(default_factory=lambda: ["geolocation", "notifications", "camera", "microphone"])


@dataclass(frozen=True)
class RenderingConfig:
    fingerprint_font_metrics: bool = True
    storage_quota_mb: int = 5000
    disable_webgl: bool = False
    disable_canvas_aa: bool = True
    canvas_grid_mapping: bool = True  # Canvas Coordinate Mapping Grid Engine
    webrtc_media_spoof: bool = True  # WebRTC Mic/Camera spoofing
    fake_video_stream_path: Optional[str] = None  # Path to fake .y4m file
    fake_audio_stream_path: Optional[str] = None  # Path to fake .wav file
