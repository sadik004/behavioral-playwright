"""
Closed-Loop Information Entropy & Structural DOM Anomaly Guard (ResolvedSchemaIntegrityGuard)

Hardened Production Features:
- Negative Lookbehind (aria-hidden exclusion) eliminating honeypot false positives.
- Expanded CSS Honeypot detection (top, left, margin-left, text-indent, font-size).
- Context-Aware Challenge Wall Detection (Structural verification avoiding blog false flags).
- Variance Floor bounding preventing Z-Score explosion on narrow baselines.
- 100% Backward Compatibility with legacy behavioral-playwright test contracts.
"""

import math
import zlib
import re
from collections import Counter
import numpy as np
from typing import List, Dict, Any

# Pre-compiled Module-Level Regular Expressions (SLA < 15ms)
RE_TAG_EXTRACT = re.compile(r'<([a-zA-Z0-9]+)')
RE_CLEAN_SCRIPTS = re.compile(r'<(script|style|svg|noscript)[^>]*>.*?</\1>', re.DOTALL | re.IGNORECASE)
RE_CLEAN_COMMENTS = re.compile(r'<!--.*?-->', re.DOTALL)
RE_CLEAN_TAGS = re.compile(r'<[^>]+>')
RE_TOTAL_TAGS = re.compile(r'<[a-zA-Z0-9]+')
RE_SCRIPT_CONTENT = re.compile(r'<script[^>]*>(.*?)</script>', re.DOTALL | re.IGNORECASE)

# FIXED: Excludes <input type="hidden"> and aria-hidden="true" from false honeypot triggers
RE_HIDDEN_ELEMENT = re.compile(
    r'(?:style=["\'][^"\']*(?:display:\s*none|visibility:\s*hidden|opacity:\s*0|height:\s*0px|width:\s*0px|font-size:\s*0|(?:left|top|margin-left|text-indent):\s*-\d{3,}px)[^"\']*["\'])|'
    r'(?:<(?!input\b)\w+[^>]*(?<!aria-)\bhidden\b[^>]*>)',
    re.IGNORECASE
)


