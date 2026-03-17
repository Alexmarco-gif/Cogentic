"""Source discovery service — makes the signal acquisition aperture grow dynamically.

When signals reference external URLs or data sources, this service:
1. Tracks them in the discovered_sources table (deduped by URL hash)
2. Increments mention counts and computes relevance scores
3. Promotes frequently-referenced or high-relevance sources to 'recommended' status
4. Provides an API for activating recommended sources as real SignalContracts

This replaces the static "280 seeded contracts" model with a living system
where the platform discovers new intelligence sources from the data it processes.

Think of it as: every signal the system ingests teaches it where to look next.
"""

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.ai.entity_extraction import SourceReference
from backend.models.discovered_source import DiscoveredSource
from backend.models.signal_contract import SignalContract

logger = logging.getLogger(__name__)

# Thresholds for automatic promotion
RECOMMEND_MIN_MENTIONS = 3  # Minimum signal mentions to recommend
RECOMMEND_MIN_RELEVANCE = 0.7  # Minimum relevance score to recommend
AUTO_ACTIVATE_MIN_MENTIONS = 10  # Auto-activate if very frequently referenced
AUTO_ACTIVATE_MIN_RELEVANCE = 0.85  # High relevance → auto-activate

# Domains to ignore (not useful as signal sources)
IGNORED_DOMAINS = frozenset(
    {
        "google.com",
        "facebook.com",
        "twitter.com",
        "x.com",
        "linkedin.com",
        "instagram.com",
        "youtube.com",
        "tiktok.com",
        "wikipedia.org",
        "github.com",
        "stackoverflow.com",
        "bit.ly",
        "t.co",
        "goo.gl",  # URL shorteners
    }
)

# Schedule tier mapping based on source type
SOURCE_TYPE_SCHEDULE = {
    "api": ("standard", "0 */1 * * *"),  # hourly
    "rss": ("standard", "0 */2 * * *"),  # every 2 hours
    "government": ("slow", "0 */6 * * *"),  # every 6 hours
    "news": ("standard", "0 */1 * * *"),  # hourly
    "research": ("daily", "0 6 * * *"),  # daily at 6am
    "social": ("realtime", "*/15 * * * *"),  # every 15 minutes
    "scraper": ("standard", "0 */3 * * *"),  # every 3 hours
    "unknown": ("slow", "0 */6 * * *"),  # default: every 6 hours
}


