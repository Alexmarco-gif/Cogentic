"""Replicability blind test engine — measures intelligence uniqueness.

Implements Metric 4: Replicability Score (<20% ChatGPT-replicable).

Methodology:
  1. Collect recent ESIP synthesis outputs (proprietary intelligence)
  2. Send the same queries to a baseline LLM without proprietary context
  3. Compare the two outputs using semantic similarity + content analysis
  4. A HIGH replicability score is BAD (means other tools can reproduce our output)
  5. Target: <20% replicability → 80%+ of our intelligence is UNIQUE

Comparison dimensions:
  - Semantic overlap (embedding cosine similarity)
  - Named entity overlap (are the same entities mentioned?)
  - Causal insight uniqueness (does baseline predict the same chains?)
  - Specificity (does ESIP cite specific data points not in baseline?)
"""

import logging
import re
from typing import Any

from openai import AsyncOpenAI
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.ai.embeddings import EmbeddingService
from backend.config import get_settings
from backend.models.user_feedback import UserFeedback

logger = logging.getLogger(__name__)
settings = get_settings()


# Singleton client
_openai_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _openai_client


class ReplicabilityBlindTestService:
    """Runs blind tests comparing ESIP synthesis vs baseline LLM.

    "Blind" because the baseline LLM gets the same question but
    zero proprietary context—only public knowledge.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.client = _get_client()
        self.embedding_service = EmbeddingService()

    async def run_blind_test(
        self,
        *,
        sample_size: int = 10,
        baseline_model: str = "gpt-4o",
    ) -> dict[str, Any]:
        """Run a batch of blind tests on recent synthesis outputs.

        Args:
            sample_size: Number of recent synthesis queries to test.
            baseline_model: The LLM model to use as baseline.

        Returns:
            Aggregate replicability score and per-test breakdown.
        """
        # Get recent user feedback entries that contain synthesis context
        # These record what the system actually produced
        feedback_result = await self.db.execute(
            select(UserFeedback)
            .where(
                UserFeedback.context.isnot(None),
                UserFeedback.context["query"].isnot(None),
                UserFeedback.context["synthesis_output"].isnot(None),
            )
            .order_by(desc(UserFeedback.created_at))
            .limit(sample_size)
        )
        feedback_items = feedback_result.scalars().all()

        if not feedback_items:
            return await self._fallback_blind_test()

        test_results: list[dict[str, Any]] = []

        for item in feedback_items:
            ctx = item.context or {}
            query = ctx.get("query", "")
            esip_output = ctx.get("synthesis_output", "")

            if not query or not esip_output:
                continue

            try:
                result = await self._compare_single(
                    query=query,
                    esip_output=esip_output,
                    baseline_model=baseline_model,
                )
                test_results.append(result)
            except Exception as e:
                logger.warning("Blind test failed for query %s: %s", query[:50], e)
                continue

        if not test_results:
            return await self._fallback_blind_test()

        # Aggregate
        avg_replicability = sum(r["replicability_pct"] for r in test_results) / len(
            test_results
        )

        return {
            "replicability_score_pct": round(avg_replicability, 2),
            "tests_run": len(test_results),
            "meets_target": avg_replicability < 20.0,
            "baseline_model": baseline_model,
            "test_results": test_results,
            "dimensions": {
                "avg_semantic_overlap": round(
                    sum(r["semantic_overlap"] for r in test_results)
                    / len(test_results),
                    3,
                ),
                "avg_entity_overlap": round(
                    sum(r["entity_overlap_pct"] for r in test_results)
                    / len(test_results),
                    1,
                ),
                "avg_specificity_gap": round(
                    sum(r["specificity_gap"] for r in test_results) / len(test_results),
                    1,
                ),
            },
        }

    async def _compare_single(
        self,
        *,
        query: str,
        esip_output: str,
        baseline_model: str,
    ) -> dict[str, Any]:
        """Compare ESIP output vs baseline for a single query."""

        # Step 1: Get baseline response (no proprietary context)
        baseline_prompt = (
            "You are a general-purpose intelligence analyst. "
            "Answer the following question using only your training knowledge. "
            "Be as detailed and specific as possible.\n\n"
            f"Question: {query}"
        )

        baseline_response = await self.client.chat.completions.create(
            model=baseline_model,
            messages=[{"role": "user", "content": baseline_prompt}],
            temperature=0.3,
            max_tokens=1500,
        )
        baseline_output = baseline_response.choices[0].message.content or ""

        # Step 2: Compute semantic similarity via embeddings
        try:
            esip_embedding = await self.embedding_service.embed_text(esip_output[:8000])
            baseline_embedding = await self.embedding_service.embed_text(
                baseline_output[:8000]
            )
            semantic_overlap = self._cosine_similarity(
                esip_embedding, baseline_embedding
            )
        except Exception:
            semantic_overlap = 0.5  # Fallback

        # Step 3: Entity overlap — extract named entities from both
        esip_entities = self._extract_entities(esip_output)
        baseline_entities = self._extract_entities(baseline_output)

        if esip_entities:
            entity_overlap = (
                len(esip_entities & baseline_entities) / len(esip_entities) * 100
            )
        else:
            entity_overlap = 0.0

        # Step 4: Specificity — count concrete data points
        esip_specifics = self._count_specifics(esip_output)
        baseline_specifics = self._count_specifics(baseline_output)
        specificity_gap = max(esip_specifics - baseline_specifics, 0)

        # Step 5: Causal insight overlap — check for predictive statements
        esip_causal = self._extract_causal_statements(esip_output)
        baseline_causal = self._extract_causal_statements(baseline_output)
        causal_unique = len(esip_causal - baseline_causal) if esip_causal else 0

        # Step 6: Composite replicability score
        # Higher = MORE replicable (BAD). Lower = MORE unique (GOOD).
        replicability_pct = self._compute_replicability(
            semantic_overlap=semantic_overlap,
            entity_overlap_pct=entity_overlap,
            specificity_gap=specificity_gap,
            causal_unique=causal_unique,
        )

        return {
            "query": query[:100],
            "replicability_pct": round(replicability_pct, 1),
            "semantic_overlap": round(semantic_overlap, 3),
            "entity_overlap_pct": round(entity_overlap, 1),
            "specificity_gap": specificity_gap,
            "causal_unique_count": causal_unique,
            "esip_entities_count": len(esip_entities),
            "baseline_entities_count": len(baseline_entities),
            "esip_specifics_count": esip_specifics,
            "baseline_specifics_count": baseline_specifics,
        }

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two embedding vectors."""
        import math

        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def _extract_entities(self, text: str) -> set[str]:
        """Extract capitalized named entities from text.

        Simple heuristic — multi-word sequences starting with capitals.
        Not a full NER but sufficient for overlap comparison.
        """
        # Match 2+ word sequences where words start with capitals
        pattern = r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b"
        matches = set(re.findall(pattern, text))
        # Also match single-word proper nouns that look like org/person names
        single_pattern = (
            r"\b([A-Z][a-z]{2,}(?:Corp|Inc|Ltd|Bank|Group|Holdings|Capital|Tech))\b"
        )
        matches.update(re.findall(single_pattern, text))
        return matches

    def _count_specifics(self, text: str) -> int:
        """Count concrete data points: numbers, percentages, dates, amounts."""
        patterns = [
            r"\$[\d,.]+[BMK]?\b",  # Dollar amounts
            r"₦[\d,.]+[BMK]?\b",  # Naira amounts
            r"\b\d+(?:\.\d+)?%",  # Percentages
            r"\b(?:January|February|March|April|May|June|July|August"
            r"|September|October|November|December)\s+\d{1,2},?\s*\d{4}",
            r"\bQ[1-4]\s+\d{4}\b",  # Quarters
            r"\b\d{1,3}(?:,\d{3})+\b",  # Large numbers
        ]
        count = 0
        for pattern in patterns:
            count += len(re.findall(pattern, text))
        return count

    def _extract_causal_statements(self, text: str) -> set[str]:
        """Extract statements implying causality or prediction."""
        causal_keywords = [
            r"will\s+(?:likely\s+)?(?:lead|cause|result|trigger|drive)",
            r"(?:may|could|might)\s+(?:cause|trigger|result\s+in)",
            r"as\s+a\s+(?:direct\s+)?result\s+of",
            r"(?:consequently|therefore|thus|hence)",
            r"is\s+(?:expected|projected|forecast)",
            r"predic(?:t|tion|ted)",
        ]
        statements: set[str] = set()
        sentences = re.split(r"[.!?]+", text)
        for sentence in sentences:
            s = sentence.strip()
            for pattern in causal_keywords:
                if re.search(pattern, s, re.IGNORECASE):
                    # Normalize for comparison
                    normalized = re.sub(r"\s+", " ", s.lower().strip())
                    if len(normalized) > 20:
                        statements.add(normalized[:80])
                    break
        return statements

    def _compute_replicability(
        self,
        *,
        semantic_overlap: float,
        entity_overlap_pct: float,
        specificity_gap: int,
        causal_unique: int,
    ) -> float:
        """Compute composite replicability score (0-100).

        Lower is BETTER (means less replicable).

        Weights:
          - Semantic overlap: 40% (high similarity = bad)
          - Entity overlap: 25% (same entities mentioned = bad)
          - Specificity gap: 20% (more unique data points = good)
          - Causal unique: 15% (unique causal insights = good)
        """
        # Semantic: 0-1 → 0-100
        semantic_score = semantic_overlap * 100

        # Entity overlap already 0-100
        entity_score = entity_overlap_pct

        # Specificity gap: more unique specifics = lower replicability
        # Cap at 20 unique data points → 100% reduction
        specificity_reduction = min(specificity_gap / 20, 1.0) * 100

        # Causal unique: more unique causal insights = lower replicability
        # Cap at 5 unique causal statements → 100% reduction
        causal_reduction = min(causal_unique / 5, 1.0) * 100

        replicability = (
            semantic_score * 0.40
            + entity_score * 0.25
            - specificity_reduction * 0.20
            - causal_reduction * 0.15
        )

        # Clamp to 0-100
        return max(0.0, min(100.0, replicability))

    async def _fallback_blind_test(self) -> dict[str, Any]:
        """Fallback when no synthesis context data is available.

        Uses data coverage heuristic similar to moat_metrics.py.
        """
        from backend.models.causal_event import CausalEdge, CausalEvent
        from backend.models.entity import Entity
        from backend.models.entity_relationship import EntityRelationship

        entity_count = (
            await self.db.execute(select(func.count(Entity.id)))
        ).scalar() or 0
        causal_count = (
            await self.db.execute(select(func.count(CausalEvent.id)))
        ).scalar() or 0
        edge_count = (
            await self.db.execute(select(func.count(CausalEdge.id)))
        ).scalar() or 0
        rel_count = (
            await self.db.execute(select(func.count(EntityRelationship.id)))
        ).scalar() or 0

        # More proprietary data → lower replicability
        data_depth = entity_count + causal_count + edge_count + rel_count
        estimated_replicability = max(10.0, 80.0 - (data_depth / 50))

        return {
            "replicability_score_pct": round(estimated_replicability, 2),
            "tests_run": 0,
            "meets_target": estimated_replicability < 20.0,
            "baseline_model": "n/a (fallback heuristic)",
            "note": (
                "No synthesis outputs with stored context found. "
                "Score estimated from proprietary data coverage. "
                "Run more synthesis queries to enable LLM-based blind testing."
            ),
            "data_depth": {
                "entities": entity_count,
                "causal_events": causal_count,
                "causal_edges": edge_count,
                "relationships": rel_count,
            },
        }
