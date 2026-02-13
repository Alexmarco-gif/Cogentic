"""Job Retry Strategy & Dead Letter Queue.

Implements robust retry logic with exponential backoff and DLQ for failed jobs.
"""

import logging
from datetime import datetime
from typing import Any, Callable

from rq import Retry
from rq.job import Job

from backend.redis_client import get_redis_client

logger = logging.getLogger(__name__)
redis_client = get_redis_client()

# Retry configuration
MAX_RETRIES = 3
RETRY_INTERVALS = [60, 300, 900]  # 1min, 5min, 15min (exponential backoff)


class DeadLetterQueue:
    """Dead letter queue for permanently failed jobs."""

    @staticmethod
    def add(
        job_id: str,
        func_name: str,
        args: tuple,
        kwargs: dict,
        error: str,
    ):
        """Add failed job to DLQ."""
        dlq_key = f"dlq:{job_id}"
        data = {
            "job_id": job_id,
            "function": func_name,
            "args": str(args),
            "kwargs": str(kwargs),
            "error": error,
            "failed_at": datetime.utcnow().isoformat(),
        }

        # Store in Redis set with 7-day TTL
        redis_client.hset(dlq_key, mapping=data)
        redis_client.expire(dlq_key, 604800)  # 7 days
        redis_client.sadd("dlq:jobs", job_id)
        redis_client.expire("dlq:jobs", 604800)

        logger.error(f"Job {job_id} moved to DLQ: {error}")

    @staticmethod
    def get_all() -> list[dict[str, Any]]:
        """Get all jobs in DLQ."""
        job_ids = redis_client.smembers("dlq:jobs")
        jobs = []

        for jid in job_ids:
            if isinstance(jid, bytes):
                jid = jid.decode()
            data = redis_client.hgetall(f"dlq:{jid}")
            if data:
                jobs.append(
                    {
                        k.decode() if isinstance(k, bytes) else k: (
                            v.decode() if isinstance(v, bytes) else v
                        )
                        for k, v in data.items()
                    }
                )

        return jobs

    @staticmethod
    def retry_job(job_id: str) -> Job | None:
        """Retry a DLQ job."""
        data = redis_client.hgetall(f"dlq:{job_id}")
        if not data:
            return None

        # Remove from DLQ
        redis_client.delete(f"dlq:{job_id}")
        redis_client.srem("dlq:jobs", job_id)

        logger.info(f"Retrying DLQ job: {job_id}")
        return None  # Caller should re-enqueue with fresh function reference


def enqueue_with_retry(
    func: Callable,
    *args,
    queue_name: str = "default",
    job_timeout: str = "10m",
    **kwargs,
) -> Job:
    """Enqueue job with retry strategy.

    Args:
        func: Function to execute
        *args: Positional arguments
        queue_name: Queue name
        job_timeout: Timeout string
        **kwargs: Keyword arguments

    Returns:
        RQ Job instance
    """
    from backend.queue import default_queue, high_priority_queue, low_priority_queue

    queue_map = {
        "high": high_priority_queue,
        "default": default_queue,
        "low": low_priority_queue,
    }
    queue = queue_map.get(queue_name, default_queue)

    # Enqueue with retry configuration
    job = queue.enqueue(
        func,
        *args,
        job_timeout=job_timeout,
        retry=Retry(max=MAX_RETRIES, interval=RETRY_INTERVALS),
        on_failure=_on_job_failure,
        **kwargs,
    )

    logger.info(f"Enqueued job {job.id} with {MAX_RETRIES} retries")
    return job


def _on_job_failure(job: Job, connection, exc_type, exc_value, traceback):
    """Callback for job failure - move to DLQ if max retries exceeded."""
    if job.retries_left == 0:
        DeadLetterQueue.add(
            job_id=job.id,
            func_name=job.func_name,
            args=job.args,
            kwargs=job.kwargs,
            error=str(exc_value),
        )
