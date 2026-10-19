"""Veil Crawling Subsystem."""

from veil.crawling.clearance_bridge import BrowserClearanceBridge, ClearanceLease
from veil.crawling.dedup import SimHashDeduplicator, canonicalize_url, compute_simhash_64, hamming_distance_64
from veil.crawling.delta_store import DeltaCrawlStore, DeltaEvaluation
from veil.crawling.frontier import HostPolitenessController, PriorityCrawlFrontier
from veil.crawling.mapper import MappedUrl, SiteMapper
from veil.crawling.pagination import PaginationPlan, UniversalPaginationEngine
from veil.crawling.world_class_engine import WorldClassCrawlerEngine
from veil.crawling.host_budget import (
    HostBudgetState,
    SampleThenDeepenAllocator,
    compute_host_quality_density,
    compute_shrout_fleiss_icc1,
    spearman_brown_reliability,
)
from veil.crawling.bandit_proxy_rotator import (
    BanditProxyRotator,
    BandwidthResourceBlocker,
    ProxyArmState,
)
from veil.crawling.deep_crawler import (
    DeepSiteCrawler,
    PersistentFrontierQueue,
    UITraceMetrics,
    UITraceTelemetryVerifier,
)

try:
    from veil.crawling.models import (
        CrawlerTier,
        CrawlRequest,
        EscalationRecord,
        CrawlResponse,
    )
    from veil.crawling.checkpoint import CheckpointStore
    from veil.crawling.service import (
        SimHashDetector,
        ThompsonSamplingDomainRouter,
        TokenBucketRateLimiter,
        AutoRuleSchemaExtractor,
        CrawlingService,
        VeilEngine,
        TieredCrawlerService,
        TieredCrawler,
    )
    from veil.crawling.crawler import Crawler
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
