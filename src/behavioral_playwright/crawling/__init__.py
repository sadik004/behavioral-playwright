"""Veil Crawling Subsystem."""

from behavioral_playwright.crawling.clearance_bridge import BrowserClearanceBridge, ClearanceLease
from behavioral_playwright.crawling.dedup import SimHashDeduplicator, canonicalize_url, compute_simhash_64, hamming_distance_64
from behavioral_playwright.crawling.delta_store import DeltaCrawlStore, DeltaEvaluation
from behavioral_playwright.crawling.frontier import HostPolitenessController, PriorityCrawlFrontier
from behavioral_playwright.crawling.mapper import MappedUrl, SiteMapper
from behavioral_playwright.crawling.pagination import PaginationPlan, UniversalPaginationEngine
from behavioral_playwright.crawling.world_class_engine import WorldClassCrawlerEngine
from behavioral_playwright.crawling.host_budget import (
    HostBudgetState,
    SampleThenDeepenAllocator,
    compute_host_quality_density,
    compute_shrout_fleiss_icc1,
    spearman_brown_reliability,
)
from behavioral_playwright.crawling.bandit_proxy_rotator import (
    BanditProxyRotator,
    BandwidthResourceBlocker,
    ProxyArmState,
)
from behavioral_playwright.crawling.deep_crawler import (
    DeepSiteCrawler,
    PersistentFrontierQueue,
    UITraceMetrics,
    UITraceTelemetryVerifier,
)

try:
    from behavioral_playwright.crawling.models import (
        CrawlerTier,
        CrawlRequest,
        EscalationRecord,
        CrawlResponse,
    )
    from behavioral_playwright.crawling.checkpoint import CheckpointStore
    from behavioral_playwright.crawling.service import (
        SimHashDetector,
        ThompsonSamplingDomainRouter,
        TokenBucketRateLimiter,
        AutoRuleSchemaExtractor,
        CrawlingService,
        VeilEngine,
        TieredCrawlerService,
        TieredCrawler,
    )
    from behavioral_playwright.crawling.crawler import Crawler
except ImportError as _optional_crawl_exc:
    _ = _optional_crawl_exc

__all__ = [
    "CrawlerTier",
    "CrawlRequest",
    "EscalationRecord",
    "CrawlResponse",
    "SimHashDetector",
    "ThompsonSamplingDomainRouter",
    "TokenBucketRateLimiter",
    "AutoRuleSchemaExtractor",
    "CrawlingService",
    "VeilEngine",
    "TieredCrawlerService",
    "TieredCrawler",
    "CheckpointStore",
    "Crawler",
    "BrowserClearanceBridge",
    "ClearanceLease",
    "SimHashDeduplicator",
    "canonicalize_url",
    "compute_simhash_64",
    "hamming_distance_64",
    "DeltaCrawlStore",
    "DeltaEvaluation",
    "HostPolitenessController",
    "PriorityCrawlFrontier",
    "MappedUrl",
    "SiteMapper",
    "PaginationPlan",
    "UniversalPaginationEngine",
    "WorldClassCrawlerEngine",
    "HostBudgetState",
    "SampleThenDeepenAllocator",
    "compute_host_quality_density",
    "compute_shrout_fleiss_icc1",
    "spearman_brown_reliability",
    "BanditProxyRotator",
    "BandwidthResourceBlocker",
    "ProxyArmState",
    "DeepSiteCrawler",
    "PersistentFrontierQueue",
    "UITraceMetrics",
    "UITraceTelemetryVerifier",
]
