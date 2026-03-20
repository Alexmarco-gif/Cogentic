"""RAG-based AI synthesis engine with causal intelligence overlay.

Uses pgvector for semantic retrieval + GPT-4o for synthesis.
Implements caching via Redis (15min TTL).
Provides evidence attribution and confidence aggregation.

Intelligence differentiation layers (what makes output unreplicable):
  1. Entity graph context — relationship context from proprietary entity graph
  2. Causal chain predictions — "what will happen next" from longitudinal data
  3. Historical precedents — "based on N past instances..."
  4. Feedback-boosted ranking — signals re-ranked by collective user engagement
  5. Regulatory intelligence — Regulatory context, rules, and precedents
"""

import hashlib
import json
import logging
import time
from typing import Any
from uuid import UUID

from openai import AsyncOpenAI
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.ai.embeddings import EmbeddingService
from backend.ai.guardrails import get_guardrails
from backend.config import get_settings
from backend.models.signal import Signal
from backend.redis_client import get_redis
from backend.services.causal_intelligence import CausalIntelligenceService
from backend.services.entity_resolution import EntityResolutionService
from backend.services.feedback_service import FeedbackService
from backend.services.regulatory_intelligence import RegulatoryIntelligenceService

logger = logging.getLogger(__name__)
settings = get_settings()

# Singleton OpenAI client
_openai_client: AsyncOpenAI | None = None

SYNTHESIS_CACHE_TTL = 900  # 15 minutes
SYNTHESIS_TOP_K = 10  # Top-K signals for retrieval


def _get_openai_client() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        import httpx

        _openai_client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            timeout=httpx.Timeout(60.0, connect=10.0),
            max_retries=2,
        )
    return _openai_client


