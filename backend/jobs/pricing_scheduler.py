"""Job scheduler configuration for pricing lifecycle background tasks."""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from backend.jobs.trial_expiry_job import run_trial_expiry_job

logger = logging.getLogger(__name__)

# Create scheduler instance
scheduler = AsyncIOScheduler()


def start_pricing_jobs():
    """
    Start pricing lifecycle scheduled jobs.

    Jobs:
    - Trial expiry check: Daily at 2 AM UTC
    """
    if scheduler.running:
        logger.info("pricing_scheduler_already_running")
        return

    logger.info("Starting pricing system scheduled jobs...")

    # Trial expiry check - runs daily at 2 AM UTC
    scheduler.add_job(
        run_trial_expiry_job,
        CronTrigger(hour=2, minute=0),
        id="trial_expiry_job",
        name="Check Trial Expirations",
        replace_existing=True,
    )
    logger.info("Scheduled: Trial expiry job (daily at 2 AM UTC)")

    # Start the scheduler
    scheduler.start()
    logger.info("Pricing system scheduled jobs started successfully")


def stop_pricing_jobs():
    """Stop all scheduled jobs"""
    logger.info("Stopping pricing system scheduled jobs...")
    if not scheduler.running:
        logger.info("pricing_scheduler_not_running")
        return
    scheduler.shutdown(wait=True)
    logger.info("Scheduler stopped")


if __name__ == "__main__":
    # For testing - run scheduler in standalone mode
    import asyncio

    start_pricing_jobs()

    try:
        # Keep running
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        stop_pricing_jobs()
