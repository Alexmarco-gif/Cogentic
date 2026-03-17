"""Background job queue setup using Redis Queue (RQ)."""

import logging
from typing import Any

from rq import Queue
from rq.job import Job

from backend.redis_client import get_redis_client

logger = logging.getLogger(__name__)

# Lazy-initialized Redis connection (avoids crash if Redis is down at import time)
_redis_conn = None


def _get_redis():
    """Lazy initialization of Redis connection for queue."""
    global _redis_conn
    if _redis_conn is None:
        _redis_conn = get_redis_client()
    return _redis_conn


# Lazy-initialized queues
_high_priority_queue = None
_default_queue = None
_low_priority_queue = None


def _get_queue(name: str) -> Queue:
    """Get or create a queue by name with lazy Redis initialization."""
    global _high_priority_queue, _default_queue, _low_priority_queue
    conn = _get_redis()
    if name == "high":
        if _high_priority_queue is None:
            _high_priority_queue = Queue("high", connection=conn, default_timeout="5m")
        return _high_priority_queue
    elif name == "low":
        if _low_priority_queue is None:
            _low_priority_queue = Queue("low", connection=conn, default_timeout="30m")
        return _low_priority_queue
    else:
        if _default_queue is None:
            _default_queue = Queue("default", connection=conn, default_timeout="10m")
        return _default_queue


# Public queue accessors for worker.py and external consumers
def get_high_priority_queue() -> Queue:
    """Get the high priority queue instance."""
    return _get_queue("high")


def get_default_queue() -> Queue:
    """Get the default queue instance."""
    return _get_queue("default")


def get_low_priority_queue() -> Queue:
    """Get the low priority queue instance."""
    return _get_queue("low")


def enqueue_job(
    func: Any, *args, queue_name: str = "default", job_timeout: str = "10m", **kwargs
) -> Job:
    """
    Enqueue a background job.

    Args:
        func: The function to execute
        args: Positional arguments for the function
        queue_name: 'high', 'default', or 'low'
        job_timeout: Maximum execution time (e.g., '5m', '1h')
        kwargs: Keyword arguments for the function

    Returns:
        RQ Job instance
    """
    queue_map = {
        "high": _get_queue("high"),
        "default": _get_queue("default"),
        "low": _get_queue("low"),
    }

    queue = queue_map.get(queue_name, _get_queue("default"))

    job = queue.enqueue(func, *args, job_timeout=job_timeout, **kwargs)

    logger.info(f"Enqueued job {job.id} to {queue_name} queue: {func.__name__}")
    return job


def get_job_status(job_id: str) -> dict[str, Any]:
    """
    Get the status of a background job.

    Args:
        job_id: The RQ job ID

    Returns:
        Dictionary with job status information
    """
    try:
        job = Job.fetch(job_id, connection=_get_redis())

        return {
            "id": job.id,
            "status": job.get_status(),
            "result": job.result if job.is_finished else None,
            "error": str(job.exc_info) if job.is_failed else None,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "ended_at": job.ended_at.isoformat() if job.ended_at else None,
        }
    except Exception as e:
        logger.error(f"Failed to fetch job {job_id}: {e}")
        return {"id": job_id, "status": "not_found", "error": str(e)}


def cancel_job(job_id: str) -> bool:
    """
    Cancel a queued or running job.

    Args:
        job_id: The RQ job ID

    Returns:
        True if cancelled successfully
    """
    try:
        job = Job.fetch(job_id, connection=_get_redis())
        job.cancel()
        logger.info(f"Cancelled job {job_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to cancel job {job_id}: {e}")
        return False


# Queue statistics
def get_queue_stats() -> dict[str, Any]:
    """
    Get statistics for all queues.

    Returns:
        Dictionary with queue statistics
    """
    return {
        "high": {
            "name": "high",
            "count": len(_get_queue("high")),
            "failed": _get_queue("high").failed_job_registry.count,
            "scheduled": _get_queue("high").scheduled_job_registry.count,
        },
        "default": {
            "name": "default",
            "count": len(_get_queue("default")),
            "failed": _get_queue("default").failed_job_registry.count,
            "scheduled": _get_queue("default").scheduled_job_registry.count,
        },
        "low": {
            "name": "low",
            "count": len(_get_queue("low")),
            "failed": _get_queue("low").failed_job_registry.count,
            "scheduled": _get_queue("low").scheduled_job_registry.count,
        },
    }