class SourceDiscoveryService:
    """Discovers and manages new signal sources from signal content.

    Called by the refinement pipeline for every signal processed.
    Manages the lifecycle: discovered → recommended → activated.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Called by refinement pipeline ─────────────────────────────────

    async def track_sources(
        self,
        sources: list[SourceReference],
        *,
        signal_id: UUID | None = None,
    ) -> int:
        """Track source references extracted from a signal.

        For each source URL:
        - If new: create a discovered_source record
        - If existing: increment mention_count, update relevance
        - If threshold met: promote to 'recommended'

        Args:
            sources: SourceReference objects from NER extraction.
            signal_id: The signal these sources were extracted from.

        Returns:
            Number of new sources discovered.
        """
        new_count = 0
        now = datetime.now(timezone.utc)

        for source in sources:
            try:
                url = self._normalize_url(source.url)
                domain = self._extract_domain(url)

                # Skip ignored domains
                if domain in IGNORED_DOMAINS:
                    continue

                # Check if already tracked by an active signal contract
                if await self._is_tracked_by_contract(url, domain):
                    continue

                url_hash = self._hash_url(url)

                # Upsert discovered source
                existing = await self._get_by_hash(url_hash)
                if existing:
                    existing.mention_count += 1
                    existing.last_seen_at = now
                    existing.relevance_score = self._compute_relevance(
                        existing.mention_count, existing.relevance_score
                    )
                    # Check for promotion
                    if (
                        existing.status == "discovered"
                        and existing.mention_count >= RECOMMEND_MIN_MENTIONS
                        and existing.relevance_score >= RECOMMEND_MIN_RELEVANCE
                    ):
                        existing.status = "recommended"
                        logger.info(
                            f"Source promoted to recommended: {domain} "
                            f"(mentions={existing.mention_count}, "
                            f"relevance={existing.relevance_score:.2f})"
                        )

                    # Auto-activate very high frequency + relevance sources
                    if (
                        existing.status == "recommended"
                        and existing.mention_count >= AUTO_ACTIVATE_MIN_MENTIONS
                        and existing.relevance_score >= AUTO_ACTIVATE_MIN_RELEVANCE
                    ):
                        # Infer industry from the signal that triggered this
                        inferred_industry_id = await self._infer_industry_id(
                            existing.first_seen_signal_id
                        )
                        if inferred_industry_id:
                            contract = await self.activate_source(
                                existing.id,
                                industry_id=inferred_industry_id,
                            )
                            if contract:
                                logger.info(
                                    f"Auto-activated source: {domain} → contract {contract.id}"
                                )
                else:
                    # Create new discovered source
                    discovered = DiscoveredSource(
                        id=uuid4(),
                        url=url,
                        url_hash=url_hash,
                        domain=domain,
                        name=source.name,
                        source_type=source.source_type
                        or self._infer_source_type(url, domain),
                        signal_type=self._infer_signal_type(
                            url, domain, source.source_type
                        ),
                        first_seen_signal_id=signal_id,
                        mention_count=1,
                        last_seen_at=now,
                        relevance_score=0.5,
                        status="discovered",
                    )
                    self.db.add(discovered)
                    new_count += 1

                await self.db.flush()

            except Exception as e:
                logger.debug(f"Failed to track source {source.url}: {e}")

        if new_count:
            logger.info(f"Discovered {new_count} new sources from signal {signal_id}")

        return new_count

    # ── Source Activation ─────────────────────────────────────────────

    async def activate_source(
        self,
        source_id: UUID,
        *,
        industry_id: UUID,
        name: str | None = None,
        description: str | None = None,
    ) -> SignalContract | None:
        """Activate a discovered source as a real SignalContract.

        Creates a functional contract with:
        - Real source_url (from the discovered source)
        - Inferred source_type, schedule_tier, refresh_cron
        - Extraction config based on source type

        Args:
            source_id: ID of the DiscoveredSource to activate.
            industry_id: Industry to associate the contract with.
            name: Optional contract name (defaults to source name/domain).
            description: Optional description.

        Returns:
            The created SignalContract, or None if source not found.
        """
        source = await self.db.get(DiscoveredSource, source_id)
        if not source:
            return None

        if source.status == "activated":
            logger.warning(f"Source {source_id} already activated")
            return None

        # Determine schedule
        schedule_tier, refresh_cron = SOURCE_TYPE_SCHEDULE.get(
            source.source_type, SOURCE_TYPE_SCHEDULE["unknown"]
        )

        # Build extraction config based on source type
        extraction_config = self._build_extraction_config(source)

        contract_name = name or source.name or f"Auto: {source.domain}"

        contract = SignalContract(
            id=uuid4(),
            name=contract_name,
            description=description or f"Auto-discovered source from {source.domain}",
            industry_id=industry_id,
            source_url=source.url,
            source_type=self._map_to_contract_source_type(source.source_type),
            schedule_tier=schedule_tier,
            refresh_cron=refresh_cron,
            extraction_config=extraction_config,
            is_active=True,
            status="active",
        )
        self.db.add(contract)

        # Update discovered source status
        source.status = "activated"
        source.activated_contract_id = contract.id

        await self.db.flush()

        logger.info(
            f"Activated source {source.domain} → contract {contract.id} "
            f"(type={contract.source_type}, tier={schedule_tier})"
        )
        return contract

    async def dismiss_source(self, source_id: UUID) -> bool:
        """Dismiss a discovered source (won't be recommended again)."""
        source = await self.db.get(DiscoveredSource, source_id)
        if not source:
            return False
        source.status = "dismissed"
        await self.db.flush()
        return True

    # ── Queries ───────────────────────────────────────────────────────

    async def get_recommended(
        self,
        *,
        limit: int = 20,
    ) -> list[DiscoveredSource]:
        """Get recommended sources (ready for activation)."""
        result = await self.db.execute(
            select(DiscoveredSource)
            .where(DiscoveredSource.status == "recommended")
            .order_by(DiscoveredSource.relevance_score.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_stats(self) -> dict[str, Any]:
        """Get source discovery statistics."""
        from sqlalchemy import func

        result = await self.db.execute(
            select(
                DiscoveredSource.status,
                func.count(DiscoveredSource.id).label("cnt"),
            ).group_by(DiscoveredSource.status)
        )
        stats: dict[str, int] = {row.status: row.cnt for row in result.all()}
        total = (
            stats.get("discovered", 0)
            + stats.get("recommended", 0)
            + stats.get("activated", 0)
            + stats.get("dismissed", 0)
        )
        return {
            "discovered": stats.get("discovered", 0),
            "recommended": stats.get("recommended", 0),
            "activated": stats.get("activated", 0),
            "dismissed": stats.get("dismissed", 0),
            "total": total,
        }

    # ── Helpers ───────────────────────────────────────────────────────

    async def _infer_industry_id(self, signal_id: UUID | None) -> UUID | None:
        """Infer industry_id from the signal that first referenced a source."""
        if not signal_id:
            return None
        from backend.models.signal import Signal

        signal = await self.db.get(Signal, signal_id)
        if signal and signal.contract_id:
            contract = await self.db.get(SignalContract, signal.contract_id)
            if contract:
                return contract.industry_id
        # Fallback: use the first industry in the database
        from backend.models.industry import Industry

        result = await self.db.execute(select(Industry.id).limit(1))
        return result.scalar_one_or_none()

    async def _get_by_hash(self, url_hash: str) -> DiscoveredSource | None:
        result = await self.db.execute(
            select(DiscoveredSource).where(DiscoveredSource.url_hash == url_hash)
        )
        return result.scalar_one_or_none()

    async def _is_tracked_by_contract(self, url: str, domain: str) -> bool:
        """Check if this URL or domain is already tracked by an active contract."""
        result = await self.db.execute(
            select(SignalContract.id)
            .where(
                SignalContract.is_active.is_(True),
                SignalContract.source_url.contains(domain),
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    @staticmethod
    def _normalize_url(url: str) -> str:
        """Normalize URL for consistent hashing."""
        url = url.strip().rstrip("/")
        # Remove tracking parameters
        parsed = urlparse(url)
        clean = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        return clean.lower()

    @staticmethod
    def _extract_domain(url: str) -> str:
        """Extract domain from URL."""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain

    @staticmethod
    def _hash_url(url: str) -> str:
        """SHA-256 hash of normalized URL."""
        return hashlib.sha256(url.encode()).hexdigest()

    @staticmethod
    def _compute_relevance(mention_count: int, current_score: float) -> float:
        """Compute relevance score based on mention frequency.

        Starts at 0.5, grows logarithmically with mentions.
        """
        import math

        base = 0.5
        growth = min(0.5, math.log2(mention_count + 1) / 10)
        return round(min(base + growth, 1.0), 4)

    @staticmethod
    def _infer_source_type(url: str, domain: str) -> str:
        """Infer source type from URL patterns."""
        if "/api/" in url or "api." in domain:
            return "api"
        if "/rss" in url or "/feed" in url or "rss" in domain:
            return "rss"
        if domain.endswith(".gov.ng") or domain.endswith(".gov"):
            return "government"
        if any(s in domain for s in ["twitter", "x.com", "facebook", "linkedin"]):
            return "social"
        if any(s in domain for s in ["reuters", "bloomberg", "guardian", "punch"]):
            return "news"
        if any(s in domain for s in ["arxiv", "ssrn", "researchgate"]):
            return "research"
        return "scraper"

    @staticmethod
    def _infer_signal_type(
        url: str, domain: str, source_type: str | None
    ) -> str | None:
        """Infer signal type from domain and source type."""
        if domain.endswith(".gov.ng") or domain.endswith(".gov"):
            return "regulatory"
        if any(s in domain for s in ["cbn.gov", "sec.gov", "ncc.gov", "nerc.gov"]):
            return "regulatory"
        if any(s in domain for s in ["exchange", "commodity", "market", "price"]):
            return "market"
        if any(s in domain for s in ["bank", "finance", "invest"]):
            return "financial"
        if source_type == "news":
            return "news"
        return None

    @staticmethod
    def _map_to_contract_source_type(discovered_type: str) -> str:
        """Map discovered source_type to SignalContract source_type enum."""
        mapping = {
            "api": "api",
            "rss": "rss",
            "government": "scraper",
            "news": "scraper",
            "research": "scraper",
            "social": "social",
            "scraper": "scraper",
            "unknown": "scraper",
        }
        return mapping.get(discovered_type, "scraper")

    @staticmethod
    def _build_extraction_config(source: DiscoveredSource) -> dict[str, Any]:
        """Build a basic extraction config for a newly activated source.

        Returns a sensible default config — can be refined manually later.
        """
        config: dict[str, Any] = {
            "auto_discovered": True,
            "discovery_domain": source.domain,
            "discovery_mentions": source.mention_count,
        }

        if source.source_type == "rss":
            config["parser"] = "rss"
            config["max_items"] = 20
        elif source.source_type == "api":
            config["parser"] = "json"
            config["response_format"] = "json"
        elif source.source_type in ("government", "news", "scraper"):
            config["parser"] = "html"
            config["selectors"] = {
                "title": "h1, .article-title, .headline",
                "content": "article, .content, .article-body, main",
                "date": "time, .date, .published",
            }

        return config
