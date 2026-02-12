"""Intelligence brief generator.

Generates structured briefs from signals using AI synthesis.
Structure: BLUF → Argument + Evidence → Outlook → Decision Lens.
Persists to IntelligenceBrief model with body_json structured content.
Supports both pre_built and auto_generated brief types.
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Any
from uuid import UUID

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from backend.ai.embeddings import EmbeddingService
from backend.ai.guardrails import get_guardrails
from backend.ai.synthesis import SynthesisService
from backend.config import get_settings
from backend.models.brief_signal import BriefSignal
from backend.models.intelligence_brief import IntelligenceBrief
from backend.repositories.intelligence_brief import IntelligenceBriefRepository

logger = logging.getLogger(__name__)
settings = get_settings()

_openai_client: AsyncOpenAI | None = None


def _get_openai_client() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _openai_client


class BriefGenerator:
    """Generates intelligence briefs from signals using GPT-4o.

    Pipeline:
      1. Gather relevant signals for topic (via BriefSignal junction or search)
      2. Generate BLUF using GPT-4o
      3. Structure argument with evidence (confidence-scored sources)
      4. Generate outlook and implications
      5. Decision Lens generation
      6. Persist to IntelligenceBrief model with body_json

    Supports:
      - pre_built: Template-based briefs with known signal sets
      - auto_generated: On-demand briefs from query/topic
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.client = _get_openai_client()
        self.guardrails = get_guardrails()
        self.synthesis = SynthesisService(db)
        self.embedding_service = EmbeddingService(db)

    async def generate_brief(
        self,
        *,
        title: str,
        industry_id: UUID,
        org_id: UUID | None = None,
        topic: str | None = None,
        signal_ids: list[UUID] | None = None,
        brief_type: str = "auto_generated",
    ) -> IntelligenceBrief:
        """Generate a full intelligence brief.

        Either provide signal_ids (pre_built) or topic (auto_generated).

        Args:
            title: Brief title.
            industry_id: Industry scope.
            org_id: Org scope (NULL = global).
            topic: Topic for auto signal retrieval.
            signal_ids: Explicit signal list (for pre_built).
            brief_type: 'pre_built' or 'auto_generated'.

        Returns:
            Persisted IntelligenceBrief model.
        """
        start = time.monotonic()

        # Sanitize topic if provided
        if topic:
            sanitized = self.guardrails.sanitize_input(
                topic, max_length=500, context="brief"
            )
            topic = sanitized.text

        # Step 1: Gather signals
        if signal_ids:
            signals = await self._get_signals_by_ids(signal_ids)
        elif topic:
            signals = await self._search_signals_for_topic(
                topic, org_id=org_id, industry_id=industry_id
            )
        else:
            signals = []

        if not signals:
            logger.warning(f"No signals found for brief '{title}'")
            # Create a draft brief with no content
            brief = IntelligenceBrief(
                title=title,
                brief_type=brief_type,
                industry_id=industry_id,
                org_id=org_id,
                status="draft",
                bluf="Insufficient signal coverage to generate this brief.",
                body_json={"argument": [], "evidence": [], "limitations": ["No signals available"]},
                outlook=None,
                decision_lens=None,
                refreshed_at=datetime.utcnow(),
            )
            self.db.add(brief)
            await self.db.flush()
            await self.db.refresh(brief)
            return brief

        # Step 2: Generate brief content via GPT-4o
        content = await self._generate_content(title, signals, topic=topic)

        # Step 3: Persist to IntelligenceBrief
        brief = IntelligenceBrief(
            title=title,
            brief_type=brief_type,
            industry_id=industry_id,
            org_id=org_id,
            status="published",
            bluf=content.get("bluf", ""),
            body_json={
                "argument": content.get("argument", []),
                "evidence": content.get("evidence", []),
                "key_signals": content.get("key_signals", []),
                "limitations": content.get("limitations", []),
            },
            outlook=content.get("outlook", ""),
            decision_lens=content.get("decision_lens", ""),
            refreshed_at=datetime.utcnow(),
        )
        self.db.add(brief)
        await self.db.flush()
        await self.db.refresh(brief)

        # Step 4: Create BriefSignal junction records
        for rank, sig in enumerate(signals, 1):
            link = BriefSignal(
                brief_id=brief.id,
                signal_id=UUID(sig["id"]) if isinstance(sig["id"], str) else sig["id"],
                relevance_rank=rank,
            )
            self.db.add(link)
        await self.db.flush()

        duration_ms = int((time.monotonic() - start) * 1000)
        logger.info(
            f"Brief '{title}' generated: {len(signals)} signals, "
            f"{duration_ms}ms, type={brief_type}"
        )

        return brief

    async def regenerate_brief(
        self,
        brief_id: UUID,
        org_id: UUID,
    ) -> IntelligenceBrief | None:
        """Regenerate an existing brief with updated signal data.

        Used by the auto-refresh system.

        Args:
            brief_id: Existing brief ID.
            org_id: Org scope for repository.

        Returns:
            Updated IntelligenceBrief or None if not found.
        """
        repo = IntelligenceBriefRepository(self.db, org_id)
        brief = await repo.get_with_signals(brief_id)
        if not brief:
            return None

        # Gather current linked signal IDs
        signal_ids = [link.signal_id for link in brief.signal_links]

        if signal_ids:
            signals = await self._get_signals_by_ids(signal_ids)
        else:
            # Fall back to topic search using the brief title
            signals = await self._search_signals_for_topic(
                brief.title,
                org_id=org_id if brief.org_id else None,
                industry_id=brief.industry_id,
            )

        if not signals:
            logger.warning(f"No signals for brief refresh: {brief_id}")
            return brief

        # Re-generate content
        content = await self._generate_content(brief.title, signals)

        # Update brief fields
        brief.bluf = content.get("bluf", brief.bluf)
        brief.body_json = {
            "argument": content.get("argument", []),
            "evidence": content.get("evidence", []),
            "key_signals": content.get("key_signals", []),
            "limitations": content.get("limitations", []),
        }
        brief.outlook = content.get("outlook", brief.outlook)
        brief.decision_lens = content.get("decision_lens", brief.decision_lens)
        brief.refreshed_at = datetime.utcnow()

        await self.db.flush()
        logger.info(f"Brief '{brief.title}' regenerated ({len(signals)} signals)")
        return brief

    # ── Signal Retrieval ─────────────────────────────────────────────

    async def _get_signals_by_ids(
        self, signal_ids: list[UUID]
    ) -> list[dict[str, Any]]:
        """Fetch signals by explicit IDs."""
        from backend.models.signal import Signal
        from sqlalchemy import select

        result = await self.db.execute(
            select(Signal).where(Signal.id.in_(signal_ids))
        )
        rows = result.scalars().all()

        return [
            {
                "id": str(s.id),
                "title": s.title or "Untitled Signal",
                "summary": s.summary or "",
                "confidence": float(s.confidence),
                "signal_type": s.signal_type,
                "source_url": s.source_url,
                "published_at": s.published_at.isoformat() if s.published_at else None,
            }
            for s in rows
        ]

    async def _search_signals_for_topic(
        self,
        topic: str,
        *,
        org_id: UUID | None = None,
        industry_id: UUID | None = None,
        top_k: int = 14,
    ) -> list[dict[str, Any]]:
        """Search for relevant signals using embedding similarity."""
        query_embedding = await self.embedding_service.generate_query_embedding(topic)

        # Reuse synthesis retrieval logic
        return await self.synthesis._retrieve_signals(
            query_embedding,
            org_id=org_id,
            industry_id=industry_id,
            top_k=top_k,
            min_confidence=0.60,
        )

    # ── LLM Content Generation ───────────────────────────────────────

    async def _generate_content(
        self,
        title: str,
        signals: list[dict[str, Any]],
        *,
        topic: str | None = None,
    ) -> dict[str, Any]:
        """Generate structured brief content via GPT-4o.

        Returns dict with: bluf, argument, evidence, outlook, decision_lens, limitations.
        """
        system_prompt = self.guardrails.get_system_prompt("brief")

        # Build evidence context
        evidence_blocks = []
        for i, sig in enumerate(signals, 1):
            block = (
                f"[Signal {i}] {sig['title']}\n"
                f"  Type: {sig['signal_type']} | Confidence: {sig['confidence']:.2f}\n"
                f"  Summary: {sig['summary'][:400]}"
            )
            evidence_blocks.append(block)

        evidence_text = "\n\n".join(evidence_blocks)

        user_prompt = f"""Generate an intelligence brief with this structure.

Title: {title}
{f'Topic Context: {topic}' if topic else ''}

Source Signals ({len(signals)}):
{evidence_text}

Generate the brief in this EXACT JSON format:
{{
  "bluf": "2 sentences max. Bottom Line Up Front.",
  "argument": ["Point 1 citing [Signal N]...", "Point 2..."],
  "evidence": [
    {{"signal_ref": "Signal 1", "signal_title": "...", "confidence": 0.85, "contribution": "What this signal shows..."}},
  ],
  "key_signals": ["signal_id_1", "signal_id_2"],
  "outlook": "Forward-looking analysis paragraph",
  "decision_lens": "What this means for you: ...",
  "limitations": ["Limitation 1", "Limitation 2"]
}}

Rules:
- BLUF must be exactly 2 sentences
- Every argument point must cite [Signal N]
- Outlook must be forward-looking and actionable
- Decision Lens must start with "What this means for you:"
- List specific limitations and data gaps
- Include confidence scores in evidence entries
"""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=2500,
                response_format={"type": "json_object"},
            )

            raw = response.choices[0].message.content or "{}"

            # Filter through guardrails
            filtered = self.guardrails.filter_output(raw, context="brief")
            content = _safe_json_parse(filtered.text)

            # Map key_signals to actual IDs from retrieved signals
            key_refs = content.get("key_signals", [])
            actual_ids = []
            for ref in key_refs:
                # If the LLM returned signal IDs, keep them
                if isinstance(ref, str) and len(ref) == 36:
                    actual_ids.append(ref)
            # Fallback: use top signals by order
            if not actual_ids:
                actual_ids = [s["id"] for s in signals[:5]]
            content["key_signals"] = actual_ids

            return content

        except Exception as e:
            logger.error(f"Brief generation LLM call failed: {e}")
            return {
                "bluf": f"Brief generation is temporarily unavailable for '{title}'.",
                "argument": [],
                "evidence": [
                    {
                        "signal_ref": f"Signal {i+1}",
                        "signal_title": s["title"],
                        "confidence": s["confidence"],
                        "contribution": s["summary"][:200],
                    }
                    for i, s in enumerate(signals[:5])
                ],
                "key_signals": [s["id"] for s in signals[:5]],
                "outlook": "Analysis pending — LLM synthesis temporarily unavailable.",
                "decision_lens": "What this means for you: manual signal review recommended.",
                "limitations": [f"AI generation failed: {str(e)[:100]}"],
            }


def _safe_json_parse(text: str) -> dict[str, Any]:
    """Parse JSON from LLM output, handling markdown wrapping."""
    import json
    import re

    # Strip markdown code block if present
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning(f"Failed to parse brief JSON: {text[:200]}...")
        return {}
