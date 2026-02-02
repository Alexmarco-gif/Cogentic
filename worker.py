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
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from rq import Worker, SimpleWorker
from rq.logutils import setup_loghandlers

from backend.queue import high_priority_queue, default_queue, low_priority_queue
from backend.redis_client import get_redis_client

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description='RQ Worker for Cogent background jobs')
    parser.add_argument(
        '--queue',
        choices=['high', 'default', 'low', 'all'],
        default='all',
        help='Queue to process (default: all)'
    )
    parser.add_argument(
        '--burst',
        action='store_true',
        help='Run in burst mode (quit after all jobs processed)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Select queues to process
    if args.queue == 'high':
        queues = [high_priority_queue]
    elif args.queue == 'default':
        queues = [default_queue]
    elif args.queue == 'low':
        queues = [low_priority_queue]
    else:  # all
        queues = [high_priority_queue, default_queue, low_priority_queue]
    
    queue_names = [q.name for q in queues]
    logger.info(f"Starting RQ worker for queues: {', '.join(queue_names)}")
    
    # Create and start worker
    redis_conn = get_redis_client()
    
    # Use SimpleWorker on Windows (no fork support)
    # Use regular Worker on Unix-like systems
    import platform
    if platform.system() == 'Windows':
        logger.info("Using SimpleWorker (Windows - no fork support)")
        worker_class = SimpleWorker
    else:
        worker_class = Worker
    
    worker = worker_class(
        queues,
        connection=redis_conn,
        name=f'cogent-worker-{args.queue}'
    )
    
    # Setup RQ logging
    setup_loghandlers('INFO')
    
    # Start processing jobs
    worker.work(burst=args.burst)


if __name__ == '__main__':
    main()
