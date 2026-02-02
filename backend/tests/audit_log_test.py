import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

import asyncio
from datetime import datetime
from backend.database import get_db_context
from backend.models import Organization, AuditLog
from sqlalchemy import select


async def test_audit_logs():
    async with get_db_context() as db:
        # Create an org for testing with unique slug
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        org = Organization(name="Audit Test", slug=f"audit-test-{timestamp}")
        db.add(org)
        await db.commit()

        # Create audit log
        log = AuditLog(
            org_id=org.id,
            action="organization.created",
            resource_type="organization",
            resource_id=org.id,
            metadata={"test": True},
        )
        db.add(log)
        await db.commit()
        log_id = log.id  # Store ID before any rollback
        print(f"✅ Created audit log: {log_id}")

        # Try to update (should fail due to PostgreSQL rule)
        log.action = "organization.updated"
        try:
            await db.commit()
            print("❌ Audit log was modified (rule not working)!")
        except Exception as e:
            # Expected: SQLAlchemy detects 0 rows updated
            print("✅ Audit log update blocked by database rule")
            await db.rollback()  # Rollback the failed transaction

        # Verify it wasn't updated by fetching fresh from DB
        result = await db.execute(select(AuditLog).where(AuditLog.id == log_id))
        fresh_log = result.scalar_one()

        if fresh_log.action == "organization.created":
            print("✅ Audit log value unchanged in database")
        else:
            print("❌ Audit log was modified!")

        # Try to delete (should also fail)
        await db.delete(fresh_log)
        await db.commit()

        # Check if it's still in the database
        result = await db.execute(select(AuditLog).where(AuditLog.id == log_id))
        still_exists = result.scalar_one_or_none()

        if still_exists:
            print("✅ Audit log delete blocked by database rule")
        else:
            print("❌ Audit log was deleted!")


asyncio.run(test_audit_logs())
