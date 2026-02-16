# Feature Gating & Pricing System Implementation Plan

**Version:** 1.0
**Date:** February 15, 2026
**Status:** Planning
**Reference:** Feature_gating_plan.md

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Technical Architecture Overview](#2-technical-architecture-overview)
3. [Database Schema Design](#3-database-schema-design)
4. [Backend Implementation Plan](#4-backend-implementation-plan)
5. [Frontend Implementation Plan](#5-frontend-implementation-plan)
6. [Integration Points](#6-integration-points)
7. [Migration Strategy](#7-migration-strategy)
8. [Testing Strategy](#8-testing-strategy)
9. [Deployment Plan](#9-deployment-plan)
10. [Rollback Procedures](#10-rollback-procedures)
11. [Timeline & Milestones](#11-timeline--milestones)

---

## 1. Executive Summary

### 1.1 Objective

Implement a modular feature gating and pricing system supporting:
- 4-tier pricing (Explorer, Growth, Mid-Market, Enterprise)
- Credit-based usage metering
- Role-based access control (RBAC)
- 30-day reverse trial onboarding
- Beta pricing overlay (temporary, 50% discount)
- Company-level pricing mode toggle (Beta/Standard)
- Account-level beta expiration automation

### 1.2 Core Principles

- **Modular Architecture**: Beta is a pricing modifier, not a system redesign
- **Zero Disruption**: Beta removal requires no code rewrite
- **Clear Separation**: Feature gating ≠ Pricing ≠ Billing
- **Permanent First**: Build for standard pricing; overlay beta temporarily

### 1.3 Success Criteria

- ✅ All 4 tiers gated correctly across frontend/backend
- ✅ Credit consumption tracked accurately
- ✅ Reverse trial auto-downgrade to Explorer works
- ✅ Beta pricing applied only to subscription base price
- ✅ Admin can toggle global pricing mode
- ✅ Users notified 14 days before beta expiration
- ✅ Zero manual intervention for trial→paid transitions

---

## 2. Technical Architecture Overview

### 2.1 System Layers

```
┌─────────────────────────────────────────────┐
│         Frontend (Next.js/TypeScript)       │
│  - Feature Gate Components                  │
│  - Credit Display & Warnings                │
│  - Tier Upgrade Prompts                     │
│  - Admin Dashboard (Pricing Mode Toggle)    │
└─────────────────────────────────────────────┘
                    ↓ API Calls
┌─────────────────────────────────────────────┐
│         Backend (FastAPI/Python)            │
│  - Gating Middleware                        │
│  - Permission Guards                        │
│  - Credit Engine Service                    │
│  - Pricing Calculator Service               │
│  - Trial Management Service                 │
│  - Beta Lifecycle Manager                   │
└─────────────────────────────────────────────┘
                    ↓ Data Access
┌─────────────────────────────────────────────┐
│         Database (PostgreSQL)               │
│  - accounts (tier, beta flags, credits)     │
│  - users (roles)                            │
│  - credit_transactions (audit log)          │
│  - pricing_config (global + tier pricing)   │
│  - beta_accounts (lifecycle tracking)       │
└─────────────────────────────────────────────┘
```

### 2.2 Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Database-driven gating** | Enables dynamic feature toggles without deployment |
| **Middleware enforcement** | Centralized access control; prevents bypass |
| **Service layer separation** | Isolates pricing logic from feature logic |
| **Event-driven credit tracking** | Ensures accurate consumption audit trail |
| **Role inheritance** | Tier gates first, then role gates within tier |

---

## 3. Database Schema Design

### 3.1 Schema Changes Required

#### 3.1.1 `accounts` Table (Modify Existing)

```sql
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS pricing_tier VARCHAR(50) DEFAULT 'explorer';
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS is_beta_account BOOLEAN DEFAULT FALSE;
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS beta_start_date TIMESTAMP;
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS beta_end_date TIMESTAMP;
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS beta_discount_percent DECIMAL(5,2) DEFAULT 50.00;
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS trial_status VARCHAR(50) DEFAULT 'active'; -- active | expired | converted
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS trial_start_date TIMESTAMP;
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS trial_end_date TIMESTAMP;
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS billing_cycle_start DATE;
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS credits_allocated_monthly INTEGER DEFAULT 0;
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS credits_consumed INTEGER DEFAULT 0;
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS credits_overage_rate DECIMAL(10,2) DEFAULT 0.10; -- $ per credit

CREATE INDEX idx_accounts_pricing_tier ON accounts(pricing_tier);
CREATE INDEX idx_accounts_beta_status ON accounts(is_beta_account, beta_end_date);
CREATE INDEX idx_accounts_trial_status ON accounts(trial_status, trial_end_date);
```

**Enums:**
- `pricing_tier`: `explorer`, `growth`, `mid_market`, `enterprise`
- `trial_status`: `active`, `expired`, `converted`

---

#### 3.1.2 `users` Table (Modify Existing)

```sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(50) DEFAULT 'viewer';

CREATE INDEX idx_users_role ON users(role);
```

**Enums:**
- `role`: `owner`, `admin`, `analyst`, `viewer`

---

#### 3.1.3 `credit_transactions` Table (New)

```sql
CREATE TABLE credit_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action_type VARCHAR(100) NOT NULL, -- e.g., 'intelligence_brief', 'api_batch_pull'
    credits_consumed INTEGER NOT NULL,
    credits_remaining INTEGER NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_credit_txn_account ON credit_transactions(account_id, created_at DESC);
CREATE INDEX idx_credit_txn_action ON credit_transactions(action_type);
```

**Purpose:** Full audit trail for credit consumption + overage billing calculations.

---

#### 3.1.4 `pricing_config` Table (New)

```sql
CREATE TABLE pricing_config (
    id SERIAL PRIMARY KEY,
    config_key VARCHAR(100) UNIQUE NOT NULL,
    config_value JSONB NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW(),
    updated_by UUID REFERENCES users(id)
);

-- Seed global pricing mode
INSERT INTO pricing_config (config_key, config_value) VALUES
    ('global_pricing_mode', '"beta"'),
    ('standard_price_explorer', '0'),
    ('standard_price_growth', '499'),
    ('standard_price_mid_market', '2499'),
    ('standard_price_enterprise', '9999'),
    ('trial_duration_days', '30'),
    ('trial_credits', '10000');
```

**Purpose:** Single source of truth for pricing logic; admin-editable without deployment.

---

#### 3.1.5 `beta_accounts` Table (New)

```sql
CREATE TABLE beta_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID UNIQUE NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    beta_start_date TIMESTAMP NOT NULL,
    beta_end_date TIMESTAMP NOT NULL,
    discount_percent DECIMAL(5,2) DEFAULT 50.00,
    notified_14d_before BOOLEAN DEFAULT FALSE,
    notified_7d_before BOOLEAN DEFAULT FALSE,
    transitioned_to_standard BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_beta_expiry ON beta_accounts(beta_end_date) WHERE transitioned_to_standard = FALSE;
```

**Purpose:** Dedicated tracking for beta lifecycle automation + notification flags.

---

#### 3.1.6 `feature_gates` Table (New - Optional, Recommended)

```sql
CREATE TABLE feature_gates (
    id SERIAL PRIMARY KEY,
    feature_key VARCHAR(100) UNIQUE NOT NULL, -- e.g., 'api_access', 'compliance_modules'
    required_tier VARCHAR(50) NOT NULL, -- explorer | growth | mid_market | enterprise
    required_role VARCHAR(50), -- NULL = all roles allowed
    is_enterprise_only BOOLEAN DEFAULT FALSE,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Seed feature gates
INSERT INTO feature_gates (feature_key, required_tier, is_enterprise_only, description) VALUES
    ('continuous_signals_limited', 'explorer', FALSE, 'Limited continuous signals access'),
    ('continuous_signals_full', 'growth', FALSE, 'Full continuous signals access'),
    ('on_demand_synthesis', 'growth', FALSE, 'On-demand synthesis capability'),
    ('api_access', 'growth', FALSE, 'API access enabled'),
    ('compliance_modules', 'mid_market', FALSE, 'Compliance module access'),
    ('custom_contracts', 'mid_market', FALSE, 'Custom contract creation'),
    ('private_signal_store', 'enterprise', TRUE, 'Private signal store access');
```

**Purpose:** Database-driven feature flags; allows runtime changes without code deployment.

---

### 3.2 Alembic Migration Files Needed

```
alembic/versions/
  001_add_pricing_tier_to_accounts.py
  002_add_beta_fields_to_accounts.py
  003_add_trial_fields_to_accounts.py
  004_add_credits_to_accounts.py
  005_add_role_to_users.py
  006_create_credit_transactions_table.py
  007_create_pricing_config_table.py
  008_create_beta_accounts_table.py
  009_create_feature_gates_table.py (optional)
  010_seed_pricing_config_data.py
  011_seed_feature_gates_data.py (optional)
```

---

## 4. Backend Implementation Plan

### 4.1 Models (`backend/models/`)

#### 4.1.1 Update Existing Models

**`backend/models/account.py`** (modify):
```python
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Numeric, Date
from enum import Enum

class PricingTier(str, Enum):
    EXPLORER = "explorer"
    GROWTH = "growth"
    MID_MARKET = "mid_market"
    ENTERPRISE = "enterprise"

class TrialStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CONVERTED = "converted"

class Account(Base):
    # ... existing fields ...
    pricing_tier = Column(String(50), default=PricingTier.EXPLORER)
    is_beta_account = Column(Boolean, default=False)
    beta_start_date = Column(DateTime, nullable=True)
    beta_end_date = Column(DateTime, nullable=True)
    beta_discount_percent = Column(Numeric(5, 2), default=50.00)
    trial_status = Column(String(50), default=TrialStatus.ACTIVE)
    trial_start_date = Column(DateTime, nullable=True)
    trial_end_date = Column(DateTime, nullable=True)
    billing_cycle_start = Column(Date, nullable=True)
    credits_allocated_monthly = Column(Integer, default=0)
    credits_consumed = Column(Integer, default=0)
    credits_overage_rate = Column(Numeric(10, 2), default=0.10)
```

**`backend/models/user.py`** (modify):
```python
from enum import Enum

class UserRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"

class User(Base):
    # ... existing fields ...
    role = Column(String(50), default=UserRole.VIEWER)
```

#### 4.1.2 New Models

**`backend/models/credit_transaction.py`** (new):
```python
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
import uuid

class CreditTransaction(Base):
    __tablename__ = "credit_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    action_type = Column(String(100), nullable=False)
    credits_consumed = Column(Integer, nullable=False)
    credits_remaining = Column(Integer, nullable=False)
    metadata = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())
```

**`backend/models/pricing_config.py`** (new):
```python
class PricingConfig(Base):
    __tablename__ = "pricing_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    config_key = Column(String(100), unique=True, nullable=False)
    config_value = Column(JSON, nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
```

**`backend/models/beta_account.py`** (new):
```python
class BetaAccount(Base):
    __tablename__ = "beta_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), unique=True, nullable=False)
    beta_start_date = Column(DateTime, nullable=False)
    beta_end_date = Column(DateTime, nullable=False)
    discount_percent = Column(Numeric(5, 2), default=50.00)
    notified_14d_before = Column(Boolean, default=False)
    notified_7d_before = Column(Boolean, default=False)
    transitioned_to_standard = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
```

**`backend/models/feature_gate.py`** (new - optional):
```python
class FeatureGate(Base):
    __tablename__ = "feature_gates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    feature_key = Column(String(100), unique=True, nullable=False)
    required_tier = Column(String(50), nullable=False)
    required_role = Column(String(50), nullable=True)
    is_enterprise_only = Column(Boolean, default=False)
    description = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
```

---

### 4.2 Repositories (`backend/repositories/`)

#### 4.2.1 `backend/repositories/pricing_repository.py` (new)

```python
from typing import Optional
from sqlalchemy.orm import Session
from backend.models.pricing_config import PricingConfig

class PricingRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_config(self, key: str) -> Optional[dict]:
        """Fetch pricing config value by key"""
        config = self.db.query(PricingConfig).filter(
            PricingConfig.config_key == key
        ).first()
        return config.config_value if config else None

    def update_config(self, key: str, value: dict, user_id: UUID):
        """Update pricing config (admin only)"""
        config = self.db.query(PricingConfig).filter(
            PricingConfig.config_key == key
        ).first()

        if config:
            config.config_value = value
            config.updated_by = user_id
        else:
            config = PricingConfig(config_key=key, config_value=value, updated_by=user_id)
            self.db.add(config)

        self.db.commit()
        return config

    def get_global_pricing_mode(self) -> str:
        """Returns 'beta' or 'standard'"""
        mode = self.get_config("global_pricing_mode")
        return mode if mode in ["beta", "standard"] else "standard"

    def set_global_pricing_mode(self, mode: str, user_id: UUID):
        """Admin toggle for pricing mode"""
        if mode not in ["beta", "standard"]:
            raise ValueError("Invalid pricing mode")
        return self.update_config("global_pricing_mode", mode, user_id)
```

#### 4.2.2 `backend/repositories/credit_repository.py` (new)

```python
from backend.models.credit_transaction import CreditTransaction
from backend.models.account import Account

class CreditRepository:
    def __init__(self, db: Session):
        self.db = db

    def consume_credits(self, account_id: UUID, user_id: UUID, action_type: str,
                       credits: int, metadata: dict = None) -> CreditTransaction:
        """Consume credits and log transaction"""
        account = self.db.query(Account).filter(Account.id == account_id).first()

        if not account:
            raise ValueError("Account not found")

        if account.credits_consumed + credits > account.credits_allocated_monthly:
            # Overage scenario - still allow but flag for billing
            pass

        account.credits_consumed += credits

        txn = CreditTransaction(
            account_id=account_id,
            user_id=user_id,
            action_type=action_type,
            credits_consumed=credits,
            credits_remaining=account.credits_allocated_monthly - account.credits_consumed,
            metadata=metadata
        )

        self.db.add(txn)
        self.db.commit()
        self.db.refresh(txn)

        return txn

    def get_remaining_credits(self, account_id: UUID) -> int:
        """Get remaining credits for account"""
        account = self.db.query(Account).filter(Account.id == account_id).first()
        if not account:
            return 0
        return max(0, account.credits_allocated_monthly - account.credits_consumed)

    def get_overage(self, account_id: UUID) -> int:
        """Get overage credits (negative = no overage)"""
        account = self.db.query(Account).filter(Account.id == account_id).first()
        if not account:
            return 0
        overage = account.credits_consumed - account.credits_allocated_monthly
        return max(0, overage)
```

#### 4.2.3 `backend/repositories/beta_repository.py` (new)

```python
from backend.models.beta_account import BetaAccount
from datetime import datetime, timedelta

class BetaRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_expiring_soon(self, days: int) -> list[BetaAccount]:
        """Get beta accounts expiring in N days"""
        threshold = datetime.utcnow() + timedelta(days=days)
        return self.db.query(BetaAccount).filter(
            BetaAccount.beta_end_date <= threshold,
            BetaAccount.transitioned_to_standard == False
        ).all()

    def mark_notified(self, beta_id: UUID, notification_type: str):
        """Mark notification sent"""
        beta = self.db.query(BetaAccount).filter(BetaAccount.id == beta_id).first()
        if beta:
            if notification_type == "14d":
                beta.notified_14d_before = True
            elif notification_type == "7d":
                beta.notified_7d_before = True
            self.db.commit()
```

---

### 4.3 Services (`backend/services/`)

#### 4.3.1 `backend/services/gating_service.py` (new)

```python
from backend.models.account import Account, PricingTier
from backend.models.user import User, UserRole
from backend.repositories.pricing_repository import PricingRepository
from sqlalchemy.orm import Session

class GatingService:
    def __init__(self, db: Session):
        self.db = db
        self.pricing_repo = PricingRepository(db)

    def check_feature_access(self, account: Account, user: User, feature_key: str) -> bool:
        """
        Check if user can access a feature based on tier + role.
        Returns True if allowed, False otherwise.
        """
        # Define tier hierarchy
        tier_hierarchy = {
            PricingTier.EXPLORER: 0,
            PricingTier.GROWTH: 1,
            PricingTier.MID_MARKET: 2,
            PricingTier.ENTERPRISE: 3
        }

        # Feature gate rules (could be pulled from feature_gates table)
        feature_gates = {
            "continuous_signals_full": {"tier": PricingTier.GROWTH, "role": None},
            "on_demand_synthesis": {"tier": PricingTier.GROWTH, "role": None},
            "api_access": {"tier": PricingTier.GROWTH, "role": None},
            "compliance_modules": {"tier": PricingTier.MID_MARKET, "role": None},
            "custom_contracts": {"tier": PricingTier.MID_MARKET, "role": None},
            "private_signal_store": {"tier": PricingTier.ENTERPRISE, "role": None},
            # Role-based gates (examples)
            "create_synthesis": {"tier": None, "role": [UserRole.OWNER, UserRole.ADMIN, UserRole.ANALYST]},
        }

        gate = feature_gates.get(feature_key)
        if not gate:
            return True  # Feature not gated

        # Check tier requirement
        if gate["tier"]:
            required_tier_level = tier_hierarchy.get(gate["tier"], 0)
            current_tier_level = tier_hierarchy.get(account.pricing_tier, 0)
            if current_tier_level < required_tier_level:
                return False

        # Check role requirement
        if gate["role"]:
            if user.role not in gate["role"]:
                return False

        return True

    def require_feature(self, account: Account, user: User, feature_key: str):
        """Raise exception if feature not accessible"""
        if not self.check_feature_access(account, user, feature_key):
            raise PermissionError(f"Feature '{feature_key}' requires higher tier or role")
```

#### 4.3.2 `backend/services/pricing_service.py` (new)

```python
from backend.models.account import Account
from backend.repositories.pricing_repository import PricingRepository
from datetime import datetime
from decimal import Decimal

class PricingService:
    def __init__(self, db: Session):
        self.db = db
        self.pricing_repo = PricingRepository(db)

    def calculate_subscription_price(self, account: Account) -> Decimal:
        """
        Calculate current subscription price for account.
        Applies beta discount if applicable.
        """
        # Get standard price for tier
        tier_price_key = f"standard_price_{account.pricing_tier}"
        standard_price = Decimal(self.pricing_repo.get_config(tier_price_key) or 0)

        # Check if beta discount applies
        if self._is_beta_active(account):
            discount_percent = account.beta_discount_percent or Decimal(50)
            discounted_price = standard_price * (Decimal(100) - discount_percent) / Decimal(100)
            return discounted_price

        return standard_price

    def _is_beta_active(self, account: Account) -> bool:
        """Check if beta pricing is active for this account"""
        if not account.is_beta_account:
            return False

        if not account.beta_end_date:
            return False

        if datetime.utcnow() > account.beta_end_date:
            return False

        return True

    def calculate_overage_cost(self, account: Account) -> Decimal:
        """Calculate cost of credit overage"""
        overage = max(0, account.credits_consumed - account.credits_allocated_monthly)
        # IMPORTANT: Overage is NEVER discounted
        return Decimal(overage) * account.credits_overage_rate
```

#### 4.3.3 `backend/services/trial_service.py` (new)

```python
from backend.models.account import Account, TrialStatus, PricingTier
from datetime import datetime, timedelta

class TrialService:
    def __init__(self, db: Session):
        self.db = db

    def start_trial(self, account: Account):
        """Initialize 30-day reverse trial"""
        trial_duration = 30  # Could be pulled from pricing_config
        trial_credits = 10000  # Could be pulled from pricing_config

        account.trial_status = TrialStatus.ACTIVE
        account.trial_start_date = datetime.utcnow()
        account.trial_end_date = datetime.utcnow() + timedelta(days=trial_duration)
        account.pricing_tier = PricingTier.GROWTH  # Full Growth access during trial
        account.credits_allocated_monthly = trial_credits
        account.credits_consumed = 0

        self.db.commit()

    def check_trial_expiry(self, account: Account):
        """Check if trial has expired and handle downgrade"""
        if account.trial_status != TrialStatus.ACTIVE:
            return

        if datetime.utcnow() > account.trial_end_date:
            # Check if user has subscribed
            if account.billing_cycle_start:
                # User subscribed - convert trial
                account.trial_status = TrialStatus.CONVERTED
            else:
                # No subscription - downgrade to Explorer
                account.trial_status = TrialStatus.EXPIRED
                account.pricing_tier = PricingTier.EXPLORER
                account.credits_allocated_monthly = 0
                account.credits_consumed = 0

            self.db.commit()

    def convert_trial_to_paid(self, account: Account, selected_tier: str):
        """Convert trial to paid subscription"""
        account.trial_status = TrialStatus.CONVERTED
        account.pricing_tier = selected_tier
        account.billing_cycle_start = datetime.utcnow().date()

        # Allocate credits based on tier
        tier_credits = {
            PricingTier.EXPLORER: 0,
            PricingTier.GROWTH: 5000,
            PricingTier.MID_MARKET: 25000,
            PricingTier.ENTERPRISE: 100000
        }
        account.credits_allocated_monthly = tier_credits.get(selected_tier, 0)
        account.credits_consumed = 0  # Reset credits on new billing cycle

        self.db.commit()
```

#### 4.3.4 `backend/services/beta_lifecycle_service.py` (new)

```python
from backend.repositories.beta_repository import BetaRepository
from backend.models.account import Account
from datetime import datetime

class BetaLifecycleService:
    def __init__(self, db: Session):
        self.db = db
        self.beta_repo = BetaRepository(db)

    def process_beta_notifications(self):
        """
        Scheduled job: Send notifications for expiring beta accounts.
        Run daily via cron/celery.
        """
        # 14-day warning
        expiring_14d = self.beta_repo.get_expiring_soon(14)
        for beta in expiring_14d:
            if not beta.notified_14d_before:
                self._send_beta_expiry_notification(beta.account_id, days_remaining=14)
                self.beta_repo.mark_notified(beta.id, "14d")

        # 7-day warning
        expiring_7d = self.beta_repo.get_expiring_soon(7)
        for beta in expiring_7d:
            if not beta.notified_7d_before:
                self._send_beta_expiry_notification(beta.account_id, days_remaining=7)
                self.beta_repo.mark_notified(beta.id, "7d")

    def process_beta_expirations(self):
        """
        Scheduled job: Transition expired beta accounts to standard pricing.
        Run daily via cron/celery.
        """
        expired = self.beta_repo.get_expiring_soon(0)  # Already expired
        for beta in expired:
            account = self.db.query(Account).filter(Account.id == beta.account_id).first()
            if account and account.is_beta_account:
                # Transition to standard
                account.is_beta_account = False
                beta.transitioned_to_standard = True
                self.db.commit()

                # Send final notification with new price
                self._send_standard_pricing_notification(account.id)

    def _send_beta_expiry_notification(self, account_id, days_remaining):
        """Send email/notification about beta expiry"""
        # TODO: Integrate with notification service
        pass

    def _send_standard_pricing_notification(self, account_id):
        """Send notification about transition to standard pricing"""
        # TODO: Integrate with notification service
        pass
```

---

### 4.4 Middleware (`backend/middleware/`)

#### 4.4.1 `backend/middleware/gating_middleware.py` (new)

```python
from fastapi import Request, HTTPException
from backend.services.gating_service import GatingService
from backend.auth.dependencies import get_current_user, get_current_account

async def enforce_feature_gate(request: Request, feature_key: str):
    """
    Middleware decorator for route-level feature gating.
    Usage: @enforce_feature_gate("api_access")
    """
    user = await get_current_user(request)
    account = await get_current_account(request)

    gating_service = GatingService(request.state.db)

    if not gating_service.check_feature_access(account, user, feature_key):
        raise HTTPException(
            status_code=403,
            detail=f"Your account tier does not have access to this feature. Please upgrade to continue."
        )

    return True
```

---

### 4.5 API Endpoints (`backend/api/`)

#### 4.5.1 `backend/api/pricing.py` (new)

```python
from fastapi import APIRouter, Depends, HTTPException
from backend.services.pricing_service import PricingService
from backend.services.gating_service import GatingService
from backend.auth.dependencies import get_current_account, get_current_user

router = APIRouter(prefix="/api/pricing", tags=["pricing"])

@router.get("/current")
async def get_current_pricing(
    account = Depends(get_current_account),
    db = Depends(get_db)
):
    """Get current subscription price for account"""
    pricing_service = PricingService(db)

    return {
        "tier": account.pricing_tier,
        "subscription_price": pricing_service.calculate_subscription_price(account),
        "is_beta": account.is_beta_account,
        "beta_ends": account.beta_end_date,
        "overage_cost": pricing_service.calculate_overage_cost(account)
    }

@router.get("/features")
async def get_feature_access(
    account = Depends(get_current_account),
    user = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get list of features available to current user"""
    gating_service = GatingService(db)

    features = [
        "continuous_signals_full",
        "on_demand_synthesis",
        "api_access",
        "compliance_modules",
        "custom_contracts",
        "private_signal_store"
    ]

    access_map = {
        feature: gating_service.check_feature_access(account, user, feature)
        for feature in features
    }

    return {
        "tier": account.pricing_tier,
        "role": user.role,
        "features": access_map
    }

@router.post("/upgrade")
async def upgrade_tier(
    tier: str,
    account = Depends(get_current_account),
    db = Depends(get_db)
):
    """Upgrade account tier (triggers billing flow)"""
    # TODO: Integrate with Stripe/payment processor
    # For now, just update tier
    account.pricing_tier = tier
    db.commit()

    return {"status": "upgraded", "new_tier": tier}
```

#### 4.5.2 `backend/api/credits.py` (new)

```python
from fastapi import APIRouter, Depends
from backend.repositories.credit_repository import CreditRepository
from backend.auth.dependencies import get_current_account

router = APIRouter(prefix="/api/credits", tags=["credits"])

@router.get("/balance")
async def get_credit_balance(
    account = Depends(get_current_account),
    db = Depends(get_db)
):
    """Get current credit balance"""
    credit_repo = CreditRepository(db)

    return {
        "allocated": account.credits_allocated_monthly,
        "consumed": account.credits_consumed,
        "remaining": credit_repo.get_remaining_credits(account.id),
        "overage": credit_repo.get_overage(account.id),
        "overage_rate": account.credits_overage_rate
    }

@router.get("/transactions")
async def get_credit_transactions(
    account = Depends(get_current_account),
    db = Depends(get_db),
    limit: int = 50
):
    """Get credit transaction history"""
    txns = db.query(CreditTransaction).filter(
        CreditTransaction.account_id == account.id
    ).order_by(CreditTransaction.created_at.desc()).limit(limit).all()

    return {"transactions": txns}
```

#### 4.5.3 `backend/api/admin/pricing.py` (new)

```python
from fastapi import APIRouter, Depends, HTTPException
from backend.repositories.pricing_repository import PricingRepository
from backend.auth.guards import require_admin

router = APIRouter(prefix="/api/admin/pricing", tags=["admin"])

@router.get("/mode")
async def get_pricing_mode(
    user = Depends(require_admin),
    db = Depends(get_db)
):
    """Get global pricing mode"""
    pricing_repo = PricingRepository(db)
    return {"mode": pricing_repo.get_global_pricing_mode()}

@router.post("/mode")
async def set_pricing_mode(
    mode: str,
    user = Depends(require_admin),
    db = Depends(get_db)
):
    """Toggle global pricing mode (beta <-> standard)"""
    if mode not in ["beta", "standard"]:
        raise HTTPException(status_code=400, detail="Invalid mode")

    pricing_repo = PricingRepository(db)
    pricing_repo.set_global_pricing_mode(mode, user.id)

    return {"status": "updated", "mode": mode}
```

---

### 4.6 Background Jobs (`backend/jobs/`)

#### 4.6.1 `backend/jobs/trial_expiry_job.py` (new)

```python
from backend.services.trial_service import TrialService
from backend.models.account import Account, TrialStatus
from backend.database import get_db

def check_trial_expiries():
    """Scheduled job: Check and process trial expirations"""
    db = next(get_db())
    trial_service = TrialService(db)

    active_trials = db.query(Account).filter(
        Account.trial_status == TrialStatus.ACTIVE
    ).all()

    for account in active_trials:
        trial_service.check_trial_expiry(account)

    print(f"Processed {len(active_trials)} trial accounts")
```

#### 4.6.2 `backend/jobs/beta_lifecycle_job.py` (new)

```python
from backend.services.beta_lifecycle_service import BetaLifecycleService
from backend.database import get_db

def process_beta_lifecycle():
    """Scheduled job: Send beta notifications and handle expirations"""
    db = next(get_db())
    beta_service = BetaLifecycleService(db)

    beta_service.process_beta_notifications()
    beta_service.process_beta_expirations()

    print("Beta lifecycle processing complete")
```

#### 4.6.3 Celery/APScheduler Configuration

**`backend/jobs/scheduler.py`** (new):
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from backend.jobs.trial_expiry_job import check_trial_expiries
from backend.jobs.beta_lifecycle_job import process_beta_lifecycle

scheduler = AsyncIOScheduler()

def start_scheduled_jobs():
    # Run trial expiry check daily at 2 AM UTC
    scheduler.add_job(check_trial_expiries, 'cron', hour=2, minute=0)

    # Run beta lifecycle processing daily at 3 AM UTC
    scheduler.add_job(process_beta_lifecycle, 'cron', hour=3, minute=0)

    scheduler.start()
```

---

## 5. Frontend Implementation Plan

### 5.1 Context & Hooks (`frontend/lib/`)

#### 5.1.1 `frontend/lib/contexts/PricingContext.tsx` (new)

```typescript
import { createContext, useContext, useEffect, useState } from 'react';

interface PricingContextType {
  tier: string;
  features: Record<string, boolean>;
  credits: {
    allocated: number;
    consumed: number;
    remaining: number;
    overage: number;
  };
  isBeta: boolean;
  betaEnds: string | null;
  loading: boolean;
}

const PricingContext = createContext<PricingContextType | null>(null);

export function PricingProvider({ children }: { children: React.ReactNode }) {
  const [pricingData, setPricingData] = useState<PricingContextType | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchPricingData() {
      try {
        const [pricingRes, featuresRes, creditsRes] = await Promise.all([
          fetch('/api/pricing/current'),
          fetch('/api/pricing/features'),
          fetch('/api/credits/balance')
        ]);

        const pricing = await pricingRes.json();
        const features = await featuresRes.json();
        const credits = await creditsRes.json();

        setPricingData({
          tier: pricing.tier,
          features: features.features,
          credits: credits,
          isBeta: pricing.is_beta,
          betaEnds: pricing.beta_ends,
          loading: false
        });
      } catch (error) {
        console.error('Failed to load pricing data', error);
      } finally {
        setLoading(false);
      }
    }

    fetchPricingData();
  }, []);

  return (
    <PricingContext.Provider value={pricingData}>
      {children}
    </PricingContext.Provider>
  );
}

export function usePricing() {
  const context = useContext(PricingContext);
  if (!context) {
    throw new Error('usePricing must be used within PricingProvider');
  }
  return context;
}
```

#### 5.1.2 `frontend/lib/hooks/useFeatureGate.ts` (new)

```typescript
import { usePricing } from '../contexts/PricingContext';

export function useFeatureGate(featureKey: string) {
  const { features, loading } = usePricing();

  const hasAccess = features?.[featureKey] ?? false;

  return {
    hasAccess,
    loading,
    isGated: !hasAccess
  };
}
```

---

### 5.2 Components (`frontend/components/`)

#### 5.2.1 `frontend/components/FeatureGate.tsx` (new)

```typescript
import { useFeatureGate } from '@/lib/hooks/useFeatureGate';
import { UpgradePrompt } from './UpgradePrompt';

interface FeatureGateProps {
  feature: string;
  children: React.ReactNode;
  fallback?: React.ReactNode;
  showUpgradePrompt?: boolean;
}

export function FeatureGate({
  feature,
  children,
  fallback,
  showUpgradePrompt = true
}: FeatureGateProps) {
  const { hasAccess, loading } = useFeatureGate(feature);

  if (loading) {
    return <div className="animate-pulse">Loading...</div>;
  }

  if (!hasAccess) {
    if (showUpgradePrompt) {
      return <UpgradePrompt feature={feature} />;
    }
    return fallback || null;
  }

  return <>{children}</>;
}
```

#### 5.2.2 `frontend/components/UpgradePrompt.tsx` (new)

```typescript
import { usePricing } from '@/lib/contexts/PricingContext';

export function UpgradePrompt({ feature }: { feature: string }) {
  const { tier } = usePricing();

  const featureTiers = {
    'api_access': 'Growth',
    'compliance_modules': 'Mid-Market',
    'private_signal_store': 'Enterprise'
  };

  const requiredTier = featureTiers[feature] || 'Growth';

  return (
    <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-6">
      <h3 className="text-lg font-semibold text-gray-900">Upgrade Required</h3>
      <p className="mt-2 text-sm text-gray-600">
        This feature requires <span className="font-semibold">{requiredTier}</span> tier or higher.
      </p>
      <p className="mt-1 text-xs text-gray-500">
        Current tier: <span className="capitalize">{tier}</span>
      </p>
      <button className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700">
        Upgrade to {requiredTier}
      </button>
    </div>
  );
}
```

#### 5.2.3 `frontend/components/CreditDisplay.tsx` (new)

```typescript
import { usePricing } from '@/lib/contexts/PricingContext';

export function CreditDisplay() {
  const { credits } = usePricing();

  const percentage = (credits.remaining / credits.allocated) * 100;
  const isLow = percentage < 20;
  const hasOverage = credits.overage > 0;

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-gray-700">Credits</span>
        <span className={`text-sm font-semibold ${isLow ? 'text-red-600' : 'text-gray-900'}`}>
          {credits.remaining.toLocaleString()} / {credits.allocated.toLocaleString()}
        </span>
      </div>

      <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
        <div
          className={`h-2 rounded-full ${isLow ? 'bg-red-500' : 'bg-blue-600'}`}
          style={{ width: `${Math.min(percentage, 100)}%` }}
        />
      </div>

      {hasOverage && (
        <div className="mt-2 text-xs text-red-600">
          ⚠️ Overage: {credits.overage.toLocaleString()} credits
        </div>
      )}

      {isLow && !hasOverage && (
        <div className="mt-2 text-xs text-amber-600">
          ⚠️ Running low on credits
        </div>
      )}
    </div>
  );
}
```

#### 5.2.4 `frontend/components/BetaBanner.tsx` (new)

```typescript
import { usePricing } from '@/lib/contexts/PricingContext';

export function BetaBanner() {
  const { isBeta, betaEnds } = usePricing();

  if (!isBeta || !betaEnds) return null;

  const daysRemaining = Math.ceil(
    (new Date(betaEnds).getTime() - Date.now()) / (1000 * 60 * 60 * 24)
  );

  const isUrgent = daysRemaining <= 14;

  return (
    <div className={`${isUrgent ? 'bg-amber-100 border-amber-400' : 'bg-blue-100 border-blue-400'} border-l-4 p-4`}>
      <div className="flex items-center">
        <div className="flex-shrink-0">
          {isUrgent ? '⚠️' : 'ℹ️'}
        </div>
        <div className="ml-3">
          <p className="text-sm text-gray-700">
            <span className="font-semibold">Beta Pricing Active:</span> Your 50% discount ends in {daysRemaining} days.
          </p>
          <p className="text-xs text-gray-600 mt-1">
            Standard pricing will apply starting {new Date(betaEnds).toLocaleDateString()}.
          </p>
        </div>
      </div>
    </div>
  );
}
```

#### 5.2.5 `frontend/components/admin/PricingModeToggle.tsx` (new)

```typescript
'use client';

import { useState } from 'react';

export function PricingModeToggle() {
  const [mode, setMode] = useState<'beta' | 'standard'>('beta');
  const [loading, setLoading] = useState(false);

  const toggleMode = async () => {
    setLoading(true);
    try {
      const newMode = mode === 'beta' ? 'standard' : 'beta';
      await fetch('/api/admin/pricing/mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: newMode })
      });
      setMode(newMode);
    } catch (error) {
      console.error('Failed to toggle pricing mode', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6">
      <h3 className="text-lg font-semibold text-gray-900">Global Pricing Mode</h3>
      <p className="mt-2 text-sm text-gray-600">
        Controls whether new accounts receive beta pricing or standard pricing.
      </p>

      <div className="mt-4 flex items-center space-x-4">
        <span className="text-sm font-medium text-gray-700">Current Mode:</span>
        <span className={`px-3 py-1 rounded-full text-sm font-semibold ${
          mode === 'beta' ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-800'
        }`}>
          {mode.toUpperCase()}
        </span>
      </div>

      <button
        onClick={toggleMode}
        disabled={loading}
        className="mt-4 px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
      >
        {loading ? 'Updating...' : `Switch to ${mode === 'beta' ? 'Standard' : 'Beta'}`}
      </button>
    </div>
  );
}
```

---

### 5.3 Page Updates

#### 5.3.1 `frontend/app/layout.tsx` (modify)

```typescript
import { PricingProvider } from '@/lib/contexts/PricingContext';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <PricingProvider>
          <BetaBanner />
          {children}
        </PricingProvider>
      </body>
    </html>
  );
}
```

#### 5.3.2 Example Usage in Feature Pages

```typescript
// frontend/app/api/page.tsx
import { FeatureGate } from '@/components/FeatureGate';

export default function APIPage() {
  return (
    <FeatureGate feature="api_access">
      <div>
        <h1>API Access</h1>
        {/* API key management, docs, etc. */}
      </div>
    </FeatureGate>
  );
}
```

---

## 6. Integration Points

### 6.1 Credit Consumption Integration

Every action that consumes credits must call:

```python
from backend.repositories.credit_repository import CreditRepository

credit_repo = CreditRepository(db)
credit_repo.consume_credits(
    account_id=account.id,
    user_id=user.id,
    action_type="intelligence_brief",
    credits=50,
    metadata={"brief_id": brief.id}
)
```

**Actions to Integrate:**
- Intelligence brief creation → 50 credits
- On-demand synthesis → 100 credits
- API batch pull → 25 credits
- Deep historical query → 200 credits
- Alert trigger → 1 credit

**Files to Modify:**
- `backend/services/brief_service.py`
- `backend/api/synthesis.py`
- `backend/api/api_endpoints.py`
- `backend/services/alert_service.py`

---

### 6.2 Feature Gate Integration

Add feature gates to existing endpoints:

```python
from backend.middleware.gating_middleware import enforce_feature_gate

@router.post("/synthesis/generate")
async def generate_synthesis(
    ...,
    _: bool = Depends(lambda req: enforce_feature_gate(req, "on_demand_synthesis"))
):
    # Synthesis logic
    pass
```

**Endpoints to Gate:**
- `/api/synthesis/*` → `on_demand_synthesis`
- `/api/v1/*` → `api_access`
- `/api/compliance/*` → `compliance_modules`
- `/api/signals/custom/*` → `custom_contracts`

---

### 6.3 Billing Integration (Future)

When integrating with Stripe/payment processor:

```python
# backend/services/billing_service.py
from backend.services.pricing_service import PricingService

def create_subscription(account: Account, tier: str):
    pricing_service = PricingService(db)

    # Calculate price (with beta discount if applicable)
    price = pricing_service.calculate_subscription_price(account)

    # Create Stripe subscription
    stripe.Subscription.create(
        customer=account.stripe_customer_id,
        items=[{"price_data": {
            "currency": "usd",
            "product": f"esip_{tier}",
            "recurring": {"interval": "month"},
            "unit_amount": int(price * 100)  # Convert to cents
        }}]
    )
```

---

## 7. Migration Strategy

### 7.1 Migration Sequence

1. **Phase 1: Database Schema** (Day 1)
   - Run Alembic migrations 001-011
   - Verify schema changes in staging
   - Seed pricing config data

2. **Phase 2: Backend Models & Repos** (Day 2-3)
   - Deploy updated models
   - Deploy repository layer
   - Test data access patterns

3. **Phase 3: Backend Services** (Day 4-5)
   - Deploy gating service
   - Deploy pricing service
   - Deploy trial service
   - Deploy beta lifecycle service

4. **Phase 4: API Endpoints** (Day 6-7)
   - Deploy new pricing/credits endpoints
   - Add feature gate middleware to existing endpoints
   - Test API responses

5. **Phase 5: Background Jobs** (Day 8)
   - Deploy scheduled jobs
   - Verify job execution
   - Monitor logs

6. **Phase 6: Frontend** (Day 9-11)
   - Deploy context providers
   - Deploy gating components
   - Update existing pages
   - Test UI flows

7. **Phase 7: Integration** (Day 12-13)
   - Integrate credit consumption into all actions
   - Add feature gates to all protected endpoints
   - End-to-end testing

8. **Phase 8: Beta Rollout** (Day 14)
   - Set `global_pricing_mode = 'beta'`
   - Create beta accounts for existing users
   - Send launch communications

---

### 7.2 Existing Account Migration

**Script: `backend/scripts/migrate_existing_accounts_to_gating.py`**

```python
from backend.database import get_db
from backend.models.account import Account, PricingTier
from datetime import datetime, timedelta

def migrate_existing_accounts():
    """
    One-time migration: Assign tiers and beta to existing accounts.
    """
    db = next(get_db())

    existing_accounts = db.query(Account).all()

    for account in existing_accounts:
        # Assign default tier (Growth) to existing paying customers
        account.pricing_tier = PricingTier.GROWTH

        # Enroll in beta (90 days)
        account.is_beta_account = True
        account.beta_start_date = datetime.utcnow()
        account.beta_end_date = datetime.utcnow() + timedelta(days=90)
        account.beta_discount_percent = 50.00

        # Allocate Growth-level credits
        account.credits_allocated_monthly = 5000
        account.credits_consumed = 0

        # Set billing cycle start (assume today for existing)
        account.billing_cycle_start = datetime.utcnow().date()

    db.commit()
    print(f"Migrated {len(existing_accounts)} accounts to gating system")

if __name__ == "__main__":
    migrate_existing_accounts()
```

---

## 8. Testing Strategy

### 8.1 Unit Tests

**`tests/test_gating_service.py`**:
```python
def test_tier_based_gating():
    account = Account(pricing_tier=PricingTier.EXPLORER)
    user = User(role=UserRole.VIEWER)
    service = GatingService(db)

    assert service.check_feature_access(account, user, "api_access") == False

    account.pricing_tier = PricingTier.GROWTH
    assert service.check_feature_access(account, user, "api_access") == True
```

**`tests/test_pricing_service.py`**:
```python
def test_beta_discount_applied():
    account = Account(
        pricing_tier=PricingTier.GROWTH,
        is_beta_account=True,
        beta_end_date=datetime.utcnow() + timedelta(days=30)
    )

    service = PricingService(db)
    price = service.calculate_subscription_price(account)

    # Growth standard = $499, beta = $249.50
    assert price == Decimal("249.50")
```

**`tests/test_credit_service.py`**:
```python
def test_credit_consumption():
    account = Account(credits_allocated_monthly=1000, credits_consumed=0)
    credit_repo = CreditRepository(db)

    credit_repo.consume_credits(account.id, user.id, "intelligence_brief", 50)

    assert account.credits_consumed == 50
    assert credit_repo.get_remaining_credits(account.id) == 950
```

---

### 8.2 Integration Tests

**`tests/integration/test_trial_flow.py`**:
```python
def test_reverse_trial_to_paid_conversion():
    # 1. Create new account
    account = create_test_account()

    # 2. Start trial
    trial_service.start_trial(account)
    assert account.pricing_tier == PricingTier.GROWTH
    assert account.credits_allocated_monthly == 10000

    # 3. Fast-forward 30 days (mock)
    account.trial_end_date = datetime.utcnow() - timedelta(days=1)

    # 4. User subscribes before expiry
    trial_service.convert_trial_to_paid(account, PricingTier.GROWTH)

    assert account.trial_status == TrialStatus.CONVERTED
    assert account.billing_cycle_start is not None
```

---

### 8.3 E2E Tests (Playwright)

**`frontend/e2e/feature-gating.spec.ts`**:
```typescript
test('should show upgrade prompt for gated feature', async ({ page }) => {
  // Login as Explorer tier user
  await loginAs(page, 'explorer-user@test.com');

  // Navigate to API page
  await page.goto('/api');

  // Should see upgrade prompt
  await expect(page.locator('text=Upgrade Required')).toBeVisible();
  await expect(page.locator('text=Growth tier or higher')).toBeVisible();
});

test('should grant access after tier upgrade', async ({ page }) => {
  await loginAs(page, 'growth-user@test.com');

  await page.goto('/api');

  // Should NOT see upgrade prompt
  await expect(page.locator('text=Upgrade Required')).not.toBeVisible();

  // Should see API dashboard
  await expect(page.locator('text=API Keys')).toBeVisible();
});
```

---

## 9. Deployment Plan

### 9.1 Pre-Deployment Checklist

- [ ] All Alembic migrations tested in staging
- [ ] Database backups created
- [ ] Pricing config seeded correctly
- [ ] Feature gates seeded correctly
- [ ] Scheduled jobs configured in production cron/Celery
- [ ] Frontend environment variables set (API endpoints)
- [ ] Monitoring/alerting configured for:
  - Beta expiration job failures
  - Trial expiry job failures
  - Credit overage spikes
- [ ] Communication plan ready for users

---

### 9.2 Deployment Steps

#### Backend Deployment

```bash
# 1. Run migrations
docker-compose exec backend alembic upgrade head

# 2. Run account migration script (one-time)
docker-compose exec backend python backend/scripts/migrate_existing_accounts_to_gating.py

# 3. Restart backend services
docker-compose restart backend worker

# 4. Verify jobs scheduled
docker-compose exec backend python -c "from backend.jobs.scheduler import start_scheduled_jobs; start_scheduled_jobs()"
```

#### Frontend Deployment

```bash
# 1. Build with new gating components
cd frontend
npm run build

# 2. Deploy to production
npm run deploy
```

---

### 9.3 Post-Deployment Verification

**Checklist:**
- [ ] `/api/pricing/current` returns correct tier
- [ ] `/api/pricing/features` returns feature access map
- [ ] `/api/credits/balance` returns credit data
- [ ] Feature gates block Explorer users from Growth features
- [ ] Admin dashboard pricing toggle works
- [ ] Beta banner displays for beta accounts
- [ ] Credit display shows correct balance
- [ ] Trial accounts auto-downgrade after 30 days
- [ ] Beta expiry notifications sent 14 days before

**Smoke Test Script:**
```python
# tests/smoke_test_gating_system.py
def smoke_test():
    # Test 1: Explorer account cannot access API
    # Test 2: Growth account can access API
    # Test 3: Beta discount applies correctly
    # Test 4: Credit consumption logs correctly
    # Test 5: Trial expiry triggers downgrade
    pass
```

---

## 10. Rollback Procedures

### 10.1 Emergency Rollback

If critical issues arise:

1. **Disable Feature Gating**:
   ```sql
   UPDATE pricing_config SET config_value = '"disabled"' WHERE config_key = 'global_pricing_mode';
   ```

2. **Revert Migrations**:
   ```bash
   docker-compose exec backend alembic downgrade -1
   ```

3. **Frontend Revert**:
   ```bash
   # Redeploy previous frontend version
   git checkout <previous-commit>
   npm run build && npm run deploy
   ```

---

### 10.2 Data Recovery

All credit transactions logged to `credit_transactions` table.

To restore credit balance:
```sql
SELECT SUM(credits_consumed) FROM credit_transactions WHERE account_id = '<uuid>';
UPDATE accounts SET credits_consumed = <sum> WHERE id = '<uuid>';
```

---

## 11. Timeline & Milestones

### 11.1 Development Timeline (14 Days)

| Day | Milestone | Deliverables |
|-----|-----------|--------------|
| 1 | Database schema complete | Alembic migrations 001-011 |
| 2-3 | Backend models & repos | All repository classes functional |
| 4-5 | Backend services | Gating, pricing, trial, beta services |
| 6-7 | API endpoints | Pricing/credits/admin endpoints |
| 8 | Background jobs | Scheduled jobs configured |
| 9-11 | Frontend components | Context, hooks, components |
| 12-13 | Integration & testing | E2E tests passing |
| 14 | Deployment | Production rollout |

---

### 11.2 Success Metrics (Week 1 Post-Launch)

- **Gating Accuracy**: 100% of gated features correctly block lower tiers
- **Credit Tracking**: 100% of credit-consuming actions logged
- **Trial Conversion**: >20% of trial users convert to paid
- **Beta Enrollment**: 100% of existing accounts enrolled in beta
- **Zero Downtime**: No service disruptions during rollout
- **User Complaints**: <5% of users report gating issues

---

## 12. Risk Mitigation

### 12.1 Identified Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Migration breaks existing accounts | Medium | High | Comprehensive staging tests + rollback plan |
| Credit overage not billed | Low | High | Audit trail + automated billing reconciliation |
| Feature gates bypass in frontend | Low | Critical | Server-side enforcement as primary defense |
| Beta expiry notifications not sent | Medium | Medium | Monitoring + manual fallback notification system |
| Trial-to-paid conversion fails | Low | High | Manual conversion process as backup |

---

### 12.2 Contingency Plans

**If credit tracking fails:**
- Disable credit-gated features temporarily
- Investigate transaction logs
- Manually reconcile accounts

**If trial downgrade fails:**
- Manual SQL script to downgrade expired trials
- Notification to affected users

**If beta discount not applied:**
- Refund difference to affected accounts
- Audit pricing calculation logic

---

## 13. Appendix

### 13.1 Credit Costs Reference

| Action | Credit Cost | API Endpoint |
|--------|-------------|--------------|
| View signal | 0 | `/api/signals/{id}` |
| Alert trigger | 1 | `/api/alerts` |
| Intelligence brief | 50 | `/api/briefs` |
| On-demand synthesis | 100 | `/api/synthesis` |
| API batch pull | 25 | `/api/v1/batch` |
| Deep historical query | 200 | `/api/signals/historical` |

---

### 13.2 Tier Feature Matrix (Full)

| Feature | Explorer | Growth | Mid-Market | Enterprise |
|---------|----------|--------|------------|------------|
| **Continuous Signals** | Limited (50/month) | Full (unlimited) | Full | Full |
| **On-Demand Synthesis** | ❌ | Limited (5/month) | Full (50/month) | Full (unlimited) |
| **API Access** | ❌ | Yes (rate limited) | Yes (standard) | Yes (priority) |
| **Historical Depth** | 3 months | 12 months | 3-5 years | Full archive |
| **Freshness SLA** | 48h | 24h | 6-12h | <6h + SLA-backed |
| **Compliance Modules** | ❌ | Limited (1 region) | Yes (3 regions) | Full (all regions) |
| **Custom Contracts** | ❌ | Limited (no upload) | Yes (upload enabled) | Yes + AI parsing |
| **Private Signal Store** | ❌ | ❌ | ❌ | Yes |
| **Dedicated Support** | Community | Email | Priority email | Phone + dedicated CSM |
| **Users** | 1 | 5 | 25 | Unlimited |
| **Monthly Credits** | 0 | 5,000 | 25,000 | 100,000 |

---

### 13.3 Database ERD

```
┌─────────────┐         ┌──────────────┐
│  accounts   │────────<│    users     │
│             │         │              │
│ pricing_tier│         │ role         │
│ is_beta     │         │              │
│ credits_*   │         └──────────────┘
│             │
│             │         ┌──────────────────────┐
│             │────────<│ credit_transactions  │
│             │         │                      │
│             │         │ action_type          │
│             │         │ credits_consumed     │
└─────────────┘         └──────────────────────┘
       │
       │                ┌──────────────────┐
       └───────────────<│ beta_accounts    │
                        │                  │
                        │ beta_end_date    │
                        │ notified_*       │
                        └──────────────────┘
```

---

## Document Control

**Prepared By:** AI Assistant
**Reviewed By:** [Engineering Lead]
**Approved By:** [Product Owner]
**Last Updated:** February 15, 2026

---

## Next Steps

1. **Engineering Review**: Schedule walkthrough of this plan with backend/frontend leads
2. **Estimation Refinement**: Validate 14-day timeline estimate
3. **Dependency Check**: Ensure Stripe integration timeline aligns
4. **Communication Plan**: Prepare user-facing documentation for gating system
5. **Staging Environment**: Provision staging environment for migration testing

---

**Questions? Contact:** [Engineering Team]
