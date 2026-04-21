#!/usr/bin/env python
"""Validate Cogent's live intelligence pipeline against a deployed backend.

This script is intentionally operational rather than exhaustive. It verifies:

1. The backend is reachable and healthy.
2. Authenticated pipeline/admin endpoints are available.
3. Workers, queues, and provider readiness look healthy enough for ingestion.
4. Contracts, signals, and briefs are visible through the public API surface.
5. An optional contract-level fetch can be triggered and observed.

Usage examples:

    python scripts/validate_intelligence_pipeline.py --base-url https://api-staging.cogent.ai --token <bearer-token>

    $env:COGENT_BASE_URL="https://api-staging.cogent.ai"
    $env:COGENT_BEARER_TOKEN="<bearer-token>"
    python scripts/validate_intelligence_pipeline.py --trigger-fetch

    python scripts/validate_intelligence_pipeline.py --contract-id 00000000-0000-0000-0000-000000000000 --trigger-fetch --require-signal-growth
"""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any


def _normalize_base_url(value: str) -> str:
    value = (value or "").strip().rstrip("/")
    if not value:
        raise ValueError("A backend base URL is required.")
    return value


def _normalize_bearer(token: str | None) -> str | None:
    token = (token or "").strip()
    if not token:
        return None
    return token if token.lower().startswith("bearer ") else f"Bearer {token}"


