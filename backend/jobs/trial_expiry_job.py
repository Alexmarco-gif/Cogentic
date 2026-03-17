"""Trial expiry background job"""

import asyncio
import logging
from datetime import datetime, timezone

from backend.database import async_session_maker
from backend.services.trial_service import TrialService

logger = logging.getLogger(__name__)


async def check_trial_expiries():
    """
    Scheduled job: Check and process trial expirations.

    Should run daily at 2 AM UTC via scheduler.
    """
    logger.info("Starting trial expiry check job...")

    async with async_session_maker() as db:
        trial_service = TrialService(db)

        try:
            count = await trial_service.check_all_expired_trials()
            logger.info(
                f"Trial expiry check complete. Processed {count} trial accounts."
            )
            return count
        except Exception as e:
            logger.error(f"Error processing trial expiries: {e}", exc_info=True)
            raise


def run_trial_expiry_job():
    """Synchronous wrapper for scheduler"""
    return asyncio.run(check_trial_expiries())


if __name__ == "__main__":
    # Allow manual execution for testing
    print(f"Running trial expiry job at {datetime.now(timezone.utc)}")
    result = run_trial_expiry_job()
    print(f"Processed {result} trials")
