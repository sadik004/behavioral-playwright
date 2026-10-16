"""Veil Customizable Client Service Blueprints (`veil.blueprints`).

Provides 5 production-grade blueprints:
1. EcommerceStealthBlueprint - Catalog, pricing, and table extraction with Newtonian scroll
2. CognitiveFormAgentBlueprint - Autonomous form agent with Weibull typing & pre-click streams
3. WebRTCAndAuthAuditBlueprint - Security headers, WebRTC leak risk, and session state vaulting
4. QuantPiTAndITCHBlueprint - Point-in-Time financial alignment and NASDAQ TotalView-ITCH 5.0 feeds
5. FirecrawlReplacementBlueprint - Self-contained, zero-cost drop-in replacement for Firecrawl
"""

from veil.blueprints.ecommerce import EcommerceStealthBlueprint
from veil.blueprints.form_agent import CognitiveFormAgentBlueprint
from veil.blueprints.security_audit import WebRTCAndAuthAuditBlueprint
from veil.blueprints.quant import QuantPiTAndITCHBlueprint
from veil.blueprints.firecrawl import FirecrawlReplacementBlueprint

__all__ = [
    "EcommerceStealthBlueprint",
    "CognitiveFormAgentBlueprint",
    "WebRTCAndAuthAuditBlueprint",
    "QuantPiTAndITCHBlueprint",
    "FirecrawlReplacementBlueprint",
]