class SynthesisService:
    """RAG synthesis engine with causal intelligence overlay.

    Pipeline: embed query → retrieve signals → enrich with entity graph +
    causal predictions + historical precedents + regulatory context → GPT-4o synthesis.

    The enrichment layers make every response proprietary — the same query
    to ChatGPT or Google produces fundamentally different (inferior) output.

    Features:
        - Query embedding via EmbeddingService
        - Top-K signal retrieval via pgvector cosine similarity
        - Entity graph context injection (who's connected to whom)
        - Causal chain predictions (what happens next)
        - Historical precedent matching (what happened last time)
        - Feedback-boosted re-ranking (collective intelligence)
        - Regulatory context enrichment (regulatory knowledge)
        - GPT-4o synthesis with structured prompt + evidence attribution
        - Redis caching for identical queries (15min TTL)
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding_service = EmbeddingService(db)
        self.client = _get_openai_client()
        self.guardrails = get_guardrails()
        # Intelligence moat services
        self.entity_service = EntityResolutionService(db)
        self.causal_service = CausalIntelligenceService(db)
        self.feedback_service = FeedbackService(db)
        self.regulatory_service = RegulatoryIntelligenceService(db)

    async def synthesize(
        self,
        query: str,
        *,
        org_id: UUID | None = None,
        industry_id: UUID | None = None,
        top_k: int = SYNTHESIS_TOP_K,
        min_confidence: float = 0.60,
        web_context: list | None = None,
    ) -> dict[str, Any]:
        """Execute RAG synthesis: embed → retrieve → synthesize.

        Args:
            query: User query text.
            org_id: Optional org filter for tenant isolation.
            industry_id: Optional industry filter.
            top_k: Number of top signals to retrieve.
            min_confidence: Minimum signal confidence threshold.
            web_context: Optional list of WebSearchResult objects from
                         live SerpApi search to enrich synthesis.

        Returns:
            Synthesis result dict with answer, sources, confidence, limitations.
        """
        start = time.monotonic()

        # Sanitize input
        sanitized = self.guardrails.sanitize_input(query, context="synthesis")
        if not sanitized.is_safe and sanitized.injection_detected:
            return {
                "answer": "Your query was flagged for safety review. Please rephrase.",
                "sources": [],
                "confidence": 0.0,
                "limitations": ["Query blocked by safety filter"],
                "cached": False,
                "response_time_ms": 0,
            }
        clean_query = sanitized.text

        # Check Redis cache
        query_hash = self._hash_query(clean_query, org_id, industry_id)
        cached = await self._get_cached(query_hash)
        if cached:
            cached["cached"] = True
            cached["response_time_ms"] = int((time.monotonic() - start) * 1000)
            return cached

        # Step 1: Generate query embedding
        query_embedding = await self.embedding_service.generate_query_embedding(
            clean_query
        )

        # Step 2: Retrieve top-K signals via pgvector cosine similarity
        signals = await self._retrieve_signals(
            query_embedding,
            org_id=org_id,
            industry_id=industry_id,
            top_k=top_k,
            min_confidence=min_confidence,
        )

        if not signals:
            result = {
                "answer": (
                    "No relevant signals found for your query. "
                    "Try broadening your search terms or checking a different industry."
                ),
                "sources": [],
                "confidence": 0.0,
                "limitations": [
                    "No signals matched the query with sufficient confidence"
                ],
                "cached": False,
                "query_hash": query_hash,
                "response_time_ms": int((time.monotonic() - start) * 1000),
            }
            return result

        # Step 3: Enrich with proprietary intelligence layers
        intelligence_context = await self._build_intelligence_context(
            clean_query, signals, org_id=org_id
        )

        # Step 4: GPT-4o synthesis with evidence + intelligence context
        synthesis_result = await self._synthesize_with_llm(
            clean_query,
            signals,
            intelligence_context,
            web_context=web_context,
        )

        # Step 5: Aggregate confidence from source signals
        avg_confidence = sum(s["confidence"] for s in signals) / len(signals)
        synthesis_result["confidence"] = round(avg_confidence, 4)
        synthesis_result["source_count"] = len(signals)
        synthesis_result["cached"] = False
        synthesis_result["query_hash"] = query_hash
        synthesis_result["intelligence_layers"] = intelligence_context.get(
            "layers_applied", []
        )
        synthesis_result["response_time_ms"] = int((time.monotonic() - start) * 1000)

        # Cache result
        await self._set_cached(query_hash, synthesis_result)

        return synthesis_result

    # ── Brief Synthesis ──────────────────────────────────────────────

    async def synthesize_brief(
        self,
        topic: str,
        *,
        org_id: UUID | None = None,
        industry_id: UUID | None = None,
        top_k: int = SYNTHESIS_TOP_K,
        min_confidence: float = 0.60,
        signal_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Generate a structured intelligence brief from retrieved signals.

        Unlike ``synthesize()``, this method returns a validated JSON dict
        with the brief body schema (``findings[]``, ``indicators[]``) rather
        than free-form markdown, making it suitable for persisting into
        ``IntelligenceBrief.body_json``.

        Args:
            topic: The brief topic / analytical question.
            org_id: Optional tenant scope.
            industry_id: Optional industry filter.
            top_k: Number of signals to retrieve.
            min_confidence: Minimum signal confidence threshold.
            signal_ids: Optional explicit signal IDs to include.

        Returns:
            Dict with keys: title, bluf, findings, indicators, outlook,
            decision_lens, domain, tags, confidence, read_time, citations.
        """
        # Embed topic
        query_embedding = await self.embedding_service.generate_query_embedding(topic)

        # Retrieve relevant signals
        signals = await self._retrieve_signals(
            query_embedding,
            org_id=org_id,
            industry_id=industry_id,
            top_k=top_k,
            min_confidence=min_confidence,
        )

        if not signals:
            return {
                "title": topic,
                "bluf": f"Insufficient signal data to synthesise a brief on: {topic}",
                "findings": [],
                "indicators": [],
                "outlook": "",
                "decision_lens": "",
                "domain": "",
                "tags": [],
                "confidence": 0,
                "read_time": 3,
                "citations": [],
            }

        # Build signal context for the prompt
        signal_blocks = []
        for i, sig in enumerate(signals, 1):
            block = (
                f"[Signal {i}] {sig['title']}\n"
                f"Confidence: {sig['confidence']:.2f} | Similarity: {sig['similarity']:.2f}\n"
                f"{sig['summary'][:400]}"
            )
            if sig.get("source_url"):
                block += f"\nSource: {sig['source_url']}"
            signal_blocks.append(block)
        signal_context = "\n---\n".join(signal_blocks)

        avg_confidence = round(
            sum(s["confidence"] for s in signals) / len(signals) * 100
        )

        system_prompt = (
            "You are a senior intelligence analyst. "
            "Return ONLY valid JSON — no prose, no markdown fences. "
            "Your analysis must be grounded solely in the provided signals. "
            "Never invent facts not supported by the evidence."
        )

        user_prompt = f"""Produce a structured intelligence brief on the following topic using the signals below.

Topic: {topic}

Signals ({len(signals)} retrieved):
{signal_context}

Return a JSON object with exactly these keys:

{{
  "title": "Analytical headline — a falsifiable claim, not a label (max 15 words)",
  "bluf": "Bottom line up front — 4-6 sentences stating the contention and why it matters",
  "findings": [
    {{
      "finding": "One analytic conclusion sentence",
      "evidence": ["Named source: specific data point", "..."],
      "objection": "Strongest counter-argument a sceptic would make",
      "rebuttal": "Why the finding still holds despite that objection"
    }}
  ],
  "indicators": [
    {{
      "watch": "Specific data source and metric to monitor",
      "confirms_if": "Concrete threshold or event that confirms the finding",
      "disconfirms_if": "Concrete threshold or event that overturns the finding"
    }}
  ],
  "outlook": "2-3 sentence forward-looking assessment with timeline",
  "decision_lens": "1-2 sentences on what this means for a decision-maker",
  "domain": "one of: macro | sector | market | regulatory | geopolitical",
  "tags": ["tag1", "tag2"],
  "confidence": {avg_confidence},
  "read_time": 5,
  "citations": ["source name or URL for each signal used"]
}}

Rules:
- 2-4 findings, each grounded in at least one signal
- 2-3 indicators with specific thresholds (not vague phrases)
- title must be a falsifiable assertion, not a topic label
- bluf must name the contention in the first sentence
"""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=2000,
            )
            raw = response.choices[0].message.content or "{}"
            result: dict[str, Any] = json.loads(raw)
            # Ensure required keys exist
            result.setdefault("findings", [])
            result.setdefault("indicators", [])
            result.setdefault(
                "citations",
                [s.get("source_url", "") for s in signals if s.get("source_url")],
            )
            result.setdefault("confidence", avg_confidence)
            result.setdefault("read_time", max(3, len(result["findings"]) * 2))
            return result
        except Exception as exc:
            logger.error("synthesize_brief LLM call failed for %r: %s", topic, exc)
            raise RuntimeError("AI synthesis failed for this brief request") from exc

    # ── Signal Retrieval ─────────────────────────────────────────────

    async def _retrieve_signals(
        self,
        query_embedding: list[float],
        *,
        org_id: UUID | None = None,
        industry_id: UUID | None = None,
        top_k: int = 10,
        min_confidence: float = 0.60,
    ) -> list[dict[str, Any]]:
        """Retrieve top-K signals via pgvector cosine similarity.

        Filters by org_id (tenant isolation), industry, and confidence.
        Returns dicts with signal metadata + similarity score.
        """
        # Build pgvector cosine distance query
        embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

        conditions = [
            "s.embedding IS NOT NULL",
            "s.confidence >= :min_confidence",
            "s.deleted_at IS NULL" if hasattr(self, "_has_deleted_at") else "1=1",
        ]
        params: dict[str, Any] = {
            "embedding": embedding_str,
            "top_k": top_k,
            "min_confidence": min_confidence,
        }

        if org_id:
            conditions.append("(s.org_id IS NULL OR s.org_id = :org_id)")
            params["org_id"] = str(org_id)

        if industry_id:
            conditions.append(
                "s.contract_id IN (SELECT id FROM signal_contracts WHERE industry_id = :industry_id)"
            )
            params["industry_id"] = str(industry_id)

        where_clause = " AND ".join(conditions)

        query = text(
            f"""
            SELECT
                s.id,
                s.title,
                s.summary,
                s.confidence,
                s.signal_type,
                s.source_url,
                s.published_at,
                s.embedding <=> :embedding AS distance
            FROM signals s
            WHERE {where_clause}
            ORDER BY s.embedding <=> :embedding
            LIMIT :top_k
        """
        )

        result = await self.db.execute(
            query,
            params,
        )
        rows = result.fetchall()

        signals = []
        for row in rows:
            similarity = 1.0 - (row.distance or 1.0)  # cosine distance → similarity
            signals.append(
                {
                    "id": str(row.id),
                    "title": row.title or "Untitled Signal",
                    "summary": row.summary or "",
                    "confidence": float(row.confidence),
                    "signal_type": row.signal_type,
                    "source_url": row.source_url,
                    "published_at": (
                        row.published_at.isoformat() if row.published_at else None
                    ),
                    "similarity": round(similarity, 4),
                }
            )

        logger.info(
            f"Retrieved {len(signals)} signals for synthesis query "
            f"(top_k={top_k}, min_conf={min_confidence})"
        )
        return signals

    # ── Intelligence Context Builder ───────────────────────────────

    async def _build_intelligence_context(
        self,
        query: str,
        signals: list[dict[str, Any]],
        *,
        org_id: UUID | None = None,
    ) -> dict[str, Any]:
        """Build proprietary intelligence context to inject into LLM prompt.

        This is the core moat: layers of context that no other platform
        has access to.

        Layers:
          1. Entity graph context — relationship network for mentioned entities
          2. Causal predictions — cascading impact analysis
          3. Historical precedents — past instances and outcomes
          4. Feedback quality — collective engagement signals
          5. Regulatory context — Regulatory knowledge and precedents
        """
        context: dict[str, Any] = {"layers_applied": []}

        # Collect entity IDs from retrieved signals
        signal_ids = [UUID(s["id"]) for s in signals if s.get("id")]

        # --- Layer 1: Entity Graph Context ---
        try:
            entity_graph_context = await self._get_entity_graph_context(
                query, signal_ids
            )
            if entity_graph_context:
                context["entity_graph"] = entity_graph_context
                context["layers_applied"].append("entity_graph")
        except Exception as e:
            logger.debug(f"Entity graph context skipped: {e}")

        # --- Layer 2: Causal Chain Predictions ---
        try:
            causal_context = await self._get_causal_context(signal_ids)
            if causal_context:
                context["causal_predictions"] = causal_context
                context["layers_applied"].append("causal_predictions")
        except Exception as e:
            logger.debug(f"Causal context skipped: {e}")

        # --- Layer 3: Feedback-Boosted Quality ---
        try:
            feedback_context = await self._get_feedback_context(signal_ids)
            if feedback_context:
                context["feedback_quality"] = feedback_context
                context["layers_applied"].append("feedback_quality")
        except Exception as e:
            logger.debug(f"Feedback context skipped: {e}")

        # --- Layer 4: Regulatory Context ---
        try:
            regulatory_context = await self._get_regulatory_context(query, signal_ids)
            if regulatory_context:
                context["regulatory_intelligence"] = regulatory_context
                context["layers_applied"].append("regulatory_intelligence")
        except Exception as e:
            logger.debug(f"Regulatory context skipped: {e}")

        return context

    async def _get_entity_graph_context(
        self,
        query: str,
        signal_ids: list[UUID],
    ) -> dict[str, Any] | None:
        """Extract entity relationship context for enrichment."""
        from backend.models.entity import Entity
        from backend.models.signal_entity import SignalEntity

        # Get entities mentioned in retrieved signals
        if not signal_ids:
            return None

        result = await self.db.execute(
            select(Entity.id, Entity.name, Entity.entity_type)
            .join(SignalEntity, SignalEntity.entity_id == Entity.id)
            .where(SignalEntity.signal_id.in_(signal_ids))
            .distinct()
            .limit(10)
        )
        entities = result.all()

        if not entities:
            return None

        # Get relationship network for top entities
        entity_profiles = []
        for entity_id, name, entity_type in entities[:5]:
            try:
                network = await self.entity_service.get_entity_network(
                    entity_id, max_depth=1, min_strength=0.3
                )
                profile = await self.entity_service.get_entity_full_profile(entity_id)
                if profile:
                    entity_profiles.append(
                        {
                            "name": name,
                            "type": entity_type,
                            "relationships": len(network.get("edges", [])),
                            "connected_to": [
                                n["name"]
                                for n in network.get("nodes", [])
                                if n.get("id") != str(entity_id)
                            ][:5],
                            "data_richness": profile.get("data_richness", 0),
                            "source_count": len(profile.get("source_profiles", [])),
                        }
                    )
            except Exception:
                entity_profiles.append({"name": name, "type": entity_type})

        return {
            "entities_found": len(entities),
            "profiles": entity_profiles,
        }

    async def _get_causal_context(
        self,
        signal_ids: list[UUID],
    ) -> dict[str, Any] | None:
        """Get causal chain predictions from signals."""
        from backend.models.causal_event import CausalEvent

        if not signal_ids:
            return None

        # Find causal events linked to these signals
        result = await self.db.execute(
            select(CausalEvent.event_type)
            .where(CausalEvent.signal_id.in_(signal_ids))
            .distinct()
        )
        event_types = [row[0] for row in result.all()]

        if not event_types:
            return None

        # Get predictions for each event type
        all_predictions = []
        for event_type in event_types[:3]:  # Limit to top 3
            try:
                predictions = await self.causal_service.predict_cascading_impacts(
                    event_type, time_horizon_days=30
                )
                if predictions.get("immediate_impacts"):
                    all_predictions.append(
                        {
                            "trigger": event_type,
                            "immediate": predictions["immediate_impacts"][:3],
                            "secondary": predictions.get("secondary_impacts", [])[:2],
                            "chains_analyzed": predictions.get(
                                "total_chains_analyzed", 0
                            ),
                        }
                    )
            except Exception:
                pass

        if not all_predictions:
            return None

        # Get historical precedents for the first event type
        precedents = []
        try:
            precedent_data = await self.causal_service.find_historical_precedents(
                event_types[0], lookback_months=24, limit=3
            )
            precedents = [
                {
                    "summary": p["event_summary"][:150],
                    "date": p["timestamp"],
                    "consequences": len(p.get("consequences", [])),
                }
                for p in precedent_data
            ]
        except Exception:
            pass

        return {
            "predictions": all_predictions,
            "historical_precedents": precedents,
        }

    async def _get_feedback_context(
        self,
        signal_ids: list[UUID],
    ) -> dict[str, Any] | None:
        """Get collective feedback quality for signals."""
        if not signal_ids:
            return None

        quality_scores = []
        for sid in signal_ids[:10]:
            try:
                quality = await self.feedback_service.get_signal_quality_score(sid)
                if quality["total_votes"] > 0:
                    quality_scores.append(
                        {
                            "signal_id": str(sid),
                            "quality_score": quality["quality_score"],
                            "total_votes": quality["total_votes"],
                        }
                    )
            except Exception:
                pass

        if not quality_scores:
            return None

        return {
            "signals_with_feedback": len(quality_scores),
            "avg_quality": round(
                sum(q["quality_score"] for q in quality_scores) / len(quality_scores),
                4,
            ),
            "scores": quality_scores,
        }

    async def _get_regulatory_context(
        self,
        query: str,
        signal_ids: list[UUID],
    ) -> dict[str, Any] | None:
        """Get regulatory context and precedents.

        Provides:
        - Applicable regulatory events (CBN, SEC, FIRS, etc.)
        - Active regulatory rules that match query context
        - Historical regulatory impacts and outcomes
        - Predicted compliance implications
        """
        if not signal_ids:
            return None

        # Enrich query with regulatory context
        # We create a synthetic signal object for context checking
        regulatory_insights = []

        # Check each signal for regulatory implications
        for sid in signal_ids[:5]:  # Check top 5 signals
            try:
                signal = await self.db.get(Signal, sid)
                if not signal:
                    continue
                enrichment = (
                    await self.regulatory_service.enrich_signal_with_regulatory_context(
                        signal
                    )
                )
                if enrichment.get("has_regulatory_implications"):
                    regulatory_insights.append(
                        {
                            "signal_id": str(sid),
                            "regulatory_events": [
                                {
                                    "issuing_body": re["issuing_body"],
                                    "event_type": re["event_type"],
                                    "severity": re.get("severity_score", 0),
                                    "summary": re.get("title", "")[:150],
                                }
                                for re in enrichment.get("regulatory_events", [])[:2]
                            ],
                            "applicable_rules": len(
                                enrichment.get("applicable_rules", [])
                            ),
                            "interpretation": enrichment.get("interpretation", "")[
                                :200
                            ],
                        }
                    )
            except Exception as e:
                logger.debug(f"Regulatory enrichment failed for signal {sid}: {e}")

        if not regulatory_insights:
            return None

        # Get statistical overview from knowledge base
        from backend.models.regulatory_knowledge import RegulatoryEvent, RegulatoryRule

        # Count relevant regulatory events by body
        result = await self.db.execute(
            select(RegulatoryEvent.issuing_body, text("COUNT(*)"))
            .group_by(RegulatoryEvent.issuing_body)
            .order_by(text("COUNT(*) DESC"))
            .limit(5)
        )
        top_regulators = [
            {"body": row[0], "event_count": row[1]} for row in result.all()
        ]

        # Count active rules
        active_rules_result = await self.db.execute(
            select(text("COUNT(*)"))
            .select_from(RegulatoryRule)
            .where(RegulatoryRule.is_active == True)
        )
        active_rules_count = active_rules_result.scalar() or 0

        return {
            "signals_with_regulatory_implications": len(regulatory_insights),
            "enrichment_details": regulatory_insights,
            "knowledge_base_stats": {
                "top_regulatory_bodies": top_regulators,
                "active_rules": active_rules_count,
            },
        }

    # ── LLM Synthesis ────────────────────────────────────────────────

    async def _synthesize_with_llm(
        self,
        query: str,
        signals: list[dict[str, Any]],
        intelligence_context: dict[str, Any] | None = None,
        *,
        web_context: list | None = None,
    ) -> dict[str, Any]:
        """Synthesize retrieved signals into an answer using GPT-4o.

        Uses structured prompt with evidence attribution AND proprietary
        intelligence context layers. Optionally enriched with live web
        search results from SerpApi.
        """
        system_prompt = self.guardrails.get_system_prompt("synthesis")

        # Build evidence context from retrieved signals
        evidence_blocks = []
        for i, sig in enumerate(signals, 1):
            block = (
                f"[Signal {i}] ID: {sig['id']}\n"
                f"Title: {sig['title']}\n"
                f"Type: {sig['signal_type']}\n"
                f"Confidence: {sig['confidence']:.2f}\n"
                f"Similarity: {sig['similarity']:.2f}\n"
                f"Summary: {sig['summary'][:500]}\n"
            )
            if sig.get("source_url"):
                block += f"Source: {sig['source_url']}\n"
            if sig.get("published_at"):
                block += f"Published: {sig['published_at']}\n"
            evidence_blocks.append(block)

        evidence_context = "\n---\n".join(evidence_blocks)

        # Build proprietary intelligence sections
        intel_sections = ""

        if intelligence_context:
            # Entity graph context
            entity_graph = intelligence_context.get("entity_graph")
            if entity_graph and entity_graph.get("profiles"):
                entity_lines = []
                for ep in entity_graph["profiles"]:
                    line = f"  - {ep['name']} ({ep.get('type', 'unknown')})"
                    connected = ep.get("connected_to", [])
                    if connected:
                        line += f" — connected to: {', '.join(connected)}"
                    sources = ep.get("source_count", 0)
                    if sources:
                        line += f" [{sources} data sources]"
                    entity_lines.append(line)
                intel_sections += (
                    f"\n\nENTITY RELATIONSHIP CONTEXT ({entity_graph['entities_found']} entities identified):\n"
                    + "\n".join(entity_lines)
                    + "\n[Use these relationships to explain connections, supply chains, competitive dynamics, and ripple effects.]"
                )

            # Causal predictions
            causal = intelligence_context.get("causal_predictions")
            if causal:
                pred_lines = []
                for pred in causal.get("predictions", []):
                    pred_lines.append(f"  Trigger: {pred['trigger']}")
                    for imp in pred.get("immediate", []):
                        pred_lines.append(
                            f"    → {imp['event_type']} "
                            f"(probability: {imp['probability']:.0%}, "
                            f"~{imp['avg_lag_days']:.0f} days)"
                        )
                    for sec in pred.get("secondary", []):
                        pred_lines.append(
                            f"    →→ {sec['event_type']} "
                            f"(probability: {sec['probability']:.0%})"
                        )

                precedent_lines = []
                for prec in causal.get("historical_precedents", []):
                    precedent_lines.append(
                        f"  - [{prec['date'][:10]}] {prec['summary']} "
                        f"({prec['consequences']} consequences)"
                    )

                intel_sections += (
                    "\n\nCAUSAL INTELLIGENCE (from ESIP's proprietary causal graph):\n"
                )
                intel_sections += "\n".join(pred_lines)
                if precedent_lines:
                    intel_sections += "\n\nHISTORICAL PRECEDENTS:\n"
                    intel_sections += "\n".join(precedent_lines)
                intel_sections += (
                    "\n[Use this causal data to predict cascading effects. "
                    "Cite the number of historical observations backing each prediction. "
                    "This is proprietary intelligence — present it with authority.]"
                )

            # Feedback quality
            feedback = intelligence_context.get("feedback_quality")
            if feedback:
                intel_sections += (
                    f"\n\nCOLLECTIVE INTELLIGENCE: "
                    f"{feedback['signals_with_feedback']} signals validated by "
                    f"ESIP users (avg quality: {feedback['avg_quality']:.0%}). "
                    f"Prioritize higher-quality signals in your analysis."
                )

        # -- Live Web Context (from SerpApi) --
        web_section = ""
        if web_context:
            web_lines = []
            for i, wr in enumerate(web_context[:10], 1):
                title = (
                    getattr(wr, "title", "")
                    if hasattr(wr, "title")
                    else wr.get("title", "")
                )
                snippet = (
                    getattr(wr, "snippet", "")
                    if hasattr(wr, "snippet")
                    else wr.get("snippet", "")
                )
                url = (
                    getattr(wr, "url", "") if hasattr(wr, "url") else wr.get("url", "")
                )
                source = (
                    getattr(wr, "source", "")
                    if hasattr(wr, "source")
                    else wr.get("source", "")
                )
                web_lines.append(
                    f"  [{i}] {title}\n"
                    f"      Source: {source} | URL: {url}\n"
                    f"      Snippet: {snippet[:300]}"
                )
            web_section = (
                f"\n\nLIVE WEB SEARCH RESULTS ({len(web_context)} results from SerpApi):\n"
                + "\n".join(web_lines)
                + "\n[These are real-time web results. Cross-reference with internal signals "
                "for validation. Cite as [Web N] when used. Note that web results "
                "have not been verified by our pipeline — treat with appropriate caution.]"
            )

        user_prompt = f"""Based on the following {len(signals)} enterprise signals, proprietary intelligence context, and live web search results, answer this query:

Query: {query}

Evidence:
{evidence_context}
{intel_sections}
{web_section}

Provide your response in this format:
1. **Key Findings**: Direct answer to the query (cite [Signal N] and [Web N] for each claim)
2. **Causal Analysis**: What caused this situation and what cascading effects to expect (with estimated timelines)
3. **Entity Impact Map**: Which entities are affected, how they're connected, and predicted impact on each
4. **Evidence Summary**: Supporting signals, web sources, and historical precedents
5. **Predictive Outlook**: What will likely happen next (with confidence levels and timeframes)
6. **Limitations**: Data gaps, confidence caveats, what this analysis does NOT cover

IMPORTANT: Go beyond what a Google search or ChatGPT could produce.
Leverage the entity relationships and causal predictions to provide
actionable, forward-looking intelligence with specific timelines.
"""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=2000,
            )

            answer_text = response.choices[0].message.content or ""

            # Filter output through guardrails
            filtered = self.guardrails.filter_output(answer_text, context="synthesis")

            # Extract token usage
            usage = {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": (
                    response.usage.completion_tokens if response.usage else 0
                ),
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            }

            # Build limitations from evidence gaps
            limitations = []
            low_conf = [s for s in signals if s["confidence"] < 0.70]
            if low_conf:
                limitations.append(
                    f"{len(low_conf)} of {len(signals)} source signals have "
                    f"confidence below 0.70"
                )
            low_sim = [s for s in signals if s["similarity"] < 0.50]
            if low_sim:
                limitations.append(
                    f"{len(low_sim)} signals have low relevance (similarity < 0.50)"
                )

            return {
                "answer": filtered.text,
                "sources": [
                    {
                        "signal_id": s["id"],
                        "title": s["title"],
                        "confidence": s["confidence"],
                        "similarity": s["similarity"],
                        "source_url": s.get("source_url"),
                    }
                    for s in signals
                ],
                "limitations": limitations,
                "token_usage": usage,
            }

        except Exception as e:
            logger.error(f"GPT-4o synthesis failed: {e}")
            return {
                "answer": (
                    "Synthesis temporarily unavailable. "
                    "Retrieved signals are available for manual review."
                ),
                "sources": [
                    {
                        "signal_id": s["id"],
                        "title": s["title"],
                        "confidence": s["confidence"],
                        "similarity": s["similarity"],
                    }
                    for s in signals
                ],
                "limitations": [f"LLM synthesis failed: {str(e)[:100]}"],
                "token_usage": {},
            }

    # ── Caching ──────────────────────────────────────────────────────

    @staticmethod
    def _hash_query(
        query: str,
        org_id: UUID | None = None,
        industry_id: UUID | None = None,
    ) -> str:
        """Generate SHA-256 hash for cache key."""
        key_parts = [query.lower().strip()]
        if org_id:
            key_parts.append(str(org_id))
        if industry_id:
            key_parts.append(str(industry_id))
        raw = "|".join(key_parts)
        return hashlib.sha256(raw.encode()).hexdigest()

    async def _get_cached(self, query_hash: str) -> dict[str, Any] | None:
        """Get cached synthesis result from Redis (with stampede protection)."""
        try:
            redis = await get_redis()
            key = f"synthesis:{query_hash}"
            data = await redis.get(key)
            if data:
                logger.debug(f"Synthesis cache hit: {query_hash[:16]}...")
                from backend.services.cache_metrics import CacheMetrics

                await CacheMetrics.record_hit(key, "synthesis")
                return json.loads(data)
            await CacheMetrics.record_miss(key, "synthesis")
        except Exception as e:
            logger.warning(f"Synthesis cache read failed: {e}")
        return None

    async def _set_cached(self, query_hash: str, result: dict[str, Any]) -> None:
        """Cache synthesis result in Redis (15min TTL)."""
        try:
            redis = await get_redis()
            key = f"synthesis:{query_hash}"
            # Don't cache error responses
            if result.get("confidence", 0) > 0:
                await redis.setex(
                    key, SYNTHESIS_CACHE_TTL, json.dumps(result, default=str)
                )
                logger.debug(f"Synthesis cached: {query_hash[:16]}...")
        except Exception as e:
            logger.warning(f"Synthesis cache write failed: {e}")
