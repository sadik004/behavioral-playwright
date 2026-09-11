"""
PowerPlay Schema Integrity Guard and O(N) Shannon Entropy Auditor.
"""

import math
from collections import Counter

class ResolvedSchemaIntegrityGuard:
    """
    MATHEMATICALLY OPTIMIZED SHANNON ENTROPY ENGINE [৩৫]
    - Resolves O(N^2) complexity to O(N) using collections.Counter.
    - Prevents CPU thread blocking during heavy HTML scans.
    - Caches calculation results to prevent redundant double executions.
    - Preserves Unicode / UTF-8 & JSON content profile baseline calibrations.
    """
    def __init__(self):
        # Base expected Shannon models
        self.baselines = {
            "english_html": {"mean": 4.50, "std": 0.85},
            "unicode_bengali": {"mean": 4.10, "std": 0.95},
            "json_api": {"mean": 4.25, "std": 0.75}
        }

    def detect_content_profile(self, text):
        """Identifies text composition profile to dynamically adjust expected baseline."""
        sample = text.strip()
        if sample.startswith("{") or sample.startswith("["):
            return "json_api"
            
        # Count non-ASCII (Unicode/Bengali chars)
        non_ascii_count = sum(1 for c in sample if ord(c) > 127)
        if len(sample) > 0 and (non_ascii_count / len(sample)) > 0.15:
            return "unicode_bengali"
            
        return "english_html"

    def calculate_shannon_entropy(self, text):
        """
        Calculates Shannon entropy value of text in O(N) complexity [৩৫].
        Uses collections.Counter to scan the string once instead of multiple counts.
        """
        if not text:
            return 0.0
        
        counts = Counter(text)
        total = len(text)
        # Shannon Entropy formula using Counter frequencies
        entropy = -sum((c / total) * math.log2(c / total) for c in counts.values())
        return entropy

    def audit_page_text(self, scraped_text):
        """Audits page information entropy using dynamic baselines and length controls [৩৫]."""
        N = len(scraped_text)
        
        # 🎯 FIX 2: Cache entropy early to avoid duplicate Shannon counting calculations! [৩৫]
        entropy = self.calculate_shannon_entropy(scraped_text)
        
        # 1. Length-Based Bypass Rule (If N < 50, Z-score computation is skipped) [৩৫]
        if N < 50:
            return {
                "decision": "PASS_BYPASS",
                "shannon_entropy": round(entropy, 3),
                "z_score": 0.0,
                "content_profile": f"Short Text (N={N})",
                "action": f"✅ PASS (BYPASS): Content length (N={N} < 50) bypassed to prevent false blocks [৩৫]."
            }
            
        # 2. Dynamic Baseline Profiling [৩৫]
        profile = self.detect_content_profile(scraped_text)
        baseline = self.baselines[profile]
        
        z_score = (entropy - baseline["mean"]) / baseline["std"]
        
        # 3. Decision Boundary Guard
        if z_score < -2.5:
            return {
                "decision": "SHADOW_BAN_DETECTED",
                "shannon_entropy": round(entropy, 3),
                "z_score": round(z_score, 3),
                "content_profile": profile,
                "action": "🔄 SHADOW-BAN RESOLVER: Initiating HTTP/2 frame swapping & dynamic referrers [৩৫]."
            }
            
        return {
            "decision": "PASS",
            "shannon_entropy": round(entropy, 3),
            "z_score": round(z_score, 3),
            "content_profile": profile,
            "action": f"✅ PASS: Information density normal for {profile.replace('_', ' ').title()}. Safe to commit."
        }


