"""Background job queue setup using Redis Queue (RQ)"""

import logging
from typing import Any, Dict

from rq import Queue
from rq.job import Job

from backend.redis_client import get_redis_client

logger = logging.getLogger(__name__)

# Initialize Redis connection
redis_conn = get_redis_client()

# Define queues with different priorities
# High priority: User-facing operations (document processing, etc.)
# Default: Regular background tasks
# Low: Maintenance, cleanup, analytics

high_priority_queue = Queue("high", connection=redis_conn, default_timeout="5m")
default_queue = Queue("default", connection=redis_conn, default_timeout="10m")
low_priority_queue = Queue("low", connection=redis_conn, default_timeout="30m")


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
        "high": high_priority_queue,
        "default": default_queue,
        "low": low_priority_queue,
    }

    queue = queue_map.get(queue_name, default_queue)

    job = queue.enqueue(func, *args, job_timeout=job_timeout, **kwargs)

    logger.info(f"Enqueued job {job.id} to {queue_name} queue: {func.__name__}")
    return job


def get_job_status(job_id: str) -> Dict[str, Any]:
    """
    Get the status of a background job.

    Args:
        job_id: The RQ job ID

    Returns:
        Dictionary with job status information
    """
    try:
        job = Job.fetch(job_id, connection=redis_conn)

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
        job = Job.fetch(job_id, connection=redis_conn)
        job.cancel()
        logger.info(f"Cancelled job {job_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to cancel job {job_id}: {e}")
        return False


# Queue statistics
def get_queue_stats() -> Dict[str, Any]:
    """
    Get statistics for all queues.

    Returns:
        Dictionary with queue statistics
    """
    return {
        "high": {
            "name": "high",
            "count": len(high_priority_queue),
            "failed": high_priority_queue.failed_job_registry.count,
            "scheduled": high_priority_queue.scheduled_job_registry.count,
        },
        "default": {
            "name": "default",
            "count": len(default_queue),
            "failed": default_queue.failed_job_registry.count,
            "scheduled": default_queue.scheduled_job_registry.count,
        },
        "low": {
            "name": "low",
            "count": len(low_priority_queue),
            "failed": low_priority_queue.failed_job_registry.count,
            "scheduled": low_priority_queue.scheduled_job_registry.count,
        },
    }