class ResolvedSchemaIntegrityGuard:
    """
    Closed-Loop Information Entropy & Structural DOM Anomaly Guard.
    """

    DECISION_NORMAL = "DECISION_NORMAL"
    DECISION_BLANK_OR_STUB = "DECISION_BLANK_OR_STUB"
    DECISION_CHALLENGE_WALL = "DECISION_CHALLENGE_WALL"
    DECISION_HONEYPOT_ANOMALY = "DECISION_HONEYPOT_ANOMALY"

    def __init__(self):
        self.baselines: Dict[str, Dict[str, Any]] = {}

    @staticmethod
    def compute_shannon_entropy(data: str) -> float:
        """Computes exact Shannon Information Entropy in O(N) linear time."""
        if not data:
            return 0.0
        n = len(data)
        counts = Counter(data)
        entropy = -sum((c / n) * math.log2(c / n) for c in counts.values())
        return float(entropy)

    # Legacy Framework Compatibility Aliases
    def calculate_shannon_entropy(self, text: str) -> float:
        """Legacy framework backward compatibility method."""
        return self.compute_shannon_entropy(text)

    def detect_content_profile(self, text: str) -> str:
        """Legacy framework content profiler."""
        sample = text.strip()
        if sample.startswith("{") or sample.startswith("["):
            return "json_api"
        non_ascii_count = sum(1 for c in sample if ord(c) > 127)
        if len(sample) > 0 and (non_ascii_count / len(sample)) > 0.15:
            return "unicode_bengali"
        return "english_html"

    def audit_page_text(self, scraped_text: str) -> Dict[str, Any]:
        """Legacy framework text auditor."""
        N = len(scraped_text)
        entropy = self.compute_shannon_entropy(scraped_text)

        if N < 50:
            return {
                "decision": "PASS_BYPASS",
                "shannon_entropy": round(entropy, 3),
                "z_score": 0.0,
                "content_profile": f"Short Text (N={N})",
                "action": f"✅ PASS (BYPASS): Content length (N={N} < 50) bypassed to prevent false blocks [৩৫]."
            }

        profile = self.detect_content_profile(scraped_text)
        legacy_baselines = {
            "english_html": {"mean": 4.50, "std": 0.85},
            "unicode_bengali": {"mean": 4.10, "std": 0.95},
            "json_api": {"mean": 4.25, "std": 0.75}
        }
        base = legacy_baselines.get(profile, {"mean": 4.50, "std": 0.85})
        z_score = (entropy - base["mean"]) / base["std"]

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

    @staticmethod
    def _extract_tag_distribution(html: str) -> Dict[str, float]:
        """Extracts normalized tag token frequency distribution Q or P from HTML."""
        tags = [t.lower() for t in RE_TAG_EXTRACT.findall(html)]
        if not tags:
            return {"empty": 1.0}
        total = len(tags)
        counts = Counter(tags)
        return {tag: count / total for tag, count in counts.items()}

    @staticmethod
    def compute_jsd(p_dist: Dict[str, float], q_dist: Dict[str, float]) -> float:
        """Computes symmetrized Jensen-Shannon Divergence (JSD) bounded in [0.0, 1.0]."""
        vocab = set(p_dist.keys()).union(set(q_dist.keys()))
        eps = 1e-9

        p_vec = [p_dist.get(k, eps) for k in vocab]
        q_vec = [q_dist.get(k, eps) for k in vocab]

        p_arr = np.array(p_vec, dtype=np.float64)
        q_arr = np.array(q_vec, dtype=np.float64)

        sum_p = np.sum(p_arr)
        sum_q = np.sum(q_arr)
        if sum_p > 0:
            p_arr /= sum_p
        if sum_q > 0:
            q_arr /= sum_q

        m_arr = 0.5 * (p_arr + q_arr)
        d_kl_pm = np.sum(p_arr * np.log2(p_arr / m_arr))
        d_kl_qm = np.sum(q_arr * np.log2(q_arr / m_arr))

        jsd = 0.5 * d_kl_pm + 0.5 * d_kl_qm
        return float(max(0.0, min(1.0, jsd)))

    @staticmethod
    def _extract_visible_text(html: str) -> str:
        """Strips HTML tags, scripts, and styles to extract visible text content."""
        clean = RE_CLEAN_SCRIPTS.sub('', html)
        clean = RE_CLEAN_COMMENTS.sub('', clean)
        clean = RE_CLEAN_TAGS.sub(' ', clean)
        return ' '.join(clean.split())

    @staticmethod
    def _calculate_hidden_element_penalty(html: str) -> float:
        """Calculates ratio of hidden/invisible DOM elements or honeypot traps."""
        hidden_matches = RE_HIDDEN_ELEMENT.findall(html)
        total_elements = len(RE_TOTAL_TAGS.findall(html))
        if total_elements == 0:
            return 0.0
        return float(len(hidden_matches) / total_elements)

    def learn_baseline(self, html_samples: List[str], profile_name: str = "default") -> None:
        """Calibrates running baseline statistics with safe variance floors."""
        if not html_samples:
            return

        entropies = []
        densities = []
        all_tags: Dict[str, List[float]] = {}

        for sample in html_samples:
            h = self.compute_shannon_entropy(sample)
            vis_text = self._extract_visible_text(sample)
            dens = len(vis_text) / max(1, len(sample))

            entropies.append(h)
            densities.append(dens)

            tag_dist = self._extract_tag_distribution(sample)
            for k, v in tag_dist.items():
                if k not in all_tags:
                    all_tags[k] = []
                all_tags[k].append(v)

        entropies_arr = np.array(entropies, dtype=np.float64)
        mean_h = float(np.mean(entropies_arr))
        std_h = max(0.20, float(np.std(entropies_arr)))

        median_h = float(np.median(entropies_arr))
        mad_h = max(0.15, float(np.median(np.abs(entropies_arr - median_h))))

        avg_q_dist = {}
        total_samples = len(html_samples)
        for k, v_list in all_tags.items():
            avg_q_dist[k] = sum(v_list) / total_samples

        sum_q = sum(avg_q_dist.values())
        if sum_q > 0:
            avg_q_dist = {k: v / sum_q for k, v in avg_q_dist.items()}

        self.baselines[profile_name] = {
            "mean_h": mean_h,
            "std_h": std_h,
            "median_h": median_h,
            "mad_h": mad_h,
            "avg_q_dist": avg_q_dist,
            "mean_density": float(np.mean(densities))
        }

    def audit_content_entropy(self, raw_html: str, profile_name: str = "default") -> Dict[str, Any]:
        """Audits provided HTML against baseline statistics with structural heuristics."""
        if profile_name not in self.baselines:
            self.baselines[profile_name] = {
                "mean_h": 4.65,
                "std_h": 0.35,
                "median_h": 4.65,
                "mad_h": 0.25,
                "avg_q_dist": {"div": 0.35, "a": 0.20, "span": 0.15, "p": 0.10, "img": 0.10, "script": 0.10},
                "mean_density": 0.25
            }

        base = self.baselines[profile_name]
        h_shannon = self.compute_shannon_entropy(raw_html)

        z_score = (h_shannon - base["mean_h"]) / base["std_h"]
        modified_z_score = 0.6745 * (h_shannon - base["median_h"]) / base["mad_h"]

        p_tag_dist = self._extract_tag_distribution(raw_html)
        jsd_val = self.compute_jsd(p_tag_dist, base["avg_q_dist"])

        vis_text = self._extract_visible_text(raw_html)
        text_density_ratio = len(vis_text) / max(1, len(raw_html))

        raw_bytes = raw_html.encode('utf-8')
        compressed_bytes = zlib.compress(raw_bytes)
        compression_ratio = len(compressed_bytes) / max(1, len(raw_bytes))

        hidden_penalty = self._calculate_hidden_element_penalty(raw_html)

        # FIXED: Structural challenge markers vs contextual tech content
        raw_html_lower = raw_html.lower()
        structural_challenge_markers = [
            "_cf_chl_opt", "cf-challenge", "challenge-form", "cf-browser-verification",
            "challenge-running", "just a moment..."
        ]
        is_structural_challenge = any(m in raw_html_lower for m in structural_challenge_markers)
        script_matches = RE_SCRIPT_CONTENT.findall(raw_html)
        script_text_len = sum(len(s) for s in script_matches)
        script_density = script_text_len / max(1, len(raw_html))

        has_contextual_challenge = any(kw in raw_html_lower for kw in ["turnstile", "datadome"]) and (text_density_ratio < 0.12 or script_density > 0.35)

        # Decision Boundary Classification
        if is_structural_challenge or has_contextual_challenge or (script_density > 0.40 and text_density_ratio < 0.05 and jsd_val > 0.38):
            decision = self.DECISION_CHALLENGE_WALL
            is_safe = False
            confidence = 0.98
        elif len(raw_html.strip()) < 150 or len(vis_text) < 10 or h_shannon < 2.5:
            decision = self.DECISION_BLANK_OR_STUB
            is_safe = False
            confidence = 0.95
        elif abs(z_score) > 3.5 or abs(modified_z_score) > 3.5 or hidden_penalty > 0.10:
            decision = self.DECISION_HONEYPOT_ANOMALY
            is_safe = False
            confidence = 0.92
        else:
            decision = self.DECISION_NORMAL
            is_safe = True
            confidence = float(max(0.70, min(1.0, 1.0 - (abs(z_score) * 0.1))))

        return {
            "shannon_entropy": round(float(h_shannon), 4),
            "z_score": round(float(z_score), 4),
            "modified_z_score": round(float(modified_z_score), 4),
            "jsd_divergence": round(float(jsd_val), 4),
            "text_density_ratio": round(float(text_density_ratio), 4),
            "compression_ratio": round(float(compression_ratio), 4),
            "decision": decision,
            "is_safe_to_proceed": is_safe,
            "confidence_score": round(float(confidence), 4)
        }

    async def verify_page_integrity(self, page: Any, profile_name: str = "default") -> Dict[str, Any]:
        """Asynchronous helper extracting active DOM HTML from Playwright page instance."""
        raw_html = ""
        try:
            if hasattr(page, "content"):
                raw_html = await page.content()
        except Exception:
            pass

        return self.audit_content_entropy(raw_html, profile_name=profile_name)
