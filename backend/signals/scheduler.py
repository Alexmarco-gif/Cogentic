"""Signal acquisition scheduler.

Uses APScheduler to manage cron-based signal fetching
across all active signal contracts. Routes contracts to
RQ background jobs based on their schedule_tier.
"""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from backend.job_queue import enqueue_job

logger = logging.getLogger(__name__)

# Schedule tier → interval mapping
_TIER_INTERVALS: dict[str, int] = {
    "realtime": 15,  # Every 15 minutes
    "standard": 60,  # Every 1 hour
    "slow": 360,  # Every 6 hours
    "daily": 1440,  # Every 24 hours
}


class SignalScheduler:
    """Manages scheduled signal acquisition across all active contracts.

    Uses APScheduler for timing and dispatches fetch jobs to RQ
    workers. Schedules are organized by tier:
    - realtime (15min): Breaking news, social mentions, market data
    - standard (1hr): Press releases, job postings, app store
    - slow (6hr): Regulatory filings, patents, SEC
    - daily: Industry reports, government gazettes
    """

    def __init__(self):
        self.scheduler = AsyncIOScheduler(
            job_defaults={
                "coalesce": True,  # Collapse missed runs
                "max_instances": 1,  # No parallel runs of same job
                "misfire_grace_time": 300,  # 5min grace for misfires
            }
        )
        self._started = False

    def start(self):
        """Start the scheduler with tier-based interval jobs."""
        if self._started:
            logger.warning("Scheduler already started")
            return

        # One job per schedule tier that batches all contracts in that tier
        for tier, interval_min in _TIER_INTERVALS.items():
            self.scheduler.add_job(
                self._dispatch_tier,
                trigger=IntervalTrigger(minutes=interval_min),
                id=f"signal_fetch_{tier}",
                name=f"Signal fetch: {tier} tier",
                args=[tier],
                replace_existing=True,
            )
            logger.info(f"Scheduled {tier} tier signal fetch every {interval_min}min")

        # Health check — runs every 30min to detect degraded contracts
        self.scheduler.add_job(
            self._health_check,
            trigger=IntervalTrigger(minutes=30),
            id="signal_health_check",
            name="Signal contract health check",
            replace_existing=True,
        )

        # Sprint 3: Refinement catch-up — process unembedded signals every hour
        self.scheduler.add_job(
            self._refinement_catchup,
            trigger=IntervalTrigger(minutes=60),
            id="refinement_catchup",
            name="Refinement catch-up (unprocessed signals)",
            replace_existing=True,
        )

        # Sprint 3: Weekly model training — retrain all 3 ML models
        from apscheduler.triggers.cron import CronTrigger

        self.scheduler.add_job(
            self._weekly_training,
            trigger=CronTrigger(day_of_week="sun", hour=2, minute=0),
            id="weekly_model_training",
            name="Weekly ML model retraining",
            replace_existing=True,
        )
        logger.info("Scheduled weekly model training (Sun 02:00 UTC)")

        # Sprint 4: Brief auto-refresh — check stale briefs every 2 hours
        self.scheduler.add_job(
            self._brief_refresh,
            trigger=IntervalTrigger(minutes=120),
            id="brief_auto_refresh",
            name="Brief auto-refresh check",
            replace_existing=True,
        )
        logger.info("Scheduled brief auto-refresh every 2 hours")

        # Sprint 4: Recommendation batch — regenerate after refinement, every 4 hours
        self.scheduler.add_job(
            self._recommendation_batch,
            trigger=IntervalTrigger(minutes=240),
            id="recommendation_batch",
            name="Recommendation batch generation",
            replace_existing=True,
        )
        logger.info("Scheduled recommendation batch every 4 hours")

        # Dynamic Intelligence: Source auto-activation — every 6 hours
        self.scheduler.add_job(
            self._source_auto_activate,
            trigger=IntervalTrigger(minutes=360),
            id="source_auto_activate",
            name="Auto-activate recommended sources",
            replace_existing=True,
        )
        logger.info("Scheduled source auto-activation every 6 hours")

        self.scheduler.start()
        self._started = True
        logger.info("Signal scheduler started")

    def stop(self):
        """Gracefully stop the scheduler."""
        if self._started:
            self.scheduler.shutdown(wait=True)
            self._started = False
            logger.info("Signal scheduler stopped")

    @property
    def is_running(self) -> bool:
        return self._started and self.scheduler.running

    @staticmethod
    def _dispatch_tier(tier: str):
        """Enqueue an RQ job to fetch all contracts in a given tier.

        This runs inside APScheduler and dispatches the heavy work
        to RQ workers so it doesn't block the scheduler loop.
        """
        from backend.jobs.acquisition_job import fetch_signals_by_tier

        queue_name = "high" if tier == "realtime" else "default"
        timeout = "15m" if tier == "daily" else "10m"

        enqueue_job(
            fetch_signals_by_tier,
            tier,
            queue_name=queue_name,
            job_timeout=timeout,
        )
        logger.info(f"Dispatched {tier} tier fetch job to {queue_name} queue")

    @staticmethod
    def _health_check():
        """Enqueue a health check job for degraded contracts."""
        from backend.jobs.acquisition_job import check_contract_health

        enqueue_job(
            check_contract_health,
            queue_name="low",
            job_timeout="5m",
        )

    @staticmethod
    def _refinement_catchup():
        """Enqueue a refinement catch-up job for unprocessed signals."""
        from backend.jobs.refinement_job import refine_unprocessed

        enqueue_job(
            refine_unprocessed,
            100,  # limit
            queue_name="default",
            job_timeout="30m",
        )
        logger.info("Dispatched refinement catch-up job")

    @staticmethod
    def _weekly_training():
        """Enqueue weekly ML model retraining job."""
        from backend.jobs.refinement_job import train_all_models

        enqueue_job(
            train_all_models,
            queue_name="low",
            job_timeout="1h",
        )
        logger.info("Dispatched weekly model training job")

    @staticmethod
    def _brief_refresh():
        """Enqueue brief auto-refresh check job."""
        from backend.jobs.sprint4_jobs import refresh_all_briefs

        enqueue_job(
            refresh_all_briefs,
            queue_name="low",
            job_timeout="15m",
        )
        logger.info("Dispatched brief refresh check job")

    @staticmethod
    def _recommendation_batch():
        """Enqueue recommendation batch generation job."""
        from backend.jobs.sprint4_jobs import generate_recommendations

        enqueue_job(
            generate_recommendations,
            100,  # limit
            queue_name="low",
            job_timeout="30m",
        )
        logger.info("Dispatched recommendation batch job")

    @staticmethod
    def _source_auto_activate():
        """Enqueue source auto-activation job."""
        from backend.jobs.source_discovery_job import auto_activate_sources

        enqueue_job(
            auto_activate_sources,
            queue_name="low",
            job_timeout="10m",
        )
        logger.info("Dispatched source auto-activation job")


# Module-level singleton
_scheduler: SignalScheduler | None = None


def get_scheduler() -> SignalScheduler:
    """Get or create the signal scheduler singleton."""
    global _scheduler
    if _scheduler is None:
        _scheduler = SignalScheduler()
    return _scheduler
