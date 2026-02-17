"""Beta lifecycle background job"""

import asyncio
import logging
from datetime import datetime, timezone

from backend.database import async_session_maker
from backend.services.beta_lifecycle_service import BetaLifecycleService

logger = logging.getLogger(__name__)


async def process_beta_lifecycle():
    """
    Scheduled job: Process beta notifications and expirations.
    
    Should run daily at 3 AM UTC via scheduler.
    Sends notifications for accounts expiring in 14/7 days and transitions expired accounts.
    """
    logger.info("Starting beta lifecycle processing job...")
    
    async with async_session_maker() as db:
        beta_service = BetaLifecycleService(db)
        
        try:
            # Send notifications
            notifications = await beta_service.process_beta_notifications()
            logger.info(
                f"Sent {notifications['14d']} 14-day warnings and "
                f"{notifications['7d']} 7-day warnings"
            )
            
            # Process expirations
            transitioned = await beta_service.process_beta_expirations()
            logger.info(f"Transitioned {transitioned} beta accounts to standard pricing")
            
            return {
                "notifications": notifications,
                "transitioned": transitioned
            }
        except Exception as e:
            logger.error(f"Error processing beta lifecycle: {e}", exc_info=True)
            raise


def run_beta_lifecycle_job():
    """Synchronous wrapper for scheduler"""
    return asyncio.run(process_beta_lifecycle())


if __name__ == "__main__":
    # Allow manual execution for testing
    print(f"Running beta lifecycle job at {datetime.now(timezone.utc)}")
    result = run_beta_lifecycle_job()
    print(f"Results: {result}")
