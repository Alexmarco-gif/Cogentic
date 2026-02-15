"""Agent tool definitions for the AI Chat Agent.

Seven function-calling tools that the LLM can invoke:
  1. search_signals    — Query existing signals in the database
  2. deep_search       — Multi-source live search
  3. synthesize_signal — Create signal from live data
  4. get_analytics     — Trends, anomalies, forecasts
  5. get_recommendations — Actionable advice for a signal
  6. browse_ontology   — Domain context lookup
  7. create_contract   — Create a new signal contract

Each tool is defined as:
  - An OpenAI function-calling schema (for the LLM)
  - An async executor function (for the agent core)
"""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.models.signal import Signal
from backend.models.signal_contract import SignalContract

logger = logging.getLogger(__name__)
settings = get_settings()


# ── OpenAI Function Schemas ──────────────────────────────────────────
# These schemas are sent to GPT-4o so it knows how to call each tool.

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search_signals",
            "description": (
                "Search existing signals in the database by keyword, type, or industry. "
                "Use when the user asks about current signal values, trends, or wants to "
                "find specific signals."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query — keywords, signal title, or topic.",
                    },
                    "signal_type": {
                        "type": "string",
                        "enum": [
                            "news",
                            "social",
                            "regulatory",
                            "financial",
                            "market",
                            "technology",
                        ],
                        "description": "Optional signal type filter.",
                    },
                    "min_confidence": {
                        "type": "number",
                        "description": "Minimum confidence threshold (0.0-1.0). Defaults to 0.6.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results to return (1-20). Defaults to 10.",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "deep_search",
            "description": (
                "Perform a deep multi-source live search when existing signals don't cover "
                "the topic. Returns ranked results with optional AI synthesis. "
                "Use when there's no existing signal coverage for the user's question."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query — what to search for across sources.",
                    },
                    "include_synthesis": {
                        "type": "boolean",
                        "description": "Whether to include AI synthesis of results. Defaults to true.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Max results to return (1-20). Defaults to 10.",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "synthesize_signal",
            "description": (
                "Create an on-demand signal synthesis from live data using RAG + LLM. "
                "Use when a gap in signal coverage is discovered and the user needs "
                "intelligence on a specific topic right now."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The intelligence question to synthesize (10-1000 chars).",
                    },
                    "industry": {
                        "type": "string",
                        "description": "Optional industry context (e.g., fintech, fmcg, energy).",
                    },
                },
                "required": ["question"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_analytics",
            "description": (
                "Get analytics data: trending signals, anomalies, or signal statistics. "
                "Use when the user asks about patterns, predictions, or data trends."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "metric": {
                        "type": "string",
                        "enum": ["trending", "anomalies", "coverage", "stats"],
                        "description": "The analytics metric to retrieve.",
                    },
                    "signal_type": {
                        "type": "string",
                        "description": "Optional filter by signal type.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results (1-50). Defaults to 10.",
                    },
                },
                "required": ["metric"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_recommendations",
            "description": (
                "Get actionable recommendations for a specific signal or the user's "
                "organization. Shows related signals and suggested actions. "
                "Use when the user asks 'What should I do?' or wants advice."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "signal_id": {
                        "type": "string",
                        "description": "UUID of the signal to get recommendations for. If omitted, returns top org-wide recommendations.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max recommendations (1-20). Defaults to 5.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browse_ontology",
            "description": (
                "Browse industry ontologies and domain knowledge. Look up industries, "
                "domain taxonomies, and signal catalog templates. "
                "Use for industry-specific context or when the user asks about "
                "available industries and signal types."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["list_industries", "get_industry", "search_catalog"],
                        "description": "What ontology action to perform.",
                    },
                    "industry_code": {
                        "type": "string",
                        "description": "Industry code (e.g., 'fintech', 'fmcg', 'energy'). Required for get_industry.",
                    },
                    "search_term": {
                        "type": "string",
                        "description": "Search term for catalog search. Required for search_catalog.",
                    },
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_contract",
            "description": (
                "Create a new signal contract to track a specific signal. "
                "Use when the user explicitly wants to start monitoring something new."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the signal contract (e.g., 'Nigeria Fintech Funding Rounds').",
                    },
                    "description": {
                        "type": "string",
                        "description": "What this contract tracks.",
                    },
                    "entity_type": {
                        "type": "string",
                        "description": "Type of entity tracked (e.g., 'company', 'product', 'regulation').",
                    },
                    "signal_type": {
                        "type": "string",
                        "enum": [
                            "news",
                            "social",
                            "regulatory",
                            "financial",
                            "market",
                            "technology",
                        ],
                        "description": "Type of signal to track.",
                    },
                    "industry": {
                        "type": "string",
                        "description": "Industry context (e.g., 'fintech', 'fmcg').",
                    },
                },
                "required": ["name", "entity_type", "signal_type"],
            },
        },
    },
]


