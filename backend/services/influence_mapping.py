"""Influence mapping and network centrality service.

Identifies key influencers, power brokers, and decision-makers within entity networks.
Uses graph algorithms to map influence flows and predict cascade effects.

This is a P1 feature that builds on Entity Resolution 2.0 to add:
- Network centrality metrics (PageRank, betweenness, closeness)
- Influence propagation modeling
- Key player identification
- Influence path discovery
"""

import logging
from typing import Any
from uuid import UUID

import networkx as nx
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.entity import Entity, EntityRelationship

logger = logging.getLogger(__name__)


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
        graph = await self._build_network_graph(industry_id=industry_id)

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
            "entity_name": entity.canonical_name if entity else None,
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
        graph = await self._build_network_graph(
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
                        "entity_name": entity.canonical_name,
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
        graph = await self._build_network_graph()

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
                            "name": from_entity.canonical_name if from_entity else None,
                        },
                        "to_entity": {
                            "id": to_id,
                            "name": to_entity.canonical_name if to_entity else None,
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
        graph = await self._build_network_graph()

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
                    "entity_name": entity.canonical_name if entity else None,
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
            .where(
                and_(EntityRelationship.is_active == True, Entity.deleted_at.is_(None))
            )
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

        Useful for detecting rising stars, declining powers, or stability.

        Args:
            entity_id: Entity to track
            lookback_days: How far back to analyze
            granularity: Time granularity (daily, weekly, monthly)

        Returns:
            Time series of influence scores with trend analysis
        """
        # TODO: Implement temporal influence tracking
        # Requires storing historical relationship snapshots or event history

        logger.warning("Temporal influence tracking not yet implemented")

        return {
            "entity_id": str(entity_id),
            "lookback_days": lookback_days,
            "granularity": granularity,
            "note": "Temporal influence tracking requires historical relationship data storage",
        }