class ApiClient:
    def __init__(self, base_url: str, token: str | None, timeout: int) -> None:
        self.base_url = _normalize_base_url(base_url)
        self.token = _normalize_bearer(token)
        self.timeout = timeout

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
        auth: bool = True,
    ) -> tuple[int, Any]:
        url = f"{self.base_url}{path}"
        if params:
            query = urllib.parse.urlencode(
                {key: value for key, value in params.items() if value is not None}
            )
            if query:
                url = f"{url}?{query}"

        data = None
        headers = {"Accept": "application/json"}
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if auth and self.token:
            headers["Authorization"] = self.token

        request = urllib.request.Request(
            url,
            data=data,
            method=method.upper(),
            headers=headers,
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = response.read().decode("utf-8")
                return response.getcode(), self._decode_json(payload)
        except urllib.error.HTTPError as exc:
            payload = exc.read().decode("utf-8", errors="replace")
            return exc.code, self._decode_json(payload)
        except urllib.error.URLError as exc:
            raise RuntimeError(f"{method.upper()} {url} failed: {exc}") from exc

    @staticmethod
    def _decode_json(payload: str) -> Any:
        payload = payload.strip()
        if not payload:
            return None
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            return payload


@dataclass
class CheckResult:
    level: str
    title: str
    detail: str


@dataclass
class Reporter:
    results: list[CheckResult] = field(default_factory=list)

    def pass_(self, title: str, detail: str) -> None:
        self.results.append(CheckResult("PASS", title, detail))

    def warn(self, title: str, detail: str) -> None:
        self.results.append(CheckResult("WARN", title, detail))

    def fail(self, title: str, detail: str) -> None:
        self.results.append(CheckResult("FAIL", title, detail))

    @property
    def failures(self) -> list[CheckResult]:
        return [item for item in self.results if item.level == "FAIL"]

    def print(self) -> None:
        for item in self.results:
            print(f"[{item.level}] {item.title}: {item.detail}")

        passes = sum(1 for item in self.results if item.level == "PASS")
        warns = sum(1 for item in self.results if item.level == "WARN")
        fails = sum(1 for item in self.results if item.level == "FAIL")
        print("")
        print(
            f"Summary: {passes} passed, {warns} warnings, {fails} failed "
            f"across {len(self.results)} checks."
        )


def _extract_total(payload: Any) -> int | None:
    if isinstance(payload, dict) and isinstance(payload.get("total"), int):
        return payload["total"]
    return None


def _choose_contract(
    contracts_payload: Any, contract_id: str | None
) -> dict[str, Any] | None:
    if not isinstance(contracts_payload, dict):
        return None
    items = contracts_payload.get("items")
    if not isinstance(items, list):
        return None
    if contract_id:
        for item in items:
            if isinstance(item, dict) and str(item.get("id")) == contract_id:
                return item
        return None
    for item in items:
        if isinstance(item, dict) and item.get("is_active"):
            return item
    return items[0] if items else None


def run_validation(args: argparse.Namespace) -> int:
    client = ApiClient(args.base_url, args.token, args.timeout)
    report = Reporter()

    health_code, health_payload = client.request("GET", "/health", auth=False)
    if health_code == 200:
        status = (
            health_payload.get("status")
            if isinstance(health_payload, dict)
            else None
        )
        if status == "healthy":
            report.pass_("Backend health", "The health endpoint returned status=healthy.")
        else:
            report.warn(
                "Backend health",
                f"The health endpoint returned HTTP 200 but status={status!r}.",
            )
    else:
        report.fail("Backend health", f"Expected HTTP 200 from /health, received {health_code}.")
        report.print()
        return 1

    if not client.token:
        report.fail(
            "Authentication",
            "No bearer token was supplied. Set --token or COGENT_BEARER_TOKEN to validate protected endpoints.",
        )
        report.print()
        return 1

    pipeline_code, pipeline_payload = client.request("GET", "/api/v1/pipeline/status")
    if pipeline_code != 200 or not isinstance(pipeline_payload, dict):
        report.fail(
            "Pipeline status",
            f"Expected HTTP 200 from /api/v1/pipeline/status, received {pipeline_code}.",
        )
        report.print()
        return 1

    scheduler_running = bool(pipeline_payload.get("scheduler_running"))
    if scheduler_running:
        report.pass_("Scheduler", "The signal scheduler reports itself as running.")
    else:
        report.fail("Scheduler", "The signal scheduler is not running.")

    workers_online = int(pipeline_payload.get("workers_online") or 0)
    if workers_online > 0:
        report.pass_("Workers", f"{workers_online} worker(s) reported online.")
    else:
        report.fail(
            "Workers",
            "No RQ workers reported online. Acquisition jobs will remain queued.",
        )

    provider_readiness = pipeline_payload.get("provider_readiness") or {}
    missing_providers = sorted(
        key for key, ready in provider_readiness.items() if not ready
    )
    if missing_providers:
        report.warn(
            "Provider readiness",
            "Some managed providers are not configured: "
            + ", ".join(missing_providers)
            + ". Generic RSS/API/scraper sources can still work.",
        )
    else:
        report.pass_(
            "Provider readiness",
            "All tracked provider credentials appear configured.",
        )

    queues = pipeline_payload.get("queues") or {}
    queue_descriptions: list[str] = []
    backlog_warnings: list[str] = []
    if isinstance(queues, dict):
        for queue_name, stats in queues.items():
            if not isinstance(stats, dict):
                continue
            queued = int(stats.get("queued") or 0)
            failed = int(stats.get("failed") or 0)
            started = int(stats.get("started") or 0)
            scheduled = int(stats.get("scheduled") or 0)
            queue_descriptions.append(
                f"{queue_name}: queued={queued}, started={started}, "
                f"failed={failed}, scheduled={scheduled}"
            )
            if failed > 0:
                backlog_warnings.append(f"{queue_name} has {failed} failed job(s)")
            if queued > args.max_queue_backlog:
                backlog_warnings.append(
                    f"{queue_name} backlog ({queued}) exceeds max backlog threshold ({args.max_queue_backlog})"
                )
    if queue_descriptions:
        if backlog_warnings:
            report.warn("Queue health", "; ".join(backlog_warnings))
        else:
            report.pass_("Queue health", " | ".join(queue_descriptions))
    else:
        report.warn(
            "Queue health",
            "No queue statistics were returned by /api/v1/pipeline/status.",
        )

    source_health_code, source_health_payload = client.request("GET", "/api/v1/pipeline/source-health")
    if source_health_code == 200 and isinstance(source_health_payload, dict):
        critical = int(source_health_payload.get("critical_contracts") or 0)
        degraded = int(source_health_payload.get("degraded_contracts") or 0)
        stale = int(source_health_payload.get("stale_contracts") or 0)
        if critical > 0:
            report.fail(
                "Source health",
                f"{critical} contract(s) are critical, {degraded} degraded, {stale} stale.",
            )
        elif degraded > 0 or stale > 0:
            report.warn(
                "Source health",
                f"{degraded} degraded and {stale} stale contract(s) need attention.",
            )
        else:
            report.pass_(
                "Source health",
                "No active contracts are currently critical, stale, or degraded.",
            )
    elif source_health_code == 403:
        report.warn(
            "Source health",
            "The token can access pipeline status but not source health details. "
            "Use an admin token for full operational validation.",
        )
    else:
        report.warn(
            "Source health",
            f"Could not read /api/v1/pipeline/source-health (HTTP {source_health_code}).",
        )

    contracts_code, contracts_payload = client.request(
        "GET",
        "/api/v1/contracts",
        params={"limit": args.contract_limit, "active_only": "true"},
    )
    if contracts_code != 200:
        report.fail(
            "Contracts",
            f"Expected HTTP 200 from /api/v1/contracts, received {contracts_code}.",
        )
        report.print()
        return 1

    contract_total = _extract_total(contracts_payload)
    if contract_total is None:
        report.warn("Contracts", "The contract list response did not include a total count.")
    elif contract_total == 0:
        report.warn(
            "Contracts",
            "No active contracts were found. The UI will remain empty until monitoring coverage is created.",
        )
    else:
        report.pass_("Contracts", f"Found {contract_total} active contract(s).")

    signals_code, signals_payload = client.request(
        "GET",
        "/api/v1/signals/feed",
        params={"limit": args.signal_limit},
    )
    if signals_code != 200:
        report.fail(
            "Signals feed",
            f"Expected HTTP 200 from /api/v1/signals/feed, received {signals_code}.",
        )
        report.print()
        return 1

    signal_total = _extract_total(signals_payload)
    if signal_total is None:
        report.warn("Signals feed", "The signals feed response did not include a total count.")
    elif signal_total == 0:
        report.warn(
            "Signals feed",
            "No signals are available yet. This is acceptable only for a fresh workspace or before ingestion has run.",
        )
    else:
        report.pass_("Signals feed", f"Found {signal_total} live signal(s) in the feed.")

    briefs_code, briefs_payload = client.request(
        "GET",
        "/api/v1/briefs",
        params={"limit": args.brief_limit},
    )
    if briefs_code != 200:
        report.fail(
            "Briefs",
            f"Expected HTTP 200 from /api/v1/briefs, received {briefs_code}.",
        )
        report.print()
        return 1

    brief_total = _extract_total(briefs_payload)
    if brief_total is None:
        report.warn("Briefs", "The briefs response did not include a total count.")
    elif brief_total == 0:
        report.warn(
            "Briefs",
            "No published briefs are available yet. That is common before live signals have been synthesized.",
        )
    else:
        report.pass_("Briefs", f"Found {brief_total} brief(s) in the library.")

    selected_contract = _choose_contract(contracts_payload, args.contract_id)
    if args.contract_id and not selected_contract:
        report.fail(
            "Fetch target",
            f"Contract {args.contract_id} was not found in the active contract list visible to this token.",
        )
    elif args.trigger_fetch and not selected_contract:
        report.warn(
            "Fetch target",
            "No active contract was available for manual fetch validation, so the fetch test was skipped.",
        )
    elif selected_contract:
        report.pass_(
            "Fetch target",
            f"Selected contract '{selected_contract.get('name')}' ({selected_contract.get('id')}).",
        )

    if args.trigger_fetch and selected_contract:
        contract_id = str(selected_contract.get("id"))
        initial_contract_signals_code, initial_contract_signals_payload = client.request(
            "GET",
            f"/api/v1/signals/contract/{contract_id}",
            params={"limit": args.signal_limit},
        )
        initial_total = (
            _extract_total(initial_contract_signals_payload)
            if initial_contract_signals_code == 200
            else None
        )

        fetch_code, fetch_payload = client.request("POST", f"/api/v1/contracts/{contract_id}/fetch")
        if fetch_code != 200:
            detail = (
                fetch_payload.get("detail")
                if isinstance(fetch_payload, dict)
                else fetch_payload
            )
            report.fail(
                "Manual fetch",
                f"Could not queue a fetch for contract {contract_id}. HTTP {fetch_code}: {detail}",
            )
        else:
            job_id = fetch_payload.get("job_id") if isinstance(fetch_payload, dict) else None
            report.pass_(
                "Manual fetch",
                f"Fetch job queued successfully{f' (job {job_id})' if job_id else ''}.",
            )

            deadline = time.time() + args.poll_timeout
            latest_total = initial_total
            while time.time() < deadline:
                time.sleep(args.poll_interval)
                contract_signals_code, contract_signals_payload = client.request(
                    "GET",
                    f"/api/v1/signals/contract/{contract_id}",
                    params={"limit": args.signal_limit},
                )
                if contract_signals_code == 200:
                    latest_total = _extract_total(contract_signals_payload)
                    if (
                        initial_total is not None
                        and latest_total is not None
                        and latest_total > initial_total
                    ):
                        break

            if initial_total is None or latest_total is None:
                report.warn(
                    "Manual fetch result",
                    "The contract-level signal endpoint did not return comparable totals, "
                    "so growth could not be measured.",
                )
            elif latest_total > initial_total:
                report.pass_(
                    "Manual fetch result",
                    f"Signal count for the contract increased from {initial_total} to {latest_total}.",
                )
            elif args.require_signal_growth:
                report.fail(
                    "Manual fetch result",
                    f"Signal count did not increase within {args.poll_timeout}s (stayed at {latest_total}).",
                )
            else:
                report.warn(
                    "Manual fetch result",
                    f"Signal count did not increase within {args.poll_timeout}s "
                    f"(stayed at {latest_total}). This may still be acceptable "
                    "if the fetch produced duplicates or the provider returned "
                    "no fresh items.",
                )

    report.print()
    return 1 if report.failures else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate Cogent's live intelligence pipeline against a deployed backend.",
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("COGENT_BASE_URL", ""),
        help="Backend base URL, for example https://api-staging.cogent.ai",
    )
    parser.add_argument(
        "--token",
        default=os.getenv("COGENT_BEARER_TOKEN", ""),
        help=(
            "Bearer token for authenticated endpoints. A plain JWT is accepted "
            "and will be prefixed automatically."
        ),
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="HTTP timeout in seconds for each request.",
    )
    parser.add_argument(
        "--contract-limit",
        type=int,
        default=10,
        help="Number of contracts to inspect from the active contract list.",
    )
    parser.add_argument(
        "--signal-limit",
        type=int,
        default=10,
        help="Number of signals to request from feed/contract endpoints.",
    )
    parser.add_argument(
        "--brief-limit",
        type=int,
        default=10,
        help="Number of briefs to request from the library endpoint.",
    )
    parser.add_argument(
        "--max-queue-backlog",
        type=int,
        default=50,
        help="Warn when any queue backlog exceeds this threshold.",
    )
    parser.add_argument(
        "--contract-id",
        default=None,
        help="Optional contract ID to use for the manual fetch validation step.",
    )
    parser.add_argument(
        "--trigger-fetch",
        action="store_true",
        help="Trigger a manual fetch on one active contract and observe signal growth.",
    )
    parser.add_argument(
        "--poll-timeout",
        type=int,
        default=120,
        help="Maximum number of seconds to wait for contract-level signal growth after a fetch is triggered.",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=10,
        help="Seconds between follow-up contract signal checks after a manual fetch is queued.",
    )
    parser.add_argument(
        "--require-signal-growth",
        action="store_true",
        help=(
            "Fail instead of warn if the contract signal count does not increase "
            "during the polling window."
        ),
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if not args.base_url:
        parser.error("--base-url is required (or set COGENT_BASE_URL).")
    return run_validation(args)


if __name__ == "__main__":
    raise SystemExit(main())
