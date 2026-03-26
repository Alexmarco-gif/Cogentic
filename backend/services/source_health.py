"""Source health monitoring service.

Tracks operational health of signal contracts — especially auto-discovered ones.
Computes freshness scores, failure streaks, and overall health status.

Used by:
  - GET /api/v1/pipeline/source-health — admin dashboard
  - Scheduler health check job — flags degraded sources
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.discovered_source import DiscoveredSource
from backend.models.signal import Signal
from backend.models.signal_contract import SignalContract

logger = logging.getLogger(__name__)

# Health thresholds
STALE_HOURS = 48  # No signals for 48h → stale
DEGRADED_FAILURE_COUNT = 3  # 3+ failures → degraded
CRITICAL_FAILURE_COUNT = 10  # 10+ failures → critical


class SourceHealthService:
    """Monitors operational health of signal contracts and discovered sources."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_health_summary(
        self,
        *,
        org_id: UUID | None = None,
    ) -> dict[str, Any]:
        """Compute overall source health summary.

        Returns:
            Dict with counts by health band, total contracts,
            and lists of stale/degraded/critical contracts.
        """
        now = datetime.now(timezone.utc)
        stale_cutoff = now - timedelta(hours=STALE_HOURS)

        # Get all active contracts
        query = select(SignalContract).where(SignalContract.is_active.is_(True))
        if org_id is not None:
            query = query.where(
                or_(SignalContract.org_id == org_id, SignalContract.org_id.is_(None))
            )
        result = await self.db.execute(query)
        contracts = list(result.scalars().all())

        healthy = []
        stale = []
        degraded = []
        critical = []

        for c in contracts:
            health = self._classify_contract_health(c, stale_cutoff)
            entry = {
                "id": str(c.id),
                "name": c.name,
                "source_url": c.source_url,
                "source_type": c.source_type,
                "schedule_tier": c.schedule_tier,
                "status": c.status,
                "failure_count": c.failure_count,
                "last_fetched_at": c.last_fetched_at.isoformat()
                if c.last_fetched_at
                else None,
                "last_error": c.last_error,
                "health": health,
                "is_auto_discovered": await self._is_auto_discovered(c.id),
            }

            if health == "critical":
                critical.append(entry)
            elif health == "degraded":
                degraded.append(entry)
            elif health == "stale":
                stale.append(entry)
            else:
                healthy.append(entry)

        return {
            "total_active": len(contracts),
            "healthy": len(healthy),
            "stale": len(stale),
            "degraded": len(degraded),
            "critical": len(critical),
            "stale_contracts": stale,
            "degraded_contracts": degraded,
            "critical_contracts": critical,
            "auto_discovered_active": await self._count_auto_discovered(),
        }

    async def get_contract_health(
        self,
        contract_id: UUID,
        *,
        org_id: UUID | None = None,
    ) -> dict[str, Any] | None:
        """Get detailed health for a single contract.

        Includes recent signal delivery history and freshness metrics.
        """
        contract = await self.db.get(SignalContract, contract_id)
        if not contract:
            return None
        if (
            org_id is not None
            and contract.org_id is not None
            and contract.org_id != org_id
        ):
            return None

        now = datetime.now(timezone.utc)
        stale_cutoff = now - timedelta(hours=STALE_HOURS)

        # Recent signal count (last 24h, 7d, 30d)
        signals_24h = await self._count_signals_since(
            contract_id, now - timedelta(hours=24)
        )
        signals_7d = await self._count_signals_since(
            contract_id, now - timedelta(days=7)
        )
        signals_30d = await self._count_signals_since(
            contract_id, now - timedelta(days=30)
        )

        # Freshness: time since last signal
        last_signal_at = await self._last_signal_time(contract_id)
        hours_since_signal = None
        if last_signal_at:
            hours_since_signal = round((now - last_signal_at).total_seconds() / 3600, 1)

        return {
            "id": str(contract.id),
            "name": contract.name,
            "source_url": contract.source_url,
            "source_type": contract.source_type,
            "schedule_tier": contract.schedule_tier,
            "status": contract.status,
            "failure_count": contract.failure_count,
            "max_failures": contract.max_failures,
            "last_fetched_at": contract.last_fetched_at.isoformat()
            if contract.last_fetched_at
            else None,
            "last_error": contract.last_error,
            "health": self._classify_contract_health(contract, stale_cutoff),
            "is_auto_discovered": await self._is_auto_discovered(contract.id),
            "signals_24h": signals_24h,
            "signals_7d": signals_7d,
            "signals_30d": signals_30d,
            "last_signal_at": last_signal_at.isoformat() if last_signal_at else None,
            "hours_since_signal": hours_since_signal,
        }

    # ── Classification ───────────────────────────────────────────────

    @staticmethod
    def _classify_contract_health(
        contract: SignalContract,
        stale_cutoff: datetime,
    ) -> str:
        """Classify a contract's health status.

        Returns: 'healthy', 'stale', 'degraded', or 'critical'
        """
        if contract.failure_count >= CRITICAL_FAILURE_COUNT:
            return "critical"
        if contract.failure_count >= DEGRADED_FAILURE_COUNT:
            return "degraded"
        if contract.last_fetched_at and contract.last_fetched_at < stale_cutoff:
            return "stale"
        if not contract.last_fetched_at:
            return "stale"
        return "healthy"

    # ── Queries ──────────────────────────────────────────────────────

    async def _count_signals_since(self, contract_id: UUID, since: datetime) -> int:
        result = await self.db.execute(
            select(func.count(Signal.id)).where(
                Signal.contract_id == contract_id,
                Signal.fetched_at >= since,
            )
        )
        return result.scalar() or 0

    async def _last_signal_time(self, contract_id: UUID) -> datetime | None:
        result = await self.db.execute(
            select(Signal.fetched_at)
            .where(Signal.contract_id == contract_id)
            .order_by(Signal.fetched_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _is_auto_discovered(self, contract_id: UUID) -> bool:
        result = await self.db.execute(
            select(DiscoveredSource.id)
            .where(DiscoveredSource.activated_contract_id == contract_id)
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def _count_auto_discovered(self) -> int:
        result = await self.db.execute(
            select(func.count(DiscoveredSource.id)).where(
                DiscoveredSource.status == "activated"
            )
        )
        return result.scalar() or 0
