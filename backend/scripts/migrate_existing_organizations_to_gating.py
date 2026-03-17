"""
One-time migration script: Migrate existing organizations to the feature gating system.

This script:
1. Assigns default tier (Growth) to existing organizations
2. Allocates Growth-level credits (5,000)
3. Sets billing cycle start date

Usage:
    python -m backend.scripts.migrate_existing_organizations_to_gating
"""

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from backend.database import AsyncSessionLocal
from backend.models.organization import Organization
from backend.models.pricing_enums import PricingTier, TrialStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def migrate_existing_organizations():
    """
    Migrate all existing organizations to the feature gating system.
    Sets them up with Growth tier and standard pricing.
    """
    async with AsyncSessionLocal() as db:
        try:
            # Fetch all existing organizations
            result = await db.execute(select(Organization))
            organizations = result.scalars().all()

            logger.info(f"Found {len(organizations)} organizations to migrate")

            migrated_count = 0
            skipped_count = 0
            error_count = 0

            for org in organizations:
                try:
                    # Skip if already migrated (has pricing_tier set)
                    if org.pricing_tier and org.pricing_tier != PricingTier.EXPLORER:
                        logger.info(
                            f"Skipping organization {org.id} - already migrated"
                        )
                        skipped_count += 1
                        continue

                    # Assign Growth tier to existing organizations
                    org.pricing_tier = PricingTier.GROWTH

                    # Set trial status as converted (existing customers are past trial)
                    org.trial_status = TrialStatus.CONVERTED
                    org.trial_start_date = None  # Historical data not available
                    org.trial_end_date = None

                    # Allocate Growth-level credits
                    org.credits_allocated_monthly = 5000
                    org.credits_consumed = 0
                    org.credits_overage_rate = 0.10  # $0.10 per credit overage

                    # Set billing cycle start (use today for existing customers)
                    org.billing_cycle_start = datetime.now(timezone.utc).date()

                    migrated_count += 1
                    logger.info(
                        f"Migrated organization {org.id} ({org.name if hasattr(org, 'name') else 'N/A'}) "
                        f"- Tier: Growth"
                    )

                except Exception as e:
                    logger.error(f"Error migrating organization {org.id}: {str(e)}")
                    error_count += 1
                    continue

            # Commit all changes
            await db.commit()

            logger.info(
                f"\n{'='*60}\n"
                f"Migration Complete!\n"
                f"{'='*60}\n"
                f"Total organizations: {len(organizations)}\n"
                f"Migrated: {migrated_count}\n"
                f"Skipped (already migrated): {skipped_count}\n"
                f"Errors: {error_count}\n"
                f"{'='*60}"
            )

            return {
                "total": len(organizations),
                "migrated": migrated_count,
                "skipped": skipped_count,
                "errors": error_count,
            }

        except Exception as e:
            logger.error(f"Fatal error during migration: {str(e)}")
            await db.rollback()
            raise


async def verify_migration():
    """
    Verify that the migration completed successfully.
    """
    async with AsyncSessionLocal() as db:
        # Count organizations with Growth tier
        result = await db.execute(
            select(Organization).where(Organization.pricing_tier == PricingTier.GROWTH)
        )
        growth_orgs = result.scalars().all()

        logger.info(
            f"\n{'='*60}\n"
            f"Migration Verification\n"
            f"{'='*60}\n"
            f"Organizations with Growth tier: {len(growth_orgs)}\n"
            f"{'='*60}"
        )


async def rollback_migration():
    """
    Rollback migration (use with caution!).
    This will reset all organizations to Explorer tier.
    """
    logger.warning(
        "⚠️  ROLLBACK INITIATED - This will reset all migrated organizations!"
    )

    async with AsyncSessionLocal() as db:
        try:
            # Reset organizations
            result = await db.execute(
                select(Organization).where(
                    Organization.pricing_tier == PricingTier.GROWTH
                )
            )
            organizations = result.scalars().all()

            for org in organizations:
                org.pricing_tier = PricingTier.EXPLORER
                org.credits_allocated_monthly = 0
                org.credits_consumed = 0
                org.billing_cycle_start = None

            await db.commit()

            logger.info(f"Rollback complete: Reset {len(organizations)} organizations")

        except Exception as e:
            logger.error(f"Error during rollback: {str(e)}")
            await db.rollback()
            raise


async def main():
    """Main execution function"""
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "migrate":
            logger.info("Starting migration...")
            await migrate_existing_organizations()
            await verify_migration()

        elif command == "verify":
            logger.info("Verifying migration...")
            await verify_migration()

        elif command == "rollback":
            response = input(
                "⚠️  WARNING: This will rollback all migrations. "
                "Type 'CONFIRM' to proceed: "
            )
            if response == "CONFIRM":
                await rollback_migration()
            else:
                logger.info("Rollback cancelled")

        else:
            logger.error(f"Unknown command: {command}")
            print(
                "Usage: python -m backend.scripts.migrate_existing_organizations_to_gating [migrate|verify|rollback]"
            )

    else:
        # Default: run migration
        logger.info("Starting migration (default)...")
        await migrate_existing_organizations()
        await verify_migration()


if __name__ == "__main__":
    asyncio.run(main())