# ── Tool Executors ───────────────────────────────────────────────────
# Each tool function receives (db, org_id, user_id, **tool_args)
# and returns a dict that gets serialized back to the LLM.


async def execute_search_signals(
    db: AsyncSession,
    org_id: UUID,
    user_id: UUID,
    *,
    query: str,
    signal_type: str | None = None,
    min_confidence: float = 0.6,
    limit: int = 10,
) -> dict[str, Any]:
    """Search signals in the database using text search + optional embedding similarity."""
    limit = max(1, min(limit, 20))

    # Full-text search on title and summary
    conditions = [
        text(
            "to_tsvector('english', COALESCE(s.title, '') || ' ' || COALESCE(s.summary, '')) "
            "@@ plainto_tsquery('english', :query)"
        ),
        Signal.confidence >= min_confidence,
    ]

    query_stmt = select(
        Signal.id,
        Signal.title,
        Signal.summary,
        Signal.signal_type,
        Signal.confidence,
        Signal.source_url,
        Signal.published_at,
        Signal.fetched_at,
    ).where(*conditions)

    if signal_type:
        query_stmt = query_stmt.where(Signal.signal_type == signal_type)

    # Scope to org or global signals
    query_stmt = query_stmt.where((Signal.org_id == org_id) | (Signal.org_id.is_(None)))

    query_stmt = query_stmt.order_by(Signal.confidence.desc()).limit(limit)

    result = await db.execute(query_stmt, {"query": query})
    rows = result.all()

    signals = []
    for row in rows:
        signals.append(
            {
                "id": str(row.id),
                "title": row.title or "Untitled",
                "summary": (row.summary or "")[:300],
                "signal_type": row.signal_type,
                "confidence": round(float(row.confidence), 2),
                "source_url": row.source_url,
                "published_at": (
                    row.published_at.isoformat() if row.published_at else None
                ),
            }
        )

    return {
        "tool": "search_signals",
        "query": query,
        "results": signals,
        "total": len(signals),
        "filters": {
            "signal_type": signal_type,
            "min_confidence": min_confidence,
        },
    }


async def execute_deep_search(
    db: AsyncSession,
    org_id: UUID,
    user_id: UUID,
    *,
    query: str,
    include_synthesis: bool = True,
    max_results: int = 10,
) -> dict[str, Any]:
    """Execute deep live search via DeepSearchService."""
    from backend.services.deep_search import DeepSearchService

    service = DeepSearchService(db)
    result = await service.search(
        query=query,
        user_id=user_id,
        org_id=org_id,
        synthesize=include_synthesis,
        max_results=max_results,
    )

    # Simplify for LLM context (avoid token bloat)
    simplified_results = []
    for r in result.get("results", [])[:max_results]:
        simplified_results.append(
            {
                "title": r.get("title", "Untitled"),
                "summary": (r.get("summary") or "")[:300],
                "confidence": r.get("confidence", 0.0),
                "similarity": r.get("similarity", 0.0),
                "source_url": r.get("source_url"),
            }
        )

    return {
        "tool": "deep_search",
        "query": query,
        "results": simplified_results,
        "total": len(simplified_results),
        "synthesis": result.get("synthesis"),
        "cached": result.get("cached", False),
        "response_time_ms": result.get("response_time_ms", 0),
    }


async def execute_synthesize_signal(
    db: AsyncSession,
    org_id: UUID,
    user_id: UUID,
    *,
    question: str,
    industry: str | None = None,
) -> dict[str, Any]:
    """Synthesize an on-demand signal from live data."""
    from backend.ai.synthesis import SynthesisService

    service = SynthesisService(db)
    result = await service.synthesize(
        query=question,
        user_id=user_id,
        org_id=org_id,
    )

    return {
        "tool": "synthesize_signal",
        "question": question,
        "industry": industry,
        "synthesis": result.get("synthesis"),
        "confidence": result.get("confidence", 0.0),
        "sources_used": result.get("sources_used", 0),
        "evidence": [
            {
                "title": e.get("title", ""),
                "snippet": (e.get("snippet") or "")[:200],
                "source_url": e.get("source_url"),
            }
            for e in result.get("evidence", [])[:5]
        ],
    }


