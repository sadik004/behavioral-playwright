"""
PowerPlay Stateful Evasion Tracker.
Tracks historic request patterns, IP reputation decays, CAPTCHA encounter counts,
and sliding-window memory metrics across scraping sessions.
"""

import time
import numpy as np

class StatefulEvasionTracker:
    """
    STATEFUL EVASION TRACKER [৩৫]
    Tracks historic request patterns, IP reputation decays, CAPTCHA encounter counts,
    and sliding-window memory metrics across the entire scraping session.
    Enables true adaptive evasion!
    """
    def __init__(self, history_window_size=10):
        self.history_window_size = history_window_size
        self.request_timestamps = []
        self.ip_reputation = 1.0  # Decays statefully on CAPTCHA loops or shadow bans
        self.captcha_encounters = 0
        self.memory_history = []
        self.shadow_ban_strikes = 0

    def record_request(self):
        """Logs request timestamp and maintains a sliding history window."""
        now = time.time()
        self.request_timestamps.append(now)
        if len(self.request_timestamps) > self.history_window_size:
            self.request_timestamps.pop(0)

    def calculate_rolling_request_rate(self):
        """Calculates requests per minute (RPM) and statistical interval jitter."""
        if len(self.request_timestamps) < 2:
            return 0.0, 0.0  # (RPM, Jitter)
        
        intervals = [self.request_timestamps[i] - self.request_timestamps[i-1] for i in range(1, len(self.request_timestamps))]
        mean_interval = np.mean(intervals)
        rpm = 60.0 / mean_interval if mean_interval > 0 else 0.0
        jitter = np.std(intervals)  # Statistical variance/deviation of delays (robotic pattern check)
        return round(rpm, 2), round(jitter, 3)

    def register_captcha(self):
        """Encountered a CAPTCHA. Decays stateful IP reputation score."""
        self.captcha_encounters += 1
        self.ip_reputation = max(0.05, self.ip_reputation * 0.75)

    def register_shadow_ban(self):
        """Encountered low entropy page. Decays reputation quickly."""
        self.shadow_ban_strikes += 1
        self.ip_reputation = max(0.05, self.ip_reputation * 0.50)

    def record_memory(self, usage_mb):
        """Tracks RAM logs for sliding-average filtering."""
        self.memory_history.append(usage_mb)
        if len(self.memory_history) > self.history_window_size:
            self.memory_history.pop(0)

    def get_sliding_average_ram(self):
        return round(np.mean(self.memory_history), 2) if self.memory_history else 0.0

    def compute_adaptive_threat_index(self):
        """
        Calculates a stateful sessional threat index (0.0 to 100.0)
        based on request rate variance, current IP reputation decay, and sessional CAPTCHAs.
        """
        rpm, jitter = self.calculate_rolling_request_rate()
        
        # High RPM + Low Jitter (robotic regularity) increases threat score
        regularity_factor = 25.0 * (1.0 / (1.0 + jitter)) if rpm > 15 and jitter < 0.1 else 0.0
        reputation_penalty = 50.0 * (1.0 - self.ip_reputation)
        captcha_penalty = min(25.0, self.captcha_encounters * 8.0)
        
        threat_score = regularity_factor + reputation_penalty + captcha_penalty
        return round(max(0.0, min(100.0, threat_score)), 2)


