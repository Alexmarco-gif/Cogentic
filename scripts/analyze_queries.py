"""Database query analysis tool for Cogent.

Runs EXPLAIN ANALYZE on the application's top query patterns,
identifies missing indexes, sequential scans, and N+1 candidates.

Prerequisites:
    pip install asyncpg rich

Usage:
    # Analyse against local database
    python scripts/analyze_queries.py

    # Analyse against a specific database
    DATABASE_URL=postgresql://user:pass@host/db python scripts/analyze_queries.py

    # Show raw EXPLAIN output
    python scripts/analyze_queries.py --verbose

Environment variables:
    DATABASE_URL — PostgreSQL connection string
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from dataclasses import dataclass, field
from typing import Any

try:
    import asyncpg
except ImportError:
    sys.exit("asyncpg is required: pip install asyncpg")

try:
    from rich.console import Console
    from rich.table import Table

    HAS_RICH = True
except ImportError:
    HAS_RICH = False


# ── Query patterns that map to the hottest application code paths ───

QUERY_PATTERNS: list[dict[str, Any]] = [
    {
        "name": "signals_list",
        "description": "Paginated signal listing (GET /api/v1/signals)",
        "sql": """
            EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
            SELECT s.id, s.title, s.signal_type, s.confidence, s.created_at
            FROM signals s
            WHERE s.organisation_id = $1
              AND s.confidence >= 0.5
            ORDER BY s.created_at DESC
            LIMIT 50 OFFSET 0
        """,
        "params": ["00000000-0000-0000-0000-000000000001"],
    },
    {
        "name": "signals_trending",
        "description": "Trending signals (GET /api/v1/signals/trending)",
        "sql": """
            EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
            SELECT s.id, s.title, s.signal_type, s.confidence,
                   s.created_at, s.trend_score
            FROM signals s
            WHERE s.organisation_id = $1
              AND s.created_at > NOW() - INTERVAL '7 days'
              AND s.confidence >= 0.6
            ORDER BY s.trend_score DESC NULLS LAST
            LIMIT 20
        """,
        "params": ["00000000-0000-0000-0000-000000000001"],
    },
    {
        "name": "signals_by_entity",
        "description": "Signals filtered by entity",
        "sql": """
            EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
            SELECT s.id, s.title, s.confidence, s.created_at
            FROM signals s
            JOIN signal_entities se ON se.signal_id = s.id
            WHERE se.entity_name = $1
              AND s.organisation_id = $2
            ORDER BY s.created_at DESC
            LIMIT 50
        """,
        "params": ["NNPC", "00000000-0000-0000-0000-000000000001"],
    },
    {
        "name": "briefs_list",
        "description": "Intelligence briefs listing (GET /api/v1/briefs)",
        "sql": """
            EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
            SELECT b.id, b.title, b.status, b.created_at, b.updated_at
            FROM briefs b
            WHERE b.organisation_id = $1
            ORDER BY b.updated_at DESC
            LIMIT 20
        """,
        "params": ["00000000-0000-0000-0000-000000000001"],
    },
    {
        "name": "situation_room",
        "description": "Situation room dashboard query",
        "sql": """
            EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
            SELECT s.id, s.title, s.signal_type, s.confidence, s.created_at
            FROM signals s
            WHERE s.organisation_id = $1
              AND s.created_at > NOW() - INTERVAL '168 hours'
            ORDER BY s.confidence DESC, s.created_at DESC
            LIMIT 50
        """,
        "params": ["00000000-0000-0000-0000-000000000001"],
    },
    {
        "name": "user_by_auth0",
        "description": "User lookup by Auth0 ID (every authenticated request)",
        "sql": """
            EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
            SELECT u.id, u.auth0_id, u.email, u.role, u.organisation_id
            FROM users u
            WHERE u.auth0_id = $1
            LIMIT 1
        """,
        "params": ["auth0|000000000000000000000001"],
    },
    {
        "name": "signal_full_text_search",
        "description": "Full-text / ILIKE search on signals",
        "sql": """
            EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
            SELECT s.id, s.title, s.content, s.confidence
            FROM signals s
            WHERE s.organisation_id = $1
              AND (s.title ILIKE $2 OR s.content ILIKE $2)
            ORDER BY s.confidence DESC
            LIMIT 20
        """,
        "params": ["00000000-0000-0000-0000-000000000001", "%fintech%"],
    },
    {
        "name": "signal_count_by_type",
        "description": "Signal aggregation for dashboard widgets",
        "sql": """
            EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
            SELECT s.signal_type, COUNT(*) as cnt
            FROM signals s
            WHERE s.organisation_id = $1
              AND s.created_at > NOW() - INTERVAL '30 days'
            GROUP BY s.signal_type
        """,
        "params": ["00000000-0000-0000-0000-000000000001"],
    },
]


# ── Recommended indexes ────────────────────────────────────────────

RECOMMENDED_INDEXES: list[dict[str, str]] = [
    {
        "table": "signals",
        "name": "ix_signals_org_created",
        "ddl": "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_signals_org_created "
        "ON signals (organisation_id, created_at DESC);",
        "reason": "Covers signals_list, situation_room queries",
    },
    {
        "table": "signals",
        "name": "ix_signals_org_confidence",
        "ddl": "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_signals_org_confidence "
        "ON signals (organisation_id, confidence DESC);",
        "reason": "Filter + sort by confidence",
    },
    {
        "table": "signals",
        "name": "ix_signals_org_trend",
        "ddl": "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_signals_org_trend "
        "ON signals (organisation_id, trend_score DESC NULLS LAST) "
        "WHERE created_at > NOW() - INTERVAL '7 days';",
        "reason": "Partial index for trending signals",
    },
    {
        "table": "signal_entities",
        "name": "ix_signal_entities_name",
        "ddl": "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_signal_entities_name "
        "ON signal_entities (entity_name, signal_id);",
        "reason": "Covers signals_by_entity join",
    },
    {
        "table": "users",
        "name": "ix_users_auth0_id",
        "ddl": "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_users_auth0_id "
        "ON users (auth0_id);",
        "reason": "Every authenticated request looks up user by auth0_id",
    },
    {
        "table": "briefs",
        "name": "ix_briefs_org_updated",
        "ddl": "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_briefs_org_updated "
        "ON briefs (organisation_id, updated_at DESC);",
        "reason": "Covers briefs_list pagination",
    },
]


@dataclass
class QueryResult:
    name: str
    description: str
    planning_time_ms: float = 0.0
    execution_time_ms: float = 0.0
    total_cost: float = 0.0
    seq_scans: list[str] = field(default_factory=list)
    index_scans: list[str] = field(default_factory=list)
    rows_returned: int = 0
    shared_hit_blocks: int = 0
    shared_read_blocks: int = 0
    error: str | None = None
    raw_plan: Any = None


def _extract_plan_info(plan: dict, result: QueryResult) -> None:
    """Recursively walk the EXPLAIN JSON plan tree."""
    node_type = plan.get("Node Type", "")

    if "Seq Scan" in node_type:
        relation = plan.get("Relation Name", "unknown")
        result.seq_scans.append(relation)
    elif "Index" in node_type:
        index_name = plan.get("Index Name", plan.get("Relation Name", "unknown"))
        result.index_scans.append(index_name)

    result.rows_returned += plan.get("Actual Rows", 0)
    result.shared_hit_blocks += plan.get("Shared Hit Blocks", 0)
    result.shared_read_blocks += plan.get("Shared Read Blocks", 0)

    for child in plan.get("Plans", []):
        _extract_plan_info(child, result)


async def run_query(conn: asyncpg.Connection, pattern: dict) -> QueryResult:
    """Execute one EXPLAIN ANALYZE query and parse results."""
    result = QueryResult(name=pattern["name"], description=pattern["description"])

    try:
        rows = await conn.fetch(pattern["sql"], *pattern["params"])
        if rows:
            plan_json = rows[0][0]
            if isinstance(plan_json, list):
                plan_json = plan_json[0]

            result.raw_plan = plan_json
            result.planning_time_ms = plan_json.get("Planning Time", 0.0)
            result.execution_time_ms = plan_json.get("Execution Time", 0.0)
            result.total_cost = plan_json.get("Plan", {}).get("Total Cost", 0.0)

            _extract_plan_info(plan_json.get("Plan", {}), result)
    except asyncpg.UndefinedTableError as e:
        result.error = f"Table not found: {e}"
    except asyncpg.UndefinedColumnError as e:
        result.error = f"Column not found: {e}"
    except Exception as e:
        result.error = str(e)

    return result


def print_results(results: list[QueryResult], verbose: bool = False) -> None:
    """Print analysis results."""
    if HAS_RICH:
        _print_rich(results, verbose)
    else:
        _print_plain(results, verbose)


def _print_rich(results: list[QueryResult], verbose: bool) -> None:
    console = Console()

    # Results table
    table = Table(title="Query Analysis Results", show_lines=True)
    table.add_column("Query", style="cyan", width=22)
    table.add_column("Plan (ms)", justify="right", width=10)
    table.add_column("Exec (ms)", justify="right", width=10)
    table.add_column("Seq Scans", style="red", width=18)
    table.add_column("Index Scans", style="green", width=22)
    table.add_column("Cache Hit%", justify="right", width=10)
    table.add_column("Status", width=10)

    for r in results:
        if r.error:
            table.add_row(r.name, "-", "-", "-", "-", "-", "[red]ERR[/red]")
            continue

        total_blocks = r.shared_hit_blocks + r.shared_read_blocks
        cache_pct = (
            f"{r.shared_hit_blocks / total_blocks * 100:.0f}%"
            if total_blocks > 0
            else "N/A"
        )

        seq_str = ", ".join(r.seq_scans) if r.seq_scans else "-"
        idx_str = ", ".join(r.index_scans) if r.index_scans else "-"

        # Flag slow queries
        status = "[green]OK[/green]"
        if r.execution_time_ms > 100:
            status = "[red]SLOW[/red]"
        elif r.execution_time_ms > 50:
            status = "[yellow]WARN[/yellow]"

        table.add_row(
            r.name,
            f"{r.planning_time_ms:.1f}",
            f"{r.execution_time_ms:.1f}",
            seq_str,
            idx_str,
            cache_pct,
            status,
        )

    console.print(table)

    # Errors
    errors = [r for r in results if r.error]
    if errors:
        console.print("\n[bold red]Errors:[/bold red]")
        for r in errors:
            console.print(f"  • {r.name}: {r.error}")

    # Seq scan warnings
    seq_scan_queries = [r for r in results if r.seq_scans and not r.error]
    if seq_scan_queries:
        console.print("\n[bold yellow]⚠ Sequential scans detected:[/bold yellow]")
        for r in seq_scan_queries:
            tables = ", ".join(set(r.seq_scans))
            console.print(f"  • {r.name}: seq scan on [{tables}]")

    # Index recommendations
    console.print("\n[bold cyan]Recommended Indexes:[/bold cyan]")
    idx_table = Table(show_lines=True)
    idx_table.add_column("Table", style="cyan", width=18)
    idx_table.add_column("Index", width=30)
    idx_table.add_column("Reason", width=42)
    for idx in RECOMMENDED_INDEXES:
        idx_table.add_row(idx["table"], idx["name"], idx["reason"])
    console.print(idx_table)

    console.print("\n[bold]DDL to create indexes (run in a migration):[/bold]")
    for idx in RECOMMENDED_INDEXES:
        console.print(f"  {idx['ddl']}")

    if verbose:
        console.print("\n[bold]Raw EXPLAIN output:[/bold]")
        for r in results:
            if r.raw_plan:
                console.print(f"\n--- {r.name} ---")
                import json

                console.print_json(json.dumps(r.raw_plan, indent=2))


def _print_plain(results: list[QueryResult], verbose: bool) -> None:
    print("\n" + "=" * 80)
    print("QUERY ANALYSIS RESULTS")
    print("=" * 80)

    for r in results:
        if r.error:
            print(f"\n{r.name}: ERROR — {r.error}")
            continue

        total_blocks = r.shared_hit_blocks + r.shared_read_blocks
        cache_pct = (
            f"{r.shared_hit_blocks / total_blocks * 100:.0f}%"
            if total_blocks > 0
            else "N/A"
        )

        status = "OK"
        if r.execution_time_ms > 100:
            status = "SLOW"
        elif r.execution_time_ms > 50:
            status = "WARN"

        print(f"\n{r.name} ({r.description})")
        print(f"  Planning:    {r.planning_time_ms:.1f} ms")
        print(f"  Execution:   {r.execution_time_ms:.1f} ms  [{status}]")
        print(f"  Seq scans:   {', '.join(r.seq_scans) or 'none'}")
        print(f"  Index scans: {', '.join(r.index_scans) or 'none'}")
        print(f"  Cache hit:   {cache_pct}")

    print("\n" + "-" * 80)
    print("RECOMMENDED INDEXES")
    print("-" * 80)
    for idx in RECOMMENDED_INDEXES:
        print(f"\n  {idx['name']} ({idx['table']})")
        print(f"    Reason: {idx['reason']}")
        print(f"    DDL:    {idx['ddl']}")


async def main(verbose: bool = False) -> None:
    db_url = os.environ.get(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/cogent"
    )

    # asyncpg expects postgresql:// not postgres://
    if db_url.startswith("postgres://"):
        db_url = "postgresql://" + db_url[len("postgres://") :]

    print("Connecting to database...")
    try:
        conn = await asyncpg.connect(db_url)
    except Exception as e:
        sys.exit(f"Failed to connect: {e}")

    print(f"Running {len(QUERY_PATTERNS)} query analyses...")
    results: list[QueryResult] = []
    for pattern in QUERY_PATTERNS:
        result = await run_query(conn, pattern)
        results.append(result)
        status = "✓" if not result.error else "✗"
        print(f"  {status} {pattern['name']}")

    await conn.close()

    print_results(results, verbose)

    # Exit code: 1 if any SLOW queries
    slow = [r for r in results if not r.error and r.execution_time_ms > 100]
    if slow:
        print(f"\n{len(slow)} slow queries detected (>100ms)")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cogent query analyser")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show raw EXPLAIN")
    args = parser.parse_args()
    asyncio.run(main(verbose=args.verbose))
