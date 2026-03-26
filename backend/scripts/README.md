# Backend Scripts

This directory contains utility and migration scripts for the Cogent backend.

## Migration Scripts

### migrate_existing_organizations_to_gating.py

**Purpose:** One-time migration to transition existing organizations to the new feature gating and pricing system.

**What it does:**
- Assigns Growth tier to all existing organizations
- Allocates 5,000 monthly credits (Growth tier allocation)
- Sets billing cycle start date to current date
- Marks trial status as "converted" (existing customers are past trial phase)

**Prerequisites:**
1. Database migrations must be run first (`alembic upgrade head`)
2. All required tables must exist: `organizations`
3. Database backup should be created before running

**Usage:**

```bash
# Run migration (default command)
python -m backend.scripts.migrate_existing_organizations_to_gating

# Explicitly run migration
python -m backend.scripts.migrate_existing_organizations_to_gating migrate

# Verify migration results
python -m backend.scripts.migrate_existing_organizations_to_gating verify

# Rollback migration (requires confirmation)
python -m backend.scripts.migrate_existing_organizations_to_gating rollback
```

**Docker Usage:**

```bash
# Run migration in Docker container
docker-compose exec backend python -m backend.scripts.migrate_existing_organizations_to_gating migrate

# Verify migration
docker-compose exec backend python -m backend.scripts.migrate_existing_organizations_to_gating verify
```

**Safety Features:**
- Skips organizations that are already migrated (pricing_tier != EXPLORER)
- Logs all actions with detailed status
- Provides verification command to check results
- Includes rollback command (with confirmation prompt)
- Uses database transactions (rolls back on error)

**Expected Output:**

```
INFO:__main__:Found 45 organizations to migrate
INFO:__main__:Migrated organization 123e4567-e89b-12d3-a456-426614174000 (Acme Corp) - Tier: Growth, Beta until: 2026-05-16
...
============================================================
Migration Complete!
============================================================
Total organizations: 45
Migrated: 45
Skipped (already migrated): 0
Errors: 0
============================================================

============================================================
Migration Verification
============================================================
Organizations with Growth tier: 45
Migration verification passed
```

**Rollback:**

If you need to undo the migration:

```bash
python -m backend.scripts.migrate_existing_organizations_to_gating rollback
# Type 'CONFIRM' when prompted
```

**⚠️ Warning:** Rollback will:
- Reset all organizations to Explorer tier
- Clear credit allocations

**Testing in Staging:**

Always test the migration in a staging environment first:

```bash
# 1. Restore production database to staging
# 2. Run migration
docker-compose exec backend python -m backend.scripts.migrate_existing_organizations_to_gating migrate

# 3. Verify results
docker-compose exec backend python -m backend.scripts.migrate_existing_organizations_to_gating verify

# 4. Test application functionality
# - Check that organizations can access Growth tier features
# - Verify credit balance displays correctly
# - Verify pricing summary reflects Growth tier
# - Confirm the account remains on the standard pricing path
```

**Post-Migration Checklist:**

After running the migration in production:

- [ ] Verify migration output shows 0 errors
- [ ] Run verification command - should show matching counts
- [ ] Check application logs for any gating errors
- [ ] Test sample organization:
  - [ ] Can access Growth tier features (API access, on-demand synthesis)
  - [ ] Credit balance shows 5,000 allocated
  - [ ] Subscription price shows the configured Growth tier price
- [ ] Monitor scheduled jobs:
  - [ ] Trial expiry job runs successfully
  - [ ] No errors in job logs
- [ ] Send communication to users about new pricing system

**Troubleshooting:**

**Issue:** "Organizations with Growth tier: 0"
- **Solution:** Check that migrations ran successfully. Run `alembic current` to verify.

**Issue:** "Error: asyncpg.exceptions.ForeignKeyViolationError"
- **Solution:** Ensure all referenced tables exist. Run `alembic upgrade head` first.

**Issue:** Migration appears to hang
- **Solution:** Check database connection. Verify connection pool settings allow sufficient connections. Check for table locks.

## Future Scripts

Additional scripts to be added:
- Credit reconciliation script (monthly reset)
- Beta expiry notification test script
- Pricing mode toggle script (for emergency pricing changes)
- Organization tier upgrade/downgrade script
