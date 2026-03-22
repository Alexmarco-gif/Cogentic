"""Intelligence Brief Generator.

Orchestrates AI synthesis to create and regenerate intelligence briefs.
Wraps the SynthesisService and IntelligenceBriefRepository to produce
structured brief content persisted to the database.

Usage:
    generator = BriefGenerator(db)
    brief = await generator.generate_brief(topic="CBN rate decision", ...)
    brief = await generator.regenerate_brief(brief_id=uuid, ...)
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.briefs.schema import normalize_brief_body
from backend.models.brief_signal import BriefSignal
from backend.models.intelligence_brief import IntelligenceBrief
from backend.repositories.intelligence_brief import IntelligenceBriefRepository

logger = logging.getLogger(__name__)


class BriefGenerator:
    """Generates and regenerates intelligence briefs using AI synthesis.

    Wraps RAG synthesis (SynthesisService) to produce the same structured brief
    schema rendered by the signal drawer UI.

    Raises clearly when AI synthesis is unavailable so callers do not mistake
    placeholder content for production intelligence.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_brief(
        self,
        *,
        topic: str,
        industry_id: UUID | None = None,
        org_id: UUID | None = None,
        signal_ids: list[str] | None = None,
    ) -> IntelligenceBrief:
        """Generate a new intelligence brief for the given topic.

        Args:
            topic: Natural-language topic for synthesis (e.g. "CBN rate decision impact")
            industry_id: Optional industry UUID to scope the brief.
            org_id: Owning organisation UUID (None for global briefs).
            signal_ids: Optional list of specific signal UUIDs to include.

        Returns:
            Persisted IntelligenceBrief in "published" status.
        """
        logger.info(
            f"Generating brief: topic={topic!r} org_id={org_id} signals={len(signal_ids or [])}"
        )

        synthesis_result = await self._run_synthesis(topic, signal_ids)

        # Resolve industry fallback: use first available industry UUID if not provided
        if industry_id is None:
            industry_id = await self._resolve_default_industry()

        brief = IntelligenceBrief(
            id=uuid4(),
            org_id=org_id,
            industry_id=industry_id,
            title=synthesis_result.get("title", topic),
            brief_type="auto_generated",
            bluf=synthesis_result.get("bluf", ""),
            body_json=synthesis_result.get("body_json", {}),
            outlook=synthesis_result.get("outlook", ""),
            decision_lens=synthesis_result.get("decision_lens", ""),
            status="published",
            refreshed_at=datetime.now(timezone.utc),
        )

        self.db.add(brief)
        await self.db.flush()
        brief.signal_links = await self._sync_signal_links(
            brief.id, synthesis_result.get("signal_ids", [])
        )
        await self.db.refresh(brief)

        logger.info(f"Brief generated: id={brief.id} title={brief.title!r}")
        return brief

    async def regenerate_brief(
        self,
        *,
        brief_id: UUID,
        signal_ids: list[str] | None = None,
        org_id: UUID | None = None,
    ) -> IntelligenceBrief:
        """Regenerate an existing brief with fresh AI synthesis.

        Fetches the existing brief, re-runs synthesis on its topic,
        and updates the content fields + refreshed_at timestamp.

        Args:
            brief_id: UUID of the brief to regenerate.
            signal_ids: Optional updated signal set for this run.
            org_id: Organisation UUID for repo scoping (uses zero UUID if None).

        Returns:
            Updated IntelligenceBrief.

        Raises:
            ValueError: If the brief is not found.
        """
        scope_org_id = org_id or UUID(int=0)
        repo = IntelligenceBriefRepository(self.db, org_id=scope_org_id)

        brief = await repo.get(brief_id)
        if brief is None:
            raise ValueError(f"Brief {brief_id} not found")

        topic = brief.title
        logger.info(f"Regenerating brief: id={brief_id} topic={topic!r}")

        synthesis_result = await self._run_synthesis(topic, signal_ids)

        updated = await repo.update(
            brief_id,
            title=synthesis_result.get("title", topic),
            bluf=synthesis_result.get("bluf", brief.bluf or ""),
            body_json=synthesis_result.get("body_json", brief.body_json or {}),
            outlook=synthesis_result.get("outlook", brief.outlook or ""),
            decision_lens=synthesis_result.get(
                "decision_lens", brief.decision_lens or ""
            ),
            refreshed_at=datetime.now(timezone.utc),
        )

        if updated is None:
            raise ValueError(f"Failed to update brief {brief_id}")

        updated.signal_links = await self._sync_signal_links(
            brief_id, synthesis_result.get("signal_ids", [])
        )
        logger.info(f"Brief regenerated: id={brief_id}")
        return updated

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _run_synthesis(
        self,
        topic: str,
        signal_ids: list[str] | None,
    ) -> dict[str, Any]:
        """Run AI synthesis and return structured brief fields.

        Attempts to use SynthesisService and raises if AI synthesis fails.
        """
        try:
            from backend.ai.synthesis import SynthesisService

            synthesis = SynthesisService(self.db)
            result = await synthesis.synthesize_brief(
                topic=topic,
                signal_ids=signal_ids,
            )
            return self._map_synthesis_result(topic, result)
        except Exception as exc:
            logger.error(
                "AI synthesis unavailable for topic %r: %s",
                topic,
                exc,
            )
            raise RuntimeError(
                "AI synthesis is unavailable; brief generation cannot continue"
            ) from exc

    def _map_synthesis_result(
        self, topic: str, result: dict[str, Any]
    ) -> dict[str, Any]:
        """Map synthesis output to persisted brief fields."""
        body_json = normalize_brief_body(
            result,
            topic=topic,
            summary=result.get("bluf") or result.get("summary"),
            domain=result.get("domain"),
            confidence=result.get("confidence"),
            outlook=result.get("outlook"),
            decision_lens=result.get("decision_lens")
            or result.get("recommendation"),
        )
        bottom_line = (
            body_json.get("executive_summary", {}).get("bottom_line")
            or result.get("bluf")
            or result.get("summary")
            or ""
        )
        return {
            "title": result.get("title") or topic,
            "bluf": bottom_line,
            "body_json": body_json,
            "outlook": body_json.get("outlook") or result.get("outlook") or "",
            "decision_lens": body_json.get("decision_lens")
            or result.get("decision_lens")
            or result.get("recommendation")
            or "",
            "signal_ids": result.get("signal_ids") or [],
        }

    async def _sync_signal_links(
        self,
        brief_id: UUID,
        signal_ids: list[str] | None,
    ) -> list[BriefSignal]:
        """Replace persisted brief-signal links with the latest ranked signal set."""

        await self.db.execute(delete(BriefSignal).where(BriefSignal.brief_id == brief_id))

        normalized_ids: list[UUID] = []
        seen: set[UUID] = set()
        for raw_signal_id in signal_ids or []:
            try:
                signal_id = UUID(str(raw_signal_id))
            except (TypeError, ValueError):
                continue
            if signal_id in seen:
                continue
            seen.add(signal_id)
            normalized_ids.append(signal_id)

        links = [
            BriefSignal(
                brief_id=brief_id,
                signal_id=signal_id,
                relevance_rank=index + 1,
            )
            for index, signal_id in enumerate(normalized_ids)
        ]
        if links:
            self.db.add_all(links)
            await self.db.flush()
        return links

    async def _resolve_default_industry(self) -> UUID:
        """Return the first available industry UUID from the database.

        Falls back to a zero UUID if no industries exist yet (e.g. fresh DB).
        """
        try:
            from sqlalchemy import select

            from backend.models.industry import Industry

            result = await self.db.execute(select(Industry).limit(1))
            industry = result.scalar_one_or_none()
            if industry:
                return industry.id
        except Exception as exc:
            logger.warning(f"Could not resolve default industry: {exc}")
        return UUID(int=0)