async def execute_get_analytics(
    db: AsyncSession,
    org_id: UUID,
    user_id: UUID,
    *,
    metric: str,
    signal_type: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Get analytics data: trending, anomalies, coverage, or stats."""
    limit = max(1, min(limit, 50))

    if metric == "trending":
        # Get signals ordered by recent confidence increase
        result = await db.execute(
            select(
                Signal.id,
                Signal.title,
                Signal.signal_type,
                Signal.confidence,
                Signal.published_at,
            )
            .where(
                (Signal.org_id == org_id) | (Signal.org_id.is_(None)),
                Signal.confidence >= 0.6,
            )
            .order_by(Signal.published_at.desc().nullslast())
            .limit(limit)
        )
        rows = result.all()
        return {
            "tool": "get_analytics",
            "metric": "trending",
            "results": [
                {
                    "id": str(r.id),
                    "title": r.title or "Untitled",
                    "signal_type": r.signal_type,
                    "confidence": round(float(r.confidence), 2),
                    "published_at": (
                        r.published_at.isoformat() if r.published_at else None
                    ),
                }
                for r in rows
            ],
        }

    elif metric == "anomalies":
        # Get signals with low confidence (potential anomalies)
        result = await db.execute(
            select(
                Signal.id,
                Signal.title,
                Signal.signal_type,
                Signal.confidence,
            )
            .where(
                (Signal.org_id == org_id) | (Signal.org_id.is_(None)),
                Signal.confidence < 0.6,
                Signal.confidence > 0.0,
            )
            .order_by(Signal.confidence.asc())
            .limit(limit)
        )
        rows = result.all()
        return {
            "tool": "get_analytics",
            "metric": "anomalies",
            "results": [
                {
                    "id": str(r.id),
                    "title": r.title or "Untitled",
                    "signal_type": r.signal_type,
                    "confidence": round(float(r.confidence), 2),
                }
                for r in rows
            ],
        }

    elif metric == "coverage":
        # Count signals by type
        result = await db.execute(
            select(
                Signal.signal_type,
                func.count(Signal.id).label("count"),
                func.avg(Signal.confidence).label("avg_confidence"),
            )
            .where((Signal.org_id == org_id) | (Signal.org_id.is_(None)))
            .group_by(Signal.signal_type)
        )
        rows = result.all()
        return {
            "tool": "get_analytics",
            "metric": "coverage",
            "results": [
                {
                    "signal_type": r.signal_type,
                    "count": r.count,
                    "avg_confidence": round(float(r.avg_confidence or 0), 2),
                }
                for r in rows
            ],
        }

    elif metric == "stats":
        # Overall statistics
        total = await db.execute(
            select(func.count(Signal.id)).where(
                (Signal.org_id == org_id) | (Signal.org_id.is_(None))
            )
        )
        total_count = total.scalar_one()

        high_conf = await db.execute(
            select(func.count(Signal.id)).where(
                (Signal.org_id == org_id) | (Signal.org_id.is_(None)),
                Signal.confidence >= 0.85,
            )
        )
        high_conf_count = high_conf.scalar_one()

        avg_conf = await db.execute(
            select(func.avg(Signal.confidence)).where(
                (Signal.org_id == org_id) | (Signal.org_id.is_(None))
            )
        )
        avg_confidence = avg_conf.scalar_one()

        return {
            "tool": "get_analytics",
            "metric": "stats",
            "results": {
                "total_signals": total_count,
                "high_confidence_signals": high_conf_count,
                "avg_confidence": round(float(avg_confidence or 0), 2),
                "brief_eligible_pct": (
                    round(high_conf_count / total_count * 100, 1)
                    if total_count > 0
                    else 0
                ),
            },
        }

    return {
        "tool": "get_analytics",
        "metric": metric,
        "error": f"Unknown metric: {metric}",
    }


async def execute_get_recommendations(
    db: AsyncSession,
    org_id: UUID,
    user_id: UUID,
    *,
    signal_id: str | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    """Get recommendations for a signal or org-wide."""
    from backend.services.recommendation import RecommendationService

    service = RecommendationService(db)
    limit = max(1, min(limit, 20))

    if signal_id:
        recs = await service.get_for_signal(UUID(signal_id), limit=limit)
    else:
        recs = await service.get_active(limit=limit)

    return {
        "tool": "get_recommendations",
        "signal_id": signal_id,
        "results": [
            {
                "id": str(r.id),
                "source_type": r.source_type,
                "target_type": r.target_type,
                "target_id": str(r.target_id),
                "score": round(float(r.score), 2),
                "reason": r.reason,
            }
            for r in recs
        ],
        "total": len(recs),
    }


async def execute_browse_ontology(
    db: AsyncSession,
    org_id: UUID,
    user_id: UUID,
    *,
    action: str,
    industry_code: str | None = None,
    search_term: str | None = None,
) -> dict[str, Any]:
    """Browse industry ontologies, taxonomies, and signal catalog."""
    from backend.models.industry import Industry

    if action == "list_industries":
        result = await db.execute(
            select(
                Industry.id, Industry.name, Industry.slug, Industry.description
            ).order_by(Industry.name)
        )
        rows = result.all()
        return {
            "tool": "browse_ontology",
            "action": "list_industries",
            "results": [
                {
                    "id": str(r.id),
                    "name": r.name,
                    "slug": r.slug,
                    "description": r.description,
                }
                for r in rows
            ],
        }

    elif action == "get_industry" and industry_code:
        result = await db.execute(
            select(Industry).where(Industry.slug == industry_code)
        )
        industry = result.scalar_one_or_none()
        if not industry:
            return {
                "tool": "browse_ontology",
                "action": "get_industry",
                "error": f"Industry '{industry_code}' not found.",
            }
        return {
            "tool": "browse_ontology",
            "action": "get_industry",
            "result": {
                "id": str(industry.id),
                "name": industry.name,
                "slug": industry.slug,
                "description": industry.description,
            },
        }

    elif action == "search_catalog" and search_term:
        # Search signal contracts as catalog proxy
        result = await db.execute(
            select(
                SignalContract.id,
                SignalContract.name,
                SignalContract.description,
                SignalContract.signal_type,
            )
            .where(
                text(
                    "to_tsvector('english', COALESCE(name, '') || ' ' || COALESCE(description, '')) "
                    "@@ plainto_tsquery('english', :term)"
                )
            )
            .limit(10),
            {"term": search_term},
        )
        rows = result.all()
        return {
            "tool": "browse_ontology",
            "action": "search_catalog",
            "search_term": search_term,
            "results": [
                {
                    "id": str(r.id),
                    "name": r.name,
                    "description": (r.description or "")[:200],
                    "signal_type": r.signal_type,
                }
                for r in rows
            ],
        }

    return {
        "tool": "browse_ontology",
        "error": f"Invalid action '{action}' or missing required parameters.",
    }


async def execute_create_contract(
    db: AsyncSession,
    org_id: UUID,
    user_id: UUID,
    *,
    name: str,
    entity_type: str,
    signal_type: str,
    description: str | None = None,
    industry: str | None = None,
) -> dict[str, Any]:
    """Create a new signal contract."""
    contract = SignalContract(
        org_id=org_id,
        name=name,
        description=description or f"Signal contract for tracking {name}",
        entity_type=entity_type,
        signal_type=signal_type,
        industry=industry,
        source_type="manual",
        is_active=True,
        confidence_threshold=0.85,
    )
    db.add(contract)
    await db.flush()
    await db.refresh(contract)

    logger.info(f"Chat agent created contract {contract.id}: {name}")

    return {
        "tool": "create_contract",
        "result": {
            "id": str(contract.id),
            "name": contract.name,
            "description": contract.description,
            "entity_type": contract.entity_type,
            "signal_type": contract.signal_type,
            "industry": contract.industry,
            "status": "created",
        },
    }


# ── Tool Registry ────────────────────────────────────────────────────
# Maps tool name → executor function

TOOL_EXECUTORS: dict[str, Any] = {
    "search_signals": execute_search_signals,
    "deep_search": execute_deep_search,
    "synthesize_signal": execute_synthesize_signal,
    "get_analytics": execute_get_analytics,
    "get_recommendations": execute_get_recommendations,
    "browse_ontology": execute_browse_ontology,
    "create_contract": execute_create_contract,
}


async def execute_tool(
    tool_name: str,
    tool_args: dict[str, Any],
    db: AsyncSession,
    org_id: UUID,
    user_id: UUID,
) -> dict[str, Any]:
    """Execute a tool by name with given arguments.

    Args:
        tool_name: Name of the tool to execute.
        tool_args: Arguments parsed from the LLM function call.
        db: Database session.
        org_id: Tenant scope.
        user_id: Requesting user.

    Returns:
        Tool result dict.
    """
    executor = TOOL_EXECUTORS.get(tool_name)
    if not executor:
        logger.warning(f"Unknown tool requested: {tool_name}")
        return {"error": f"Unknown tool: {tool_name}"}

    try:
        result = await executor(db, org_id, user_id, **tool_args)
        return result
    except Exception as e:
        logger.error(f"Tool execution failed: {tool_name} — {e}", exc_info=True)
        return {
            "tool": tool_name,
            "error": f"Tool execution failed: {str(e)}",
        }
