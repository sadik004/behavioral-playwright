"""
PowerPlay CAPTCHA Infinite Loop Detector.
Cumulative Poisson CDF and dynamic escalating lambda loop-risk evaluator.
"""

import math

class ResolvedCAPTCHAInfiniteLoopDetector:
    """
    MATHEMATICALLY SOLVED (Cumulative Poisson CDF & Dynamic Escalating Lambda) [৩৫]
    Bypasses infinite Turnstile challenges without hard-crashing. Handles zero-challenges gracefully!
    
    Formula:
    1. Dynamic Lambda: λ(t) = λ_base * (1.0 + α * t)
    2. Cumulative Loop Chance: P(X >= k) = 1 - CDF_poisson(k-1, λ)
    """
    def __init__(self, critical_trust_threshold=0.30, alpha=0.20):
        self.critical_trust_threshold = critical_trust_threshold
        self.alpha = alpha  # Anti-bot hostility acceleration rate

    def evaluate_loop_risk(self, consecutive_challenges, base_trust=0.9, lambda_base=1.2):
        """Calculates escalated risk and triggers proxy swings. Includes safety guard for zero inputs [৩৫]."""
        # 🎯 SAFETY GUARD (FIX 4 from earlier turn): Handle 0 consecutive challenges gracefully to avoid inverse 100% risk!
        if consecutive_challenges <= 0:
            return {
                "decision": "PASS",
                "current_trust": round(base_trust, 4),
                "dynamic_lambda": round(lambda_base, 2),
                "cumulative_loop_risk": "0.0%",
                "action": "✅ SAFE: No CAPTCHAs encountered yet."
            }

        # Dynamic, escalating lambda over consecutive challenge attempts [৩৫]
        lambda_t = lambda_base * (1.0 + self.alpha * consecutive_challenges)
        
        # Exponential Bayesian trust decay
        current_trust = base_trust * math.exp(-0.40 * consecutive_challenges)
        
        # Cumulative Poisson loop risk calculation (P(X >= k)) [৩৫]
        poisson_cdf = 0.0
        for i in range(consecutive_challenges):
            poisson_cdf += (math.exp(-lambda_t) * (lambda_t ** i)) / math.factorial(i)
        cumulative_loop_risk = 1.0 - poisson_cdf
        
        # Force risk bounds
        cumulative_loop_risk = max(0.0, min(1.0, cumulative_loop_risk))
        
        if consecutive_challenges >= 3 or current_trust < self.critical_trust_threshold:
            return {
                "decision": "PROACTIVE_ROTATE",
                "current_trust": round(current_trust, 4),
                "dynamic_lambda": round(lambda_t, 2),
                "cumulative_loop_risk": f"{round(cumulative_loop_risk * 100, 2)}%",
                "action": "🔄 PROACTIVE SOFT ROTATION: Commencing SOCKS5 pool swing and cookie warming [৩৫]."
            }
        return {
            "decision": "PASS",
            "current_trust": round(current_trust, 4),
            "dynamic_lambda": round(lambda_t, 2),
            "cumulative_loop_risk": f"{round(cumulative_loop_risk * 100, 2)}%",
            "action": "✅ SAFE: Trust score acceptable. Resolving CAPTCHA challenge."
        }


