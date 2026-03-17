"""Influence mapping and network centrality service.

Identifies key influencers, power brokers, and decision-makers within entity networks.
Uses graph algorithms to map influence flows and predict cascade effects.

This is a P1 feature that builds on Entity Resolution 2.0 to add:
- Network centrality metrics (PageRank, betweenness, closeness)
- Influence propagation modeling
- Key player identification
- Influence path discovery
- Temporal influence tracking (influence over time)
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import networkx as nx
import numpy as np
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.entity import Entity
from backend.models.entity_relationship import EntityRelationship
from backend.models.influence_snapshot import InfluenceSnapshot

logger = logging.getLogger(__name__)

# Module-level graph cache with TTL
_graph_cache: dict[str, tuple[nx.DiGraph, float]] = {}
_graph_cache_lock = asyncio.Lock()
_GRAPH_CACHE_TTL = 300  # 5 minutes


class InfluenceMappingService:
    """Network analysis service for identifying influential entities and relationships."""

    # Relationship type weights (higher = more influential)
    RELATIONSHIP_WEIGHTS = {
        "owns": 1.0,  # Ownership = strongest influence
        "controls": 0.95,  # Control relationship
        "employs": 0.85,  # Employment relationship
        "funds": 0.80,  # Financial relationship
        "partner": 0.70,  # Partnership
        "supplier": 0.60,  # Supply chain
        "customer": 0.55,  # Customer relationship
        "competitor": 0.30,  # Competitive (inverse influence)
        "affiliated": 0.50,  # General affiliation
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    async def calculate_entity_influence_score(
        self,
        entity_id: UUID,
        *,
        industry_id: UUID | None = None,
        algorithm: str = "composite",
    ) -> dict[str, Any]:
        """Calculate comprehensive influence score for an entity.

        Uses multiple centrality metrics to build composite influence score:
        - PageRank: Global importance in network
        - Betweenness: Bridge/broker position
        - Closeness: Access to rest of network
        - Degree: Direct connections count
        - Eigenvector: Connected to other influential nodes

        Args:
            entity_id: Entity to score
            industry_id: Optional industry filter for network construction
            algorithm: Scoring algorithm ('pagerank', 'betweenness', 'composite')

        Returns:
            Influence metrics and overall score
        """
        # Build network graph
        graph = await self._get_or_build_graph(industry_id=industry_id)

        if not graph.has_node(str(entity_id)):
            return {
                "entity_id": str(entity_id),
                "influence_score": 0.0,
                "error": "Entity not found in network graph",
            }

        # Calculate centrality metrics
        node_id = str(entity_id)

        # PageRank (importance)
        pagerank_scores = nx.pagerank(graph, weight="weight")
        pagerank_score = pagerank_scores.get(node_id, 0.0)

        # Betweenness (broker position)
        betweenness_scores = nx.betweenness_centrality(graph, weight="weight")
        betweenness_score = betweenness_scores.get(node_id, 0.0)

        # Closeness (access to network)
        if nx.is_strongly_connected(graph):
            closeness_scores = nx.closeness_centrality(graph, distance="weight")
            closeness_score = closeness_scores.get(node_id, 0.0)
        else:
            # Use weakly connected component
            closeness_score = 0.0

        # Degree centrality (direct connections)
        degree_scores = nx.degree_centrality(graph)
        degree_score = degree_scores.get(node_id, 0.0)

        # Eigenvector centrality (connected to influential nodes)
        try:
            eigenvector_scores = nx.eigenvector_centrality(
                graph, weight="weight", max_iter=1000
            )
            eigenvector_score = eigenvector_scores.get(node_id, 0.0)
        except nx.PowerIterationFailedConvergence:
            logger.warning(
                f"Eigenvector centrality failed to converge for entity {entity_id}"
            )
            eigenvector_score = 0.0

        # Composite score (weighted average)
        composite_score = (
            pagerank_score * 0.30
            + betweenness_score * 0.25  # Global importance
            + eigenvector_score * 0.20  # Broker position
            + degree_score * 0.15  # Connected to influencers
            + closeness_score * 0.10  # Direct connections  # Network access
        )

        # Get entity metadata
        entity = await self.db.get(Entity, entity_id)

        return {
            "entity_id": str(entity_id),
            "entity_name": entity.name if entity else None,
            "influence_score": round(composite_score, 4),
            "metrics": {
                "pagerank": round(pagerank_score, 4),
                "betweenness": round(betweenness_score, 4),
                "eigenvector": round(eigenvector_score, 4),
                "degree": round(degree_score, 4),
                "closeness": round(closeness_score, 4),
            },
            "interpretation": self._interpret_influence_score(composite_score),
            "network_size": graph.number_of_nodes(),
        }

    async def identify_key_influencers(
        self,
        *,
        industry_id: UUID | None = None,
        entity_type: str | None = None,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """Identify the most influential entities in a network.

        Args:
            industry_id: Filter by industry
            entity_type: Filter by entity type (company, person, etc.)
            top_k: Number of top influencers to return

        Returns:
            Ranked list of influential entities
        """
        # Build network
        graph = await self._get_or_build_graph(
            industry_id=industry_id, entity_type=entity_type
        )

        # Calculate PageRank for all nodes
        pagerank_scores = nx.pagerank(graph, weight="weight")

        # Sort by score
        ranked_entities = sorted(
            pagerank_scores.items(), key=lambda x: x[1], reverse=True
        )[:top_k]

        # Fetch entity details
        influencers = []
        for entity_id_str, score in ranked_entities:
            entity_id = UUID(entity_id_str)
            entity = await self.db.get(Entity, entity_id)

            if entity:
                # Get full influence metrics
                metrics = await self.calculate_entity_influence_score(
                    entity_id, industry_id=industry_id
                )

                influencers.append(
                    {
                        "entity_id": str(entity.id),
                        "entity_name": entity.name,
                        "entity_type": entity.entity_type,
                        "influence_score": round(score, 4),
                        "rank": len(influencers) + 1,
                        "full_metrics": metrics.get("metrics", {}),
                    }
                )

        return influencers

    async def find_influence_path(
        self,
        source_entity_id: UUID,
        target_entity_id: UUID,
        *,
        max_hops: int = 5,
    ) -> dict[str, Any]:
        """Find the influence path between two entities.

        Identifies how influence flows from source to target through intermediaries.

        Args:
            source_entity_id: Starting entity
            target_entity_id: Target entity
            max_hops: Maximum path length to consider

        Returns:
            Influence path with intermediaries and strength
        """
        # Build network
        graph = await self._get_or_build_graph()

        source_id = str(source_entity_id)
        target_id = str(target_entity_id)

        if not graph.has_node(source_id) or not graph.has_node(target_id):
            return {
                "source_entity_id": source_id,
                "target_entity_id": target_id,
                "path_exists": False,
                "error": "One or both entities not found in network",
            }

        try:
            # Find shortest weighted path
            path = nx.shortest_path(
                graph,
                source=source_id,
                target=target_id,
                weight="weight",
                method="dijkstra",
            )

            if len(path) - 1 > max_hops:
                return {
                    "source_entity_id": source_id,
                    "target_entity_id": target_id,
                    "path_exists": True,
                    "too_long": True,
                    "path_length": len(path) - 1,
                    "max_hops": max_hops,
                }

            # Build path details
            path_details = []
            total_influence = 1.0

            for i in range(len(path) - 1):
                from_id = path[i]
                to_id = path[i + 1]

                # Get edge data
                edge_data = graph.get_edge_data(from_id, to_id)
                relationship_type = edge_data.get("relationship_type", "unknown")
                strength = edge_data.get("strength", 0.5)

                # Get entity details
                from_entity = await self.db.get(Entity, UUID(from_id))
                to_entity = await self.db.get(Entity, UUID(to_id))

                path_details.append(
                    {
                        "from_entity": {
                            "id": from_id,
                            "name": from_entity.name if from_entity else None,
                        },
                        "to_entity": {
                            "id": to_id,
                            "name": to_entity.name if to_entity else None,
                        },
                        "relationship_type": relationship_type,
                        "strength": round(strength, 3),
                    }
                )

                # Compound influence strength
                total_influence *= strength

            return {
                "source_entity_id": source_id,
                "target_entity_id": target_id,
                "path_exists": True,
                "path_length": len(path) - 1,
                "total_influence_strength": round(total_influence, 4),
                "path": path_details,
                "interpretation": (
                    f"Influence path of {len(path) - 1} hops with "
                    f"{round(total_influence * 100, 1)}% strength"
                ),
            }

        except nx.NetworkXNoPath:
            return {
                "source_entity_id": source_id,
                "target_entity_id": target_id,
                "path_exists": False,
                "message": "No influence path found between entities",
            }

    async def predict_influence_cascade(
        self,
        origin_entity_id: UUID,
        *,
        cascade_type: str = "positive",  # positive, negative, neutral
        propagation_decay: float = 0.8,
        max_depth: int = 3,
        min_influence_threshold: float = 0.1,
    ) -> dict[str, Any]:
        """Predict how influence/impact cascades through the network.

        Example: If company X goes bankrupt, which entities are affected and how much?

        Args:
            origin_entity_id: Starting point of cascade
            cascade_type: Type of influence (positive, negative, neutral)
            propagation_decay: How much influence decays at each hop (0-1)
            max_depth: Maximum cascade depth
            min_influence_threshold: Minimum influence to consider

        Returns:
            Cascade prediction with affected entities and impact scores
        """
        # Build network
        graph = await self._get_or_build_graph()

        origin_id = str(origin_entity_id)

        if not graph.has_node(origin_id):
            return {
                "origin_entity_id": origin_id,
                "error": "Origin entity not found in network",
            }

        # BFS traversal with influence propagation
        affected_entities = {}
        queue = [(origin_id, 1.0, 0)]  # (entity_id, influence_strength, depth)
        visited = set()

        while queue:
            current_id, current_influence, depth = queue.pop(0)

            if current_id in visited or depth > max_depth:
                continue

            visited.add(current_id)

            # Record affected entity
            if current_id != origin_id and current_influence >= min_influence_threshold:
                entity = await self.db.get(Entity, UUID(current_id))
                affected_entities[current_id] = {
                    "entity_id": current_id,
                    "entity_name": entity.name if entity else None,
                    "influence_received": round(current_influence, 4),
                    "cascade_depth": depth,
                }

            # Propagate to neighbors
            for neighbor in graph.successors(current_id):
                if neighbor not in visited:
                    edge_data = graph.get_edge_data(current_id, neighbor)
                    edge_strength = edge_data.get("strength", 0.5)

                    # Calculate propagated influence
                    propagated_influence = (
                        current_influence * edge_strength * propagation_decay
                    )

                    if propagated_influence >= min_influence_threshold:
                        queue.append((neighbor, propagated_influence, depth + 1))

        # Sort by influence received
        sorted_affected = sorted(
            affected_entities.values(),
            key=lambda x: x["influence_received"],
            reverse=True,
        )

        return {
            "origin_entity_id": origin_id,
            "cascade_type": cascade_type,
            "total_affected_entities": len(sorted_affected),
            "max_depth_reached": (
                max(e["cascade_depth"] for e in sorted_affected)
                if sorted_affected
                else 0
            ),
            "affected_entities": sorted_affected,
            "propagation_parameters": {
                "decay_rate": propagation_decay,
                "max_depth": max_depth,
                "min_threshold": min_influence_threshold,
            },
        }

    async def _get_or_build_graph(
        self,
        *,
        industry_id: UUID | None = None,
        entity_type: str | None = None,
    ) -> nx.DiGraph:
        """Get cached graph or build a new one.

        Uses a TTL-based in-memory cache keyed by (industry_id, entity_type).
        An asyncio.Lock prevents concurrent builds for the same cache key.
        """
        cache_key = f"{industry_id}:{entity_type}"

        # Fast path: check cache without lock
        if cache_key in _graph_cache:
            graph, cached_at = _graph_cache[cache_key]
            if (time.time() - cached_at) < _GRAPH_CACHE_TTL:
                return graph

        # Slow path: acquire lock, double-check, then build
        async with _graph_cache_lock:
            if cache_key in _graph_cache:
                graph, cached_at = _graph_cache[cache_key]
                if (time.time() - cached_at) < _GRAPH_CACHE_TTL:
                    return graph

            graph = await self._build_network_graph(
                industry_id=industry_id, entity_type=entity_type
            )
            _graph_cache[cache_key] = (graph, time.time())
            return graph

    async def _build_network_graph(
        self,
        *,
        industry_id: UUID | None = None,
        entity_type: str | None = None,
    ) -> nx.DiGraph:
        """Build NetworkX directed graph from entity relationships.

        Args:
            industry_id: Filter entities by industry
            entity_type: Filter entities by type

        Returns:
            NetworkX DiGraph with weighted edges
        """
        # Fetch all active relationships
        query = (
            select(EntityRelationship, Entity)
            .join(Entity, EntityRelationship.source_entity_id == Entity.id)
            .where(EntityRelationship.is_active == True)
        )

        if industry_id:
            query = query.where(Entity.industry_id == industry_id)

        if entity_type:
            query = query.where(Entity.entity_type == entity_type)

        result = await self.db.execute(query)
        relationships = result.all()

        # Build graph
        graph = nx.DiGraph()

        for rel, entity in relationships:
            source_id = str(rel.source_entity_id)
            target_id = str(rel.target_entity_id)

            # Calculate edge weight (combination of strength, confidence, and relationship type)
            relationship_weight = self.RELATIONSHIP_WEIGHTS.get(
                rel.relationship_type, 0.5
            )
            edge_weight = rel.strength * rel.confidence * relationship_weight

            # Add edge
            graph.add_edge(
                source_id,
                target_id,
                weight=edge_weight,
                strength=rel.strength,
                confidence=rel.confidence,
                relationship_type=rel.relationship_type,
            )

            # If bidirectional, add reverse edge
            if rel.bidirectional:
                graph.add_edge(
                    target_id,
                    source_id,
                    weight=edge_weight,
                    strength=rel.strength,
                    confidence=rel.confidence,
                    relationship_type=rel.relationship_type,
                )

        logger.info(
            f"Built network graph with {graph.number_of_nodes()} nodes and {graph.number_of_edges()} edges"
        )

        return graph

    @staticmethod
    def _interpret_influence_score(score: float) -> str:
        """Interpret influence score into human-readable category."""
        if score >= 0.15:
            return "Very High Influence - Major power broker in network"
        elif score >= 0.08:
            return "High Influence - Key player with significant reach"
        elif score >= 0.04:
            return "Moderate Influence - Established position in network"
        elif score >= 0.02:
            return "Low Influence - Peripheral player"
        else:
            return "Minimal Influence - Limited network connections"

    async def get_influence_changes_over_time(
        self,
        entity_id: UUID,
        *,
        lookback_days: int = 90,
        granularity: str = "weekly",
    ) -> dict[str, Any]:
        """Track how an entity's influence has changed over time.

        Reads stored ``InfluenceSnapshot`` rows and computes trend statistics.
        If no snapshots exist yet, a live snapshot is recorded and returned as the
        single data-point so the system bootstraps automatically.

        Args:
            entity_id: Entity to track
            lookback_days: How far back to analyze
            granularity: Time granularity ('daily', 'weekly', 'monthly')

        Returns:
            Time series of influence scores with trend analysis
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)

        query = (
            select(InfluenceSnapshot)
            .where(
                and_(
                    InfluenceSnapshot.entity_id == entity_id,
                    InfluenceSnapshot.snapshot_date >= cutoff,
                )
            )
            .order_by(InfluenceSnapshot.snapshot_date)
        )

        result = await self.db.execute(query)
        snapshots = result.scalars().all()

        # Bootstrap: if no snapshots exist, record one now
        if not snapshots:
            live = await self.record_influence_snapshot(entity_id)
            if live:
                snapshots = [live]

        if not snapshots:
            return {
                "entity_id": str(entity_id),
                "lookback_days": lookback_days,
                "granularity": granularity,
                "data_points": 0,
                "time_series": [],
                "trend": "insufficient_data",
            }

        # ── Build time-series ──────────────────────────────────────────
        time_series = [
            {
                "date": s.snapshot_date.isoformat(),
                "influence_score": round(s.influence_score, 4),
                "metrics": {
                    "pagerank": round(s.pagerank, 4),
                    "betweenness": round(s.betweenness, 4),
                    "eigenvector": round(s.eigenvector, 4),
                    "degree": round(s.degree, 4),
                    "closeness": round(s.closeness, 4),
                },
                "network_size": s.network_size,
                "direct_connections": s.direct_connections,
            }
            for s in snapshots
        ]

        # ── Aggregate by granularity ───────────────────────────────────
        if granularity in ("weekly", "monthly") and len(time_series) > 1:
            time_series = self._aggregate_time_series(time_series, granularity)

        # ── Trend analysis ─────────────────────────────────────────────
        scores = [pt["influence_score"] for pt in time_series]
        trend_info = self._compute_trend(scores)

        entity = await self.db.get(Entity, entity_id)

        return {
            "entity_id": str(entity_id),
            "entity_name": entity.name if entity else None,
            "lookback_days": lookback_days,
            "granularity": granularity,
            "data_points": len(time_series),
            "time_series": time_series,
            **trend_info,
        }

    # ── Snapshot Recording ──────────────────────────────────────────────

    async def record_influence_snapshot(
        self,
        entity_id: UUID,
        *,
        industry_id: UUID | None = None,
        source: str = "scheduled",
    ) -> InfluenceSnapshot | None:
        """Compute current influence metrics and persist a snapshot row.

        Call this on a schedule (e.g. daily cron) to build the time-series
        that ``get_influence_changes_over_time`` reads.

        Args:
            entity_id: Entity to snapshot
            industry_id: Optional industry scope
            source: Label for what triggered the snapshot

        Returns:
            The persisted InfluenceSnapshot, or None if entity not in graph
        """
        metrics = await self.calculate_entity_influence_score(
            entity_id, industry_id=industry_id
        )

        if metrics.get("error"):
            logger.warning("Cannot snapshot entity %s: %s", entity_id, metrics["error"])
            return None

        graph = await self._get_or_build_graph(industry_id=industry_id)
        node_id = str(entity_id)
        direct_connections = graph.degree(node_id) if graph.has_node(node_id) else 0

        snapshot = InfluenceSnapshot(
            entity_id=entity_id,
            snapshot_date=datetime.now(timezone.utc),
            influence_score=metrics["influence_score"],
            pagerank=metrics["metrics"]["pagerank"],
            betweenness=metrics["metrics"]["betweenness"],
            eigenvector=metrics["metrics"]["eigenvector"],
            degree=metrics["metrics"]["degree"],
            closeness=metrics["metrics"]["closeness"],
            network_size=metrics.get("network_size"),
            direct_connections=direct_connections,
            industry_id=industry_id,
            source=source,
        )

        self.db.add(snapshot)
        await self.db.flush()

        logger.info(
            "Recorded influence snapshot for entity %s: score=%.4f",
            entity_id,
            snapshot.influence_score,
        )
        return snapshot

    async def record_all_influence_snapshots(
        self,
        *,
        industry_id: UUID | None = None,
        source: str = "scheduled",
    ) -> int:
        """Snapshot every entity currently in the network graph.

        Intended to be called from a daily background job:

            service = InfluenceMappingService(db)
            count = await service.record_all_influence_snapshots()

        Returns:
            Number of snapshots recorded
        """
        graph = await self._get_or_build_graph(industry_id=industry_id)
        count = 0

        for node_id in graph.nodes():
            try:
                entity_id = UUID(node_id)
                snap = await self.record_influence_snapshot(
                    entity_id, industry_id=industry_id, source=source
                )
                if snap:
                    count += 1
            except (ValueError, Exception) as exc:
                logger.warning("Skipping node %s: %s", node_id, exc)

        await self.db.commit()
        logger.info("Recorded %d influence snapshots (industry=%s)", count, industry_id)
        return count

    # ── Private helpers ─────────────────────────────────────────────────

    @staticmethod
    def _aggregate_time_series(
        points: list[dict[str, Any]], granularity: str
    ) -> list[dict[str, Any]]:
        """Bucket raw data-points into weekly or monthly averages."""
        from collections import defaultdict

        buckets: dict[str, list[dict]] = defaultdict(list)

        for pt in points:
            dt = datetime.fromisoformat(pt["date"])
            if granularity == "weekly":
                # ISO week start (Monday)
                key = (dt - timedelta(days=dt.weekday())).strftime("%Y-%m-%d")
            else:
                key = dt.strftime("%Y-%m-01")
            buckets[key].append(pt)

        aggregated = []
        for bucket_date, pts in sorted(buckets.items()):
            scores = [p["influence_score"] for p in pts]
            aggregated.append(
                {
                    "date": bucket_date,
                    "influence_score": round(float(np.mean(scores)), 4),
                    "data_points_in_bucket": len(pts),
                    "metrics": pts[-1]["metrics"],  # latest in bucket
                    "network_size": pts[-1].get("network_size"),
                    "direct_connections": pts[-1].get("direct_connections"),
                }
            )
        return aggregated

    @staticmethod
    def _compute_trend(scores: list[float]) -> dict[str, Any]:
        """Compute trend direction, magnitude, and volatility from a score series."""
        if len(scores) < 2:
            return {
                "trend": "insufficient_data",
                "trend_direction": 0,
                "score_change": 0.0,
                "score_change_pct": 0.0,
                "volatility": 0.0,
                "current_score": scores[0] if scores else 0.0,
            }

        first, last = scores[0], scores[-1]
        change = last - first
        change_pct = (change / first * 100) if first != 0 else 0.0
        volatility = float(np.std(scores))

        # Linear regression slope for direction
        x = np.arange(len(scores), dtype=float)
        slope = float(np.polyfit(x, scores, 1)[0])

        if abs(change_pct) < 5:
            trend = "stable"
        elif change_pct > 20:
            trend = "rising_fast"
        elif change_pct > 0:
            trend = "rising"
        elif change_pct < -20:
            trend = "declining_fast"
        else:
            trend = "declining"

        return {
            "trend": trend,
            "trend_direction": 1 if slope > 0 else (-1 if slope < 0 else 0),
            "score_change": round(change, 4),
            "score_change_pct": round(change_pct, 2),
            "volatility": round(volatility, 4),
            "current_score": round(last, 4),
            "period_high": round(float(max(scores)), 4),
            "period_low": round(float(min(scores)), 4),
        }
