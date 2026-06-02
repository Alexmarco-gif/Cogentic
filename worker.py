"""
RQ Worker for processing background jobs.

Usage:
    # Start worker for all queues (high priority first)
    python worker.py

    # Start worker for specific queue
    python worker.py --queue high

    # Start multiple workers
    python worker.py --workers 4
"""

import argparse
import logging
import os
import socket
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from rq import SimpleWorker, Worker
from rq.logutils import setup_loghandlers

from backend.job_queue import (
    get_default_queue,
    get_high_priority_queue,
    get_low_priority_queue,
)
from backend.redis_client import get_redis_client

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ── Liveness probe for container orchestrators ────────────────────────────────

_worker_started_at: float = 0.0
_worker_ref: Worker | SimpleWorker | None = None
_scheduler_mode = False


def _redis_value(value):
    return value.decode("utf-8") if isinstance(value, bytes) else value


class _HealthHandler(BaseHTTPRequestHandler):
    """Minimal HTTP handler for /health liveness probe."""

    def do_GET(self):  # noqa: N802
        if self.path != "/health":
            self.send_error(404)
            return
        uptime = round(time.time() - _worker_started_at, 1) if _worker_started_at else 0
        # Quick Redis connectivity check
        try:
            conn = get_redis_client()
            conn.ping()
            redis_ok = True
        except Exception:
            redis_ok = False

        healthy = redis_ok
        status = 200 if healthy else 503
        import json

        body = json.dumps(
            {
                "status": "healthy" if healthy else "degraded",
                "mode": "scheduler" if _scheduler_mode else "worker",
                "uptime_s": uptime,
                "redis": "up" if redis_ok else "down",
            }
        ).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):  # noqa: A002
        """Suppress default stderr logging for health probes."""
        pass


def _start_health_server(port: int = 8001):
    """Start a tiny HTTP server on a daemon thread for liveness probes."""
    server = HTTPServer(("0.0.0.0", port), _HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info(f"Worker health server listening on :{port}/health")


async def _renew_scheduler_lock(redis_conn, lock_key: str, token: str, ttl: int):
    """Renew a Redis lock while the scheduler process is healthy."""
    import asyncio

    while True:
        await asyncio.sleep(max(1, ttl // 3))
        try:
            if _redis_value(redis_conn.get(lock_key)) != token:
                logger.error("Lost scheduler lock; exiting to avoid duplicate jobs")
                os._exit(2)
            redis_conn.expire(lock_key, ttl)
        except Exception:
            logger.exception("Failed to renew scheduler lock")
            os._exit(2)


def _run_scheduler_mode():
    """Run the singleton scheduler service outside the API process."""
    import asyncio
    import uuid

    from backend.jobs.pricing_scheduler import start_pricing_jobs, stop_pricing_jobs
    from backend.signals.scheduler import get_scheduler

    redis_conn = get_redis_client()
    lock_key = os.environ.get("SCHEDULER_LOCK_KEY", "cogent:scheduler:singleton")
    lock_ttl = int(os.environ.get("SCHEDULER_LOCK_TTL_SECONDS", "90"))
    token = f"{socket.gethostname()}-{os.getpid()}-{uuid.uuid4()}"

    if not redis_conn.set(lock_key, token, nx=True, ex=lock_ttl):
        logger.error("Another scheduler owns %s; exiting", lock_key)
        raise SystemExit(2)

    async def _main():
        renew_task = asyncio.create_task(
            _renew_scheduler_lock(redis_conn, lock_key, token, lock_ttl)
        )
        scheduler = get_scheduler()
        try:
            scheduler.start()
            start_pricing_jobs()
            logger.info("Scheduler service started")
            await asyncio.Event().wait()
        finally:
            renew_task.cancel()
            try:
                scheduler.stop()
            finally:
                stop_pricing_jobs()
                if _redis_value(redis_conn.get(lock_key)) == token:
                    redis_conn.delete(lock_key)

    asyncio.run(_main())


def main():
    parser = argparse.ArgumentParser(description="RQ Worker for Cogent background jobs")
    parser.add_argument(
        "--queue",
        choices=["high", "default", "low", "all"],
        default="all",
        help="Queue to process (default: all)",
    )
    parser.add_argument(
        "--burst",
        action="store_true",
        help="Run in burst mode (quit after all jobs processed)",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument(
        "--scheduler",
        action="store_true",
        help="Run singleton APScheduler dispatchers instead of processing RQ jobs",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    global _worker_started_at, _worker_ref, _scheduler_mode
    _scheduler_mode = args.scheduler
    _worker_started_at = time.time()

    # Start liveness health server
    health_port = int(os.environ.get("WORKER_HEALTH_PORT", "8001"))
    _start_health_server(health_port)

    if args.scheduler:
        _run_scheduler_mode()
        return

    # Select queues to process
    if args.queue == "high":
        queues = [get_high_priority_queue()]
    elif args.queue == "default":
        queues = [get_default_queue()]
    elif args.queue == "low":
        queues = [get_low_priority_queue()]
    else:  # all
        queues = [
            get_high_priority_queue(),
            get_default_queue(),
            get_low_priority_queue(),
        ]

    queue_names = [q.name for q in queues]
    logger.info(f"Starting RQ worker for queues: {', '.join(queue_names)}")

    # Create and start worker
    redis_conn = get_redis_client()

    # Use SimpleWorker on Windows (no fork support)
    # Use regular Worker on Unix-like systems
    import platform

    if platform.system() == "Windows":
        logger.info("Using SimpleWorker (Windows - no fork support)")
        worker_class = SimpleWorker
    else:
        worker_class = Worker

    worker_identity = f"{socket.gethostname()}-{os.getpid()}"
    worker = worker_class(
        queues,
        connection=redis_conn,
        name=f"cogent-worker-{args.queue}-{worker_identity}",
    )

    # Setup RQ logging
    setup_loghandlers("INFO")

    _worker_ref = worker

    # Enqueue periodic jobs at startup (idempotent — RQ deduplicates by job_id)
    if not args.burst:
        try:
            from backend.job_handlers import schedule_feedback_retraining
            schedule_feedback_retraining()
        except Exception as exc:
            logger.warning("Could not schedule feedback retraining at startup: %s", exc)

    # Start processing jobs
    worker.work(burst=args.burst)


if __name__ == "__main__":
    main()
