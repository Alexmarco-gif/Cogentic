"""Dynamic Regulatory Intelligence Service.

NOT a static rule engine — this is a learning system that:
- Automatically extracts regulatory knowledge from signals
- Applies context-aware interpretation to new signals
- Learns from historical impacts to improve predictions
- Evolves as domain experts provide feedback

This is the "unreplicable business context" moat.
"""

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

import numpy as np
from dateutil import parser as dateparser
from rapidfuzz import fuzz
from sqlalchemy import and_, desc, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.ai.embeddings import EmbeddingService
from backend.models.regulatory_knowledge import (
    RegulatoryEvent,
    RegulatoryImpact,
    RegulatoryPattern,
    RegulatoryRule,
)
from backend.models.signal import Signal
from backend.services.knowledge_service import KnowledgeService

logger = logging.getLogger(__name__)


class RegulatoryIntelligenceService:
    """Dynamic regulatory knowledge base and contextual interpretation engine."""

    # Regulatory body names — now loaded from DB at runtime via KnowledgeService.
    # Kept as an empty class-level fallback so static references don't break.
    REGULATORY_BODIES: dict[str, list[str]] = {}

    # Event type detection patterns (generic regex — NOT country-specific)
    EVENT_PATTERNS = {
        "policy_change": [
            r"new policy",
            r"policy change",
            r"policy update",
            r"revised policy",
            r"policy framework",
            r"regulatory framework",
        ],
        "rate_adjustment": [
            r"rate (increase|decrease|adjustment)",
            r"MPR",
            r"monetary policy rate",
            r"interest rate",
            r"CRR",
            r"cash reserve ratio",
        ],
        "license_requirement": [
            r"licens(e|ing) requirement",
            r"applies? for licens",
            r"obtain.*licens",
            r"registration requirement",
        ],
        "enforcement_action": [
            r"penalti(es|zed)",
            r"sanction(ed|s)",
            r"violation",
            r"non-compliance",
            r"enforcement",
            r"revok(ed|ation)",
            r"suspend(ed|sion)",
        ],
        "compliance_deadline": [
            r"deadline",
            r"must comp",
            r"required.*by",
            r"within.*days",
            r"not later than",
            r"expires?",
        ],
        "regulatory_consultation": [
            r"public consultation",
            r"stakeholder engagement",
            r"request.*comment",
            r"draft.*regulation",
            r"proposed.*rule",
        ],
    }

    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding_service = EmbeddingService(db)
        self.knowledge = KnowledgeService(db)
        # Runtime caches (populated on first use per request)
        self._regulatory_bodies: dict[str, list[str]] | None = None
        self._sector_keywords: dict[str, list[str]] | None = None
        self._entity_type_keywords: dict[str, list[str]] | None = None

    async def _get_regulatory_bodies(self) -> dict[str, list[str]]:
        """Lazy-load regulatory bodies from DB."""
        if self._regulatory_bodies is None:
            self._regulatory_bodies = await self.knowledge.get_regulatory_bodies()
        return self._regulatory_bodies

    async def _get_sector_keywords(self) -> dict[str, list[str]]:
        """Lazy-load sector keywords from DB."""
        if self._sector_keywords is None:
            self._sector_keywords = await self.knowledge.get_sector_keywords()
        return self._sector_keywords

    async def _get_entity_type_keywords(self) -> dict[str, list[str]]:
        """Lazy-load entity type keywords from DB."""
        if self._entity_type_keywords is None:
            self._entity_type_keywords = await self.knowledge.get_entity_type_keywords()
        return self._entity_type_keywords

    # ── Automatic Knowledge Extraction ──────────────────────────────

    async def extract_regulatory_event_from_signal(
        self,
        signal: Signal,
        *,
        auto_create: bool = True,
    ) -> RegulatoryEvent | None:
        """Automatically detect and extract regulatory events from signals.

        Uses NLP patterns + ML embeddings to identify regulatory content,
        then structures it into the knowledge base.

        Args:
            signal: Signal to analyze
            auto_create: If True, create event if detected

        Returns:
            RegulatoryEvent if detected, None otherwise
        """
        signal_text = self._get_signal_text(signal)

        # Detect regulatory body mention
        issuing_body = await self._detect_regulatory_body(signal_text)
        if not issuing_body:
            return None  # Not a regulatory signal

        # Detect event type
        event_type = self._detect_event_type(signal_text)
        if not event_type:
            return None

        # Extract temporal information
        temporal_data = self._extract_temporal_data(signal_text)

        # Extract affected sectors and entities
        affected_sectors = await self._extract_affected_sectors(signal_text)
        affected_entity_types = await self._extract_affected_entity_types(signal_text)

        # Calculate severity score (ML-based would be better, but heuristic for now)
        severity_score = self._estimate_severity(signal_text, event_type)

        # Generate content embedding for semantic search
        content_text = f"{signal.title or ''} {(signal.raw_content or '')[:500]}"
        content_embedding = await self.embedding_service.generate_query_embedding(
            content_text
        )

        if not auto_create:
            # Just return detection result
            return {
                "detected": True,
                "issuing_body": issuing_body,
                "event_type": event_type,
                "severity_score": severity_score,
            }  # type: ignore

        # Create regulatory event
        reg_event = RegulatoryEvent(
            id=uuid4(),
            event_type=event_type,
            title=signal.title or signal.summary,
            description=signal_text[:2000],  # Truncate if too long
            source_signal_id=signal.id,
            source_url=signal.source_url,
            issuing_body=issuing_body,
            announced_at=signal.published_at or datetime.now(timezone.utc),
            effective_date=temporal_data.get("effective_date"),
            deadline_date=temporal_data.get("deadline_date"),
            affected_sectors=affected_sectors,
            affected_entity_types=affected_entity_types,
            severity_score=severity_score,
            compliance_complexity=0.5,  # Default, can be refined
            requirements=self._extract_structured_requirements(
                signal_text, temporal_data
            ),
            exemptions={},
            penalties={},
            historical_precedents=[],
            confidence_score=0.7,  # Automated extraction confidence
            verified_by_expert=False,
            content_embedding=content_embedding,
        )

        self.db.add(reg_event)
        await self.db.flush()

        logger.info(
            f"Extracted regulatory event: {event_type} from {issuing_body} "
            f"(signal {signal.id})"
        )

        return reg_event

    @staticmethod
    def _get_signal_text(signal: Signal) -> str:
        """Get the best available text for regulatory analysis."""
        if signal.raw_content:
            return signal.raw_content
        if signal.summary:
            return signal.summary
        if signal.title:
            return signal.title
        return ""

    async def _detect_regulatory_body(self, text: str) -> str | None:
        """Detect which regulatory body is mentioned (DB-driven)."""
        text_lower = text.lower()
        bodies = await self._get_regulatory_bodies()

        for body_code, variants in bodies.items():
            for variant in variants:
                if variant.lower() in text_lower:
                    return body_code

        return None

    def _detect_event_type(self, text: str) -> str | None:
        """Detect event type using pattern matching."""
        text_lower = text.lower()

        scores = {}
        for event_type, patterns in self.EVENT_PATTERNS.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    score += 1
            scores[event_type] = score

        # Return highest scoring type (if score > 0)
        if scores:
            best_type = max(scores, key=scores.get)
            if scores[best_type] > 0:
                return best_type

        return None

    def _extract_temporal_data(self, text: str) -> dict[str, Any]:
        """Extract dates and deadlines from text using dateutil."""
        temporal_data: dict[str, Any] = {}

        # Look for "effective from X" patterns
        effective_match = re.search(
            r"effective\s+(?:from\s+)?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            text,
            re.IGNORECASE,
        )
        if effective_match:
            try:
                temporal_data["effective_date"] = dateparser.parse(
                    effective_match.group(1), dayfirst=True
                )
            except (ValueError, OverflowError):
                temporal_data["effective_date"] = None

        # Look for deadline patterns
        deadline_match = re.search(
            r"(?:by|before|deadline|not later than)\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            text,
            re.IGNORECASE,
        )
        if deadline_match:
            try:
                temporal_data["deadline_date"] = dateparser.parse(
                    deadline_match.group(1), dayfirst=True
                )
            except (ValueError, OverflowError):
                temporal_data["deadline_date"] = None

        return temporal_data

    async def _extract_affected_sectors(self, text: str) -> list[str]:
        """Extract affected industry sectors (DB-driven)."""
        sectors = []
        sector_keywords = await self._get_sector_keywords()

        text_lower = text.lower()
        for sector, keywords in sector_keywords.items():
            if any(kw in text_lower for kw in keywords):
                sectors.append(sector)

        return sectors or ["general"]

    async def _extract_affected_entity_types(self, text: str) -> list[str]:
        """Extract affected entity types (DB-driven)."""
        entity_types = []
        entity_keywords = await self._get_entity_type_keywords()

        text_lower = text.lower()
        for entity_type, keywords in entity_keywords.items():
            if any(kw in text_lower for kw in keywords):
                entity_types.append(entity_type)

        return entity_types or ["all_entities"]

    def _estimate_severity(self, text: str, event_type: str) -> float:
        """Estimate regulatory severity (0-1 scale)."""
        # Base severity by event type
        base_severity = {
            "policy_change": 0.7,
            "rate_adjustment": 0.6,
            "license_requirement": 0.8,
            "enforcement_action": 0.9,
            "compliance_deadline": 0.5,
            "regulatory_consultation": 0.3,
        }.get(event_type, 0.5)

        # Adjust based on content urgency indicators
        text_lower = text.lower()
        urgency_keywords = {
            "immediate": 0.2,
            "mandatory": 0.15,
            "all entities": 0.1,
            "penalty": 0.1,
            "revoke": 0.15,
            "suspend": 0.1,
        }

        severity_boost = sum(
            boost
            for keyword, boost in urgency_keywords.items()
            if keyword in text_lower
        )

        return min(base_severity + severity_boost, 1.0)

    # ── Contextual Interpretation ───────────────────────────────────

    def _extract_structured_requirements(
        self, text: str, temporal_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Extract deterministic compliance requirements from narrative text."""
        if not text:
            return {}

        sentences = [
            sentence.strip(" \n\r\t.;:-")
            for sentence in re.split(r"(?<=[.!?])\s+", text)
            if sentence.strip()
        ]
        obligation_keywords = (
            "must",
            "shall",
            "required to",
            "requirement",
            "comply",
            "compliance",
            "submit",
            "file",
            "report",
            "register",
            "obtain",
            "maintain",
            "disclose",
            "implement",
        )
        filing_keywords = ("submit", "file", "report", "disclose", "register")
        control_keywords = (
            "maintain",
            "implement",
            "control",
            "policy",
            "procedure",
        )

        obligations: list[str] = []
        filings: list[str] = []
        controls: list[str] = []

        for sentence in sentences:
            lowered = sentence.lower()
            if not any(keyword in lowered for keyword in obligation_keywords):
                continue

            normalized = sentence[:300]
            obligations.append(normalized)

            if any(keyword in lowered for keyword in filing_keywords):
                filings.append(normalized)
            if any(keyword in lowered for keyword in control_keywords):
                controls.append(normalized)

        requirements: dict[str, Any] = {}
        if obligations:
            requirements["obligations"] = obligations[:8]
        if filings:
            requirements["filings"] = filings[:5]
        if controls:
            requirements["controls"] = controls[:5]
        if temporal_data.get("effective_date"):
            requirements["effective_date"] = temporal_data["effective_date"].isoformat()
        if temporal_data.get("deadline_date"):
            requirements["deadline_date"] = temporal_data["deadline_date"].isoformat()

        return requirements

    async def enrich_signal_with_regulatory_context(
        self,
        signal: Signal,
    ) -> dict[str, Any]:
        """Apply regulatory context to a signal for synthesis.

        This is what makes ChatGPT-level analysis look basic — we add
        deep regulatory context that generic AI doesn't have.

        Returns:
            Rich regulatory context dictionary
        """
        context = {
            "has_regulatory_implications": False,
            "regulatory_events": [],
            "applicable_rules": [],
            "predicted_impacts": [],
            "historical_precedents": [],
            "interpretation": None,
        }

        # Check if signal has regulatory content
        reg_event = await self.extract_regulatory_event_from_signal(
            signal, auto_create=False
        )

        if not reg_event or not reg_event.get("detected"):
            return context

        context["has_regulatory_implications"] = True
        context["issuing_body"] = reg_event.get("issuing_body")  # type: ignore
        context["event_type"] = reg_event.get("event_type")  # type: ignore
        context["severity_score"] = reg_event.get("severity_score")  # type: igbore

        # Find related regulatory events (semantic similarity)
        related_events = await self._find_related_regulatory_events(signal)
        context["regulatory_events"] = [
            {
                "id": str(e.id),
                "title": e.title,
                "event_type": e.event_type,
                "issuing_body": e.issuing_body,
                "announced_at": e.announced_at.isoformat(),
                "severity_score": e.severity_score,
                "similarity": similarity,
            }
            for e, similarity in related_events
        ]

        # Find applicable rules
        applicable_rules = await self._find_applicable_rules(signal)
        context["applicable_rules"] = [
            {
                "id": str(r.id),
                "rule_type": r.rule_type,
                "description": r.description,
                "effective_from": r.effective_from.isoformat(),
                "confidence": r.confidence_score,
            }
            for r in applicable_rules
        ]

        # Find historical precedents and impacts
        precedents = await self._find_historical_precedents(
            reg_event.get("issuing_body"), reg_event.get("event_type")
        )
        context["historical_precedents"] = precedents

        # Generate contextual interpretation
        context["interpretation"] = await self._generate_interpretation(
            signal, reg_event, related_events, applicable_rules, precedents
        )

        return context

    async def _find_related_regulatory_events(
        self,
        signal: Signal,
        top_k: int = 5,
    ) -> list[tuple[RegulatoryEvent, float]]:
        """Find semantically similar regulatory events using pgvector cosine similarity.

        Uses the ``content_embedding <=> query_embedding`` operator provided by
        pgvector to perform an exact nearest-neighbour search over the
        ``regulatory_events.content_embedding`` column.

        Falls back to fuzzy title matching when no embeddings are available.
        """
        # Generate embedding for the query signal
        query_text = f"{signal.title or ''} {self._get_signal_text(signal)[:300]}"
        query_embedding = await self.embedding_service.generate_query_embedding(
            query_text
        )

        # ── Primary path: pgvector cosine distance search ──────────────
        if query_embedding:
            embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

            pgvector_query = text(
                """
                SELECT
                    re.id,
                    re.content_embedding <=> :embedding AS distance
                FROM regulatory_events re
                WHERE re.content_embedding IS NOT NULL
                  AND re.verified_by_expert = true
                ORDER BY re.content_embedding <=> :embedding
                LIMIT :top_k
                """
            )

            result = await self.db.execute(
                pgvector_query,
                {"embedding": embedding_str, "top_k": top_k},
            )
            rows = result.fetchall()

            if rows:
                scored_events: list[tuple[RegulatoryEvent, float]] = []
                for row in rows:
                    event = await self.db.get(RegulatoryEvent, row.id)
                    if event:
                        similarity = 1.0 - float(
                            row.distance
                        )  # cosine distance → similarity
                        scored_events.append((event, round(similarity, 4)))

                logger.debug(
                    "pgvector search returned %d results (top similarity=%.3f)",
                    len(scored_events),
                    scored_events[0][1] if scored_events else 0,
                )
                return scored_events

        # ── Fallback: fuzzy title matching (no embeddings stored yet) ──
        logger.debug("Falling back to fuzzy title matching (no embeddings available)")

        query = (
            select(RegulatoryEvent)
            .where(RegulatoryEvent.verified_by_expert == True)
            .order_by(desc(RegulatoryEvent.announced_at))
            .limit(top_k * 3)  # over-fetch to compensate for weak ranking
        )

        result = await self.db.execute(query)
        events = result.scalars().all()

        scored_events = []
        for event in events:
            similarity = (
                fuzz.token_set_ratio((signal.title or "").lower(), event.title.lower())
                / 100.0
            )
            scored_events.append((event, similarity))

        scored_events.sort(key=lambda x: x[1], reverse=True)
        return scored_events[:top_k]

    async def _find_applicable_rules(
        self,
        signal: Signal,
        min_confidence: float = 0.6,
    ) -> list[RegulatoryRule]:
        """Find rules that might apply to entities mentioned in signal."""
        # Get current active rules
        query = (
            select(RegulatoryRule)
            .where(
                and_(
                    RegulatoryRule.is_active == True,
                    RegulatoryRule.confidence_score >= min_confidence,
                    RegulatoryRule.effective_from <= datetime.now(timezone.utc),
                    or_(
                        RegulatoryRule.effective_until.is_(None),
                        RegulatoryRule.effective_until >= datetime.now(timezone.utc),
                    ),
                )
            )
            .order_by(desc(RegulatoryRule.confidence_score))
            .limit(10)
        )

        result = await self.db.execute(query)
        return result.scalars().all()

    async def _find_historical_precedents(
        self,
        issuing_body: str,
        event_type: str,
        lookback_months: int = 24,
    ) -> list[dict[str, Any]]:
        """Find historical precedents for similar regulatory actions."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_months * 30)

        # Find past events from same regulator, same type
        query = (
            select(RegulatoryEvent, RegulatoryImpact)
            .outerjoin(
                RegulatoryImpact,
                RegulatoryImpact.regulatory_event_id == RegulatoryEvent.id,
            )
            .where(
                and_(
                    RegulatoryEvent.issuing_body == issuing_body,
                    RegulatoryEvent.event_type == event_type,
                    RegulatoryEvent.announced_at >= cutoff,
                    RegulatoryEvent.verified_by_expert == True,
                )
            )
            .order_by(desc(RegulatoryEvent.announced_at))
            .limit(5)
        )

        result = await self.db.execute(query)
        rows = result.all()

        precedents = []
        for event, impact in rows:
            precedent = {
                "event_id": str(event.id),
                "title": event.title,
                "announced_at": event.announced_at.isoformat(),
                "severity_score": event.severity_score,
            }

            if impact:
                precedent["observed_impact"] = {
                    "impact_type": impact.impact_type,
                    "metric": impact.metric_name,
                    "percentage_change": impact.percentage_change,
                    "lag_days": impact.lag_days,
                }

            precedents.append(precedent)

        return precedents

    async def _generate_interpretation(
        self,
        signal: Signal,
        reg_event: dict,
        related_events: list,
        applicable_rules: list,
        precedents: list,
    ) -> str:
        """Generate contextual interpretation (what ChatGPT can't do)."""
        interpretation_parts = []

        # Event classification
        interpretation_parts.append(
            f"**Regulatory Classification**: {reg_event['event_type'].replace('_', ' ').title()} "
            f"from {reg_event['issuing_body']}"
        )

        # Severity assessment
        severity = reg_event["severity_score"]
        if severity >= 0.8:
            severity_label = "HIGH IMPACT"
        elif severity >= 0.6:
            severity_label = "MODERATE IMPACT"
        else:
            severity_label = "LOW IMPACT"

        interpretation_parts.append(
            f"**Impact Severity**: {severity_label} (score: {severity:.2f})"
        )

        # Historical context
        if precedents:
            interpretation_parts.append(
                f"\n**Historical Context**: Based on {len(precedents)} similar actions "
                f"by {reg_event['issuing_body']} in the past 24 months:"
            )

            for i, prec in enumerate(precedents[:3], 1):
                if "observed_impact" in prec:
                    impact = prec["observed_impact"]
                    interpretation_parts.append(
                        f"  {i}. {prec['title'][:80]}... → "
                        f"{impact['impact_type']}: {impact['percentage_change']:.1f}% change "
                        f"in {impact['metric']} within {impact['lag_days']} days"
                    )

        # Applicable rules
        if applicable_rules:
            interpretation_parts.append(
                f"\n**Regulatory Framework**: {len(applicable_rules)} existing rules may apply"
            )

        return "\n".join(interpretation_parts)

    # ── Learning & Feedback ──────────────────────────────────────────

    async def record_regulatory_impact(
        self,
        regulatory_event_id: UUID,
        impact_type: str,
        metric_name: str,
        baseline_value: float,
        post_impact_value: float,
        *,
        affected_entity_id: UUID | None = None,
        affected_sector: str | None = None,
        supporting_signal_ids: list[UUID] | None = None,
        description: str | None = None,
        expert_verified: bool = False,
    ) -> RegulatoryImpact:
        """Record observed impact of a regulatory event (learning mechanism).

        This is how the system gets smarter over time — we track actual
        outcomes and use them to improve future predictions.
        """
        percentage_change = (
            (post_impact_value - baseline_value) / baseline_value * 100
            if baseline_value != 0
            else 0.0
        )

        # Calculate lag from regulatory event
        reg_event = await self.db.get(RegulatoryEvent, regulatory_event_id)
        if not reg_event:
            raise ValueError(f"Regulatory event {regulatory_event_id} not found")

        lag_days = (datetime.now(timezone.utc) - reg_event.announced_at).days

        impact = RegulatoryImpact(
            id=uuid4(),
            regulatory_event_id=regulatory_event_id,
            impact_type=impact_type,
            affected_entity_id=affected_entity_id,
            affected_sector=affected_sector,
            metric_name=metric_name,
            baseline_value=baseline_value,
            post_impact_value=post_impact_value,
            percentage_change=percentage_change,
            observation_date=datetime.now(timezone.utc),
            lag_days=lag_days,
            supporting_signal_ids=[str(sid) for sid in (supporting_signal_ids or [])],
            evidence_quality=0.8 if supporting_signal_ids else 0.5,
            description=description or f"Observed {impact_type} in {metric_name}",
            confidence_score=0.8 if expert_verified else 0.6,
            verified_by_expert=expert_verified,
        )

        self.db.add(impact)
        await self.db.flush()

        logger.info(
            f"Recorded regulatory impact: {impact_type} "
            f"({percentage_change:+.1f}% in {metric_name}) "
            f"{lag_days} days after event {regulatory_event_id}"
        )

        return impact

    async def update_rule_accuracy(
        self,
        rule_id: UUID,
        was_accurate: bool,
    ):
        """Update rule accuracy based on expert feedback (learning loop)."""
        rule = await self.db.get(RegulatoryRule, rule_id)
        if not rule:
            return

        # Incremental accuracy update (exponential moving average)
        alpha = 0.2  # Learning rate
        new_observation = 1.0 if was_accurate else 0.0
        rule.accuracy_score = (
            alpha * new_observation + (1 - alpha) * rule.accuracy_score
        )

        rule.application_count += 1
        rule.updated_at = datetime.now(timezone.utc)

        await self.db.flush()

    # ── ML-Based Pattern Learning ───────────────────────────────────

    async def learn_patterns_from_history(
        self,
        lookback_months: int = 36,
        min_occurrences: int = 3,
    ) -> list[RegulatoryPattern]:
        """Discover recurring regulatory sequences using ML pattern mining.

        Analyzes historical events to detect:
        - Event sequences (e.g., consultation → policy → enforcement)
        - Temporal patterns (e.g., rate adjustments every 6 weeks)
        - Cascading regulatory actions (one body triggers another)
        - Seasonal patterns (e.g., budget-related changes in Q1)
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_months * 30)

        # Get historical events grouped by regulator and type
        query = (
            select(RegulatoryEvent)
            .where(
                and_(
                    RegulatoryEvent.announced_at >= cutoff,
                    RegulatoryEvent.verified_by_expert == True,
                )
            )
            .order_by(RegulatoryEvent.announced_at)
        )

        result = await self.db.execute(query)
        events = result.scalars().all()

        if len(events) < min_occurrences:
            logger.info(f"Not enough events ({len(events)}) to learn patterns")
            return []

        discovered_patterns = []

        # Pattern 1: Sequential event chains
        # E.g., "consultation → draft policy → final policy"
        sequences = self._detect_event_sequences(events, min_occurrences)
        for seq in sequences:
            pattern = await self._create_or_update_pattern(
                pattern_type="event_sequence",
                pattern_signature=seq["signature"],
                description=seq["description"],
                confidence_score=seq["confidence"],
                metadata=seq["metadata"],
            )
            discovered_patterns.append(pattern)

        # Pattern 2: Temporal cycles
        # E.g., "MPR adjustment every 45-60 days"
        cycles = self._detect_temporal_cycles(events, min_occurrences)
        for cycle in cycles:
            pattern = await self._create_or_update_pattern(
                pattern_type="temporal_cycle",
                pattern_signature=cycle["signature"],
                description=cycle["description"],
                confidence_score=cycle["confidence"],
                metadata=cycle["metadata"],
            )
            discovered_patterns.append(pattern)

        # Pattern 3: Cross-regulator cascades
        # E.g., "CBN policy change → FIRS tax adjustment within 30 days"
        cascades = self._detect_regulatory_cascades(events, min_occurrences)
        for cascade in cascades:
            pattern = await self._create_or_update_pattern(
                pattern_type="regulatory_cascade",
                pattern_signature=cascade["signature"],
                description=cascade["description"],
                confidence_score=cascade["confidence"],
                metadata=cascade["metadata"],
            )
            discovered_patterns.append(pattern)

        await self.db.flush()

        logger.info(
            f"Learned {len(discovered_patterns)} patterns from {len(events)} events: "
            f"{len(sequences)} sequences, {len(cycles)} cycles, {len(cascades)} cascades"
        )

        return discovered_patterns

    def _detect_event_sequences(
        self,
        events: list[RegulatoryEvent],
        min_occurrences: int,
    ) -> list[dict]:
        """Detect recurring event type sequences using n-gram analysis."""
        # Build event sequence by regulator
        sequences_by_regulator = {}
        for event in events:
            key = event.issuing_body
            if key not in sequences_by_regulator:
                sequences_by_regulator[key] = []
            sequences_by_regulator[key].append(
                {
                    "type": event.event_type,
                    "date": event.announced_at,
                }
            )

        discovered = []

        # Look for 2-grams and 3-grams
        for regulator, event_list in sequences_by_regulator.items():
            if len(event_list) < 3:
                continue

            # Extract sequences with time windows (max 90 days between events)
            for window_size in [2, 3]:
                sequences = {}

                for i in range(len(event_list) - window_size + 1):
                    window = event_list[i : i + window_size]

                    # Check time gap
                    time_span = (window[-1]["date"] - window[0]["date"]).days
                    if time_span > 90:  # Max 90 days for sequence
                        continue

                    sig = " → ".join([e["type"] for e in window])
                    if sig not in sequences:
                        sequences[sig] = []
                    sequences[sig].append(time_span)

                # Find sequences that occur at least min_occurrences times
                for sig, time_spans in sequences.items():
                    if len(time_spans) >= min_occurrences:
                        avg_time_span = np.mean(time_spans)
                        std_time_span = np.std(time_spans)
                        confidence = min(0.95, len(time_spans) / (min_occurrences * 2))

                        discovered.append(
                            {
                                "signature": f"{regulator}:{sig}",
                                "description": (
                                    f"{regulator} typically follows '{sig}' pattern "
                                    f"(avg {avg_time_span:.0f} days, {len(time_spans)} occurrences)"
                                ),
                                "confidence": confidence,
                                "metadata": {
                                    "regulator": regulator,
                                    "sequence": sig,
                                    "avg_time_span_days": avg_time_span,
                                    "std_time_span_days": std_time_span,
                                    "occurrences": len(time_spans),
                                },
                            }
                        )

        return discovered

    def _detect_temporal_cycles(
        self,
        events: list[RegulatoryEvent],
        min_occurrences: int,
    ) -> list[dict]:
        """Detect recurring temporal patterns using time series analysis."""
        # Group events by (regulator, event_type)
        event_groups = {}
        for event in events:
            key = (event.issuing_body, event.event_type)
            if key not in event_groups:
                event_groups[key] = []
            event_groups[key].append(event.announced_at)

        discovered = []

        for (regulator, event_type), dates in event_groups.items():
            if len(dates) < min_occurrences:
                continue

            # Calculate inter-event intervals
            dates_sorted = sorted(dates)
            intervals = [
                (dates_sorted[i + 1] - dates_sorted[i]).days
                for i in range(len(dates_sorted) - 1)
            ]

            if not intervals:
                continue

            avg_interval = np.mean(intervals)
            std_interval = np.std(intervals)

            # Check if intervals are consistent (low variance = strong pattern)
            coefficient_of_variation = (
                std_interval / avg_interval if avg_interval > 0 else 1.0
            )

            if coefficient_of_variation < 0.3:  # Consistent pattern
                confidence = max(0.5, 1.0 - coefficient_of_variation)

                discovered.append(
                    {
                        "signature": f"{regulator}:{event_type}:cycle_{int(avg_interval)}d",
                        "description": (
                            f"{regulator} {event_type} occurs approximately every "
                            f"{avg_interval:.0f} days (±{std_interval:.0f} days, "
                            f"{len(dates)} occurrences)"
                        ),
                        "confidence": confidence,
                        "metadata": {
                            "regulator": regulator,
                            "event_type": event_type,
                            "avg_interval_days": avg_interval,
                            "std_interval_days": std_interval,
                            "coefficient_of_variation": coefficient_of_variation,
                            "occurrences": len(dates),
                        },
                    }
                )

        return discovered

    def _detect_regulatory_cascades(
        self,
        events: list[RegulatoryEvent],
        min_occurrences: int,
    ) -> list[dict]:
        """Detect cross-regulator cascades (one event triggers another)."""
        # For each event, look for other events within 30 days
        cascades = {}

        for i, trigger_event in enumerate(events):
            for response_event in events[i + 1 :]:
                # Check if response is within 30 days
                time_diff = (
                    response_event.announced_at - trigger_event.announced_at
                ).days
                if time_diff < 0 or time_diff > 30:
                    continue

                if trigger_event.issuing_body != response_event.issuing_body:
                    # Cross-regulator cascade
                    sig = (
                        f"{trigger_event.issuing_body}:{trigger_event.event_type} → "
                        f"{response_event.issuing_body}:{response_event.event_type}"
                    )

                    if sig not in cascades:
                        cascades[sig] = []
                    cascades[sig].append(time_diff)

        discovered = []

        for sig, time_diffs in cascades.items():
            if len(time_diffs) >= min_occurrences:
                avg_lag = np.mean(time_diffs)
                std_lag = np.std(time_diffs)
                confidence = min(0.9, len(time_diffs) / (min_occurrences * 2))

                discovered.append(
                    {
                        "signature": sig,
                        "description": (
                            f"Cascade pattern: {sig} "
                            f"(avg {avg_lag:.0f} day lag, {len(time_diffs)} occurrences)"
                        ),
                        "confidence": confidence,
                        "metadata": {
                            "cascade_signature": sig,
                            "avg_lag_days": avg_lag,
                            "std_lag_days": std_lag,
                            "occurrences": len(time_diffs),
                        },
                    }
                )

        return discovered

    async def _create_or_update_pattern(
        self,
        pattern_type: str,
        pattern_signature: str,
        description: str,
        confidence_score: float,
        metadata: dict,
    ) -> RegulatoryPattern:
        """Create new pattern or update existing one."""
        # Check if pattern already exists
        query = select(RegulatoryPattern).where(
            RegulatoryPattern.pattern_signature == pattern_signature
        )
        result = await self.db.execute(query)
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing pattern
            existing.occurrence_count = metadata.get(
                "occurrences", existing.occurrence_count
            )
            existing.confidence_score = confidence_score
            existing.last_observed_at = datetime.now(timezone.utc)
            existing.metadata_ = metadata
            existing.updated_at = datetime.now(timezone.utc)
            return existing
        else:
            # Create new pattern
            pattern = RegulatoryPattern(
                id=uuid4(),
                pattern_type=pattern_type,
                pattern_signature=pattern_signature,
                description=description,
                occurrence_count=metadata.get("occurrences", 1),
                confidence_score=confidence_score,
                first_observed_at=datetime.now(timezone.utc),
                last_observed_at=datetime.now(timezone.utc),
                metadata_=metadata,
            )
            self.db.add(pattern)
            return pattern

    async def detect_pattern_in_signal(
        self,
        signal: Signal,
        event: RegulatoryEvent | None = None,
    ) -> list[tuple[RegulatoryPattern, float]]:
        """Check if signal matches any learned patterns.

        Returns list of (pattern, match_score) tuples.
        """
        if not event:
            # Try to extract event from signal first
            event_dict = await self.extract_regulatory_event_from_signal(
                signal, auto_create=False
            )
            if not event_dict:
                return []
            issuing_body = event_dict.get("issuing_body")
            event_type = event_dict.get("event_type")
        else:
            issuing_body = event.issuing_body
            event_type = event.event_type

        if not issuing_body or not event_type:
            return []

        # Get all active patterns
        query = select(RegulatoryPattern).where(
            RegulatoryPattern.confidence_score >= 0.5
        )
        result = await self.db.execute(query)
        patterns = result.scalars().all()

        matched_patterns = []

        for pattern in patterns:
            match_score = 0.0

            if pattern.pattern_type == "event_sequence":
                # Check if this event type appears in the sequence
                if event_type in pattern.pattern_signature:
                    match_score = 0.7

                    # Bonus if regulator matches
                    if issuing_body in pattern.pattern_signature:
                        match_score = 0.9

            elif pattern.pattern_type == "temporal_cycle":
                # Check if regulator and event type match
                if (
                    issuing_body in pattern.pattern_signature
                    and event_type in pattern.pattern_signature
                ):
                    match_score = 0.8

            elif pattern.pattern_type == "regulatory_cascade":
                # Check if this could be a trigger or response event
                if issuing_body in pattern.pattern_signature:
                    match_score = 0.6

            if match_score > 0:
                matched_patterns.append((pattern, match_score))

        # Sort by match score
        matched_patterns.sort(key=lambda x: x[1], reverse=True)

        return matched_patterns

    async def predict_next_regulatory_action(
        self,
        recent_event: RegulatoryEvent,
    ) -> list[dict[str, Any]]:
        """Use learned patterns to predict what regulatory actions might follow.

        This is the "intelligence moat" — predicting what comes next based on
        learned patterns that competitors don't have.
        """
        predictions = []

        # Find patterns that include this event
        matched_patterns = await self.detect_pattern_in_signal(
            signal=None,  # We'll check using event directly
            event=recent_event,
        )

        for pattern, match_score in matched_patterns:
            if pattern.pattern_type == "event_sequence":
                # Parse sequence to find what comes next
                sequence_parts = pattern.pattern_signature.split(" → ")
                event_type_target = recent_event.event_type

                for i, part in enumerate(sequence_parts):
                    if event_type_target in part and i < len(sequence_parts) - 1:
                        next_event_type = sequence_parts[i + 1].split(":")[-1]

                        predictions.append(
                            {
                                "prediction_type": "sequence_continuation",
                                "predicted_event_type": next_event_type,
                                "predicted_regulator": recent_event.issuing_body,
                                "confidence": pattern.confidence_score * match_score,
                                "expected_timeframe_days": pattern.metadata_.get(
                                    "avg_time_span_days", 30
                                ),
                                "pattern_id": str(pattern.id),
                                "rationale": f"Based on {pattern.occurrence_count} historical occurrences of this sequence",
                            }
                        )

            elif pattern.pattern_type == "temporal_cycle":
                # Predict next occurrence based on cycle
                avg_interval = pattern.metadata_.get("avg_interval_days", 60)
                expected_date = recent_event.announced_at + timedelta(days=avg_interval)
                days_until = (expected_date - datetime.now(timezone.utc)).days

                if days_until > 0:  # Only predict future events
                    predictions.append(
                        {
                            "prediction_type": "temporal_cycle",
                            "predicted_event_type": recent_event.event_type,
                            "predicted_regulator": recent_event.issuing_body,
                            "confidence": pattern.confidence_score * 0.8,
                            "expected_date": expected_date.isoformat(),
                            "days_until_expected": days_until,
                            "pattern_id": str(pattern.id),
                            "rationale": f"Based on {pattern.occurrence_count} cycle occurrences (avg {avg_interval:.0f} days)",
                        }
                    )

            elif pattern.pattern_type == "regulatory_cascade":
                # Predict cascade response
                cascade_parts = pattern.pattern_signature.split(" → ")
                if len(cascade_parts) == 2:
                    trigger_part, response_part = cascade_parts
                    trigger_body = trigger_part.split(":")[0]

                    if trigger_body == recent_event.issuing_body:
                        # This could trigger a cascade
                        response_body = response_part.split(":")[0]
                        response_type = response_part.split(":")[-1]
                        avg_lag = pattern.metadata_.get("avg_lag_days", 15)
                        expected_date = recent_event.announced_at + timedelta(
                            days=avg_lag
                        )
                        days_until = (expected_date - datetime.now(timezone.utc)).days

                        if days_until > 0:
                            predictions.append(
                                {
                                    "prediction_type": "regulatory_cascade",
                                    "predicted_event_type": response_type,
                                    "predicted_regulator": response_body,
                                    "confidence": pattern.confidence_score
                                    * match_score
                                    * 0.7,
                                    "expected_date": expected_date.isoformat(),
                                    "days_until_expected": days_until,
                                    "pattern_id": str(pattern.id),
                                    "rationale": f"Based on {pattern.occurrence_count} historical cascades (avg {avg_lag:.0f} day lag)",
                                }
                            )

        # Sort by confidence
        predictions.sort(key=lambda x: x["confidence"], reverse=True)

        return predictions[:5]  # Top 5 predictions
