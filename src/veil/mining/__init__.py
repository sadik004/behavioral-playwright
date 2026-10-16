"""
SEO, AEO, and GEO Mining Subsystem.
Provides People Also Ask (PAA) tree extraction, AI Overview audit, and SERP cannibalization analysis.
"""

from behavioral_playwright.mining.aio_auditor import AIOAuditor
from behavioral_playwright.mining.cannibalization import SERPCannibalizationEngine
from behavioral_playwright.mining.engine import SEOMiningEngine
from behavioral_playwright.mining.paa_miner import PAAMiner
from behavioral_playwright.mining.suggest_miner import GoogleSuggestMiner, SuggestMiner
from behavioral_playwright.verification.rendering_auditor import (
    CSRRenderingDriftAuditor,
    RenderingDriftAuditor,
)

__all__ = [
    "SEOMiningEngine",
    "PAAMiner",
    "AIOAuditor",
    "SERPCannibalizationEngine",
    "GoogleSuggestMiner",
    "SuggestMiner",
    "CSRRenderingDriftAuditor",
    "RenderingDriftAuditor",
]
