Below is the **correct master document structure** — written as a permanent system specification with Beta layered into it.

This is what you give to engineering.

---

# ESIP

# Master Feature Gating & Pricing System Specification

**Version:** 1.0
**Status:** Core System Architecture
**Scope:** Permanent Gating + Pricing Engine + 3-Month Discounted Beta Overlay

---

# 1. Document Purpose

This document defines:

* The permanent feature gating architecture
* The permanent pricing system
* The credit engine
* Reverse trial mechanics
* Billing logic
* Role-based access controls
* Beta discount overlay (temporary)
* Company-level pricing mode switching

This is the core system specification — not a beta-only document.

Beta is implemented as a pricing modifier layer.

---

# 2. System Philosophy

The system must support:

1. Permanent tier-based gating
2. Usage-based credit scaling
3. Enterprise modules
4. Reverse trial onboarding
5. Beta discount overlay
6. Toggle between Beta & Standard pricing
7. Clean transition from Beta → Standard pricing

The architecture must be modular.

Beta must not alter core gating logic.

---

# 3. Core Pricing & Gating Architecture (Permanent System)

Feature gating is enforced across 4 independent axes:

---

## Axis 1 — Tier-Based Feature Access

Each account is assigned a `pricing_tier`.

Possible values:

```
explorer
growth
mid_market
enterprise
```

Feature access checks must reference `pricing_tier`.

Example:

```
if pricing_tier == "growth" or higher:
    allow_api_access()
```

---

### Tier Feature Matrix (Permanent)

| Feature              | Explorer | Growth    | Mid-Market | Enterprise   |
| -------------------- | -------- | --------- | ---------- | ------------ |
| Continuous Signals   | Limited  | Full      | Full       | Full         |
| On-Demand Synthesis  | ❌        | Limited   | Full       | Full         |
| API Access           | ❌        | Yes       | Yes        | Yes          |
| Historical Depth     | 3 months | 12 months | 3–5 years  | Full archive |
| Freshness SLA        | 48h      | 24h       | 6–12h      | SLA-backed   |
| Compliance Modules   | ❌        | Limited   | Yes        | Full         |
| Custom Contracts     | ❌        | Limited   | Yes        | Yes          |
| Private Signal Store | ❌        | ❌         | ❌          | Yes          |

This matrix is permanent.

Beta does NOT change this matrix.

---

## Axis 2 — Credit Engine (Permanent)

Credits control compute-heavy actions.

Each account has:

```
credits_allocated_monthly
credits_consumed
credits_remaining
credit_overage_rate
```

Credits renew every billing cycle.

---

### Credit Consumption Rules

| Action                | Credit Cost |
| --------------------- | ----------- |
| View basic signal     | 0           |
| Alert trigger         | 1           |
| Intelligence brief    | 50          |
| On-demand synthesis   | 100         |
| API batch pull        | 25          |
| Deep historical query | 200         |

Credits are consumed regardless of beta or standard pricing.

Overages are billed at full credit rate.

Beta discount NEVER applies to credit overages.

---

## Axis 3 — Role-Based Access Control (Permanent)

Each user inside an account has a role:

```
owner
admin
analyst
viewer
```

Permissions layered on top of tier.

Example:

```
if role == viewer:
    disable_synthesis_button()
```

---

## Axis 4 — Enterprise Modules (Permanent)

Enterprise-only features gated via:

```
if pricing_tier == "enterprise":
    enable_private_signal_store()
```

Enterprise modules are never discounted via beta automation.

---

# 4. Reverse Trial (Permanent System Behavior)

Reverse trial is not beta-specific.

It is a permanent onboarding mechanism.

---

## 4.1 Reverse Trial Rules

All new accounts:

* Receive 30-day full Growth-level access
* Receive full signal packs
* Receive 10,000 credits
* API enabled
* No payment required during trial

This lasts one full month.

---

## 4.2 Trial Expiry Behavior

After 30 days:

If user subscribes:
→ convert to selected tier

If user does not subscribe:
→ auto-downgrade to Explorer (free limited mode)

Important:
Credits reset only if subscription starts.

Trial credits do NOT roll over.

---

# 5. Pricing Engine (Permanent)

Standard pricing is stored as:

```
standard_price_explorer
standard_price_growth
standard_price_mid_market
standard_price_enterprise
```

This is the baseline pricing.

---

# 6. Beta Overlay (Temporary Layer)

Beta is implemented as a pricing modifier.

Beta does NOT modify:

* Feature gating
* Credit costs
* Enterprise modules
* Reverse trial logic

It modifies:

* Subscription base price only

---

## 6.1 Company-Level Beta Toggle

System must include:

```
global_pricing_mode:
    beta
    standard
```

Admin dashboard must allow manual switching.

When:

```
global_pricing_mode == beta:
    apply_beta_discount()
```

---

## 6.2 Account-Level Beta Flag

Each account stores:

```
is_beta_account: boolean
beta_start_date
beta_end_date
beta_discount_percent
```

This allows:

* Mixed-mode operation
* Manual overrides
* Gradual beta phase-out

---

## 6.3 Beta Pricing Logic

```
if is_beta_account == true AND current_date < beta_end_date:
    subscription_price = standard_price * 0.5
else:
    subscription_price = standard_price
```

Credit overage rate is NOT discounted.

---

# 7. Beta Timeline Rules

Beta duration:

* 90 days per account

At `beta_end_date`:

System must:

1. Notify user 14 days before expiration
2. Show upcoming standard price
3. Allow downgrade
4. Auto-transition to standard pricing if not canceled

No silent changes.

---

# 8. Credit Renewal & Reverse Trial Clarification

You specified:

> Reversal plan is a whole month before it renews the credit.

Correct implementation:

* Trial period: 30 days
* Trial credits expire at day 30
* If user subscribes:
  → Subscription cycle starts
  → Monthly credits allocated on billing date

Example timeline:

Day 0: Trial begins
Day 30: Trial ends
Day 30: Subscription activated
Day 30: Credits allocated for Month 1
Day 60: Next credit renewal

Credits are always tied to billing cycle.

---

# 9. Manual Pricing Mode Switching

System must support:

Admin Action:

```
switch_global_pricing_mode(beta | standard)
```

When switching to standard:

* New accounts default to standard pricing
* Existing beta accounts retain beta until expiration
* No retroactive price changes

---

# 10. Data Model Requirements

Account Object:

```
account_id
pricing_tier
is_beta_account
beta_start_date
beta_end_date
trial_status
billing_cycle_start
credits_allocated
credits_consumed
```

System Object:

```
global_pricing_mode
standard_price_table
beta_discount_percent
```

---

# 11. Permanent System Behavior After Beta Ends

When global_pricing_mode switches to standard:

* Reverse trial continues permanently
* Discount layer disabled
* All new accounts pay full price
* Existing beta accounts complete cycle
* No system restructuring required

Beta removal must not require code rewrite.

---

# 12. What This Document Covers

This document defines:

* Permanent feature gating
* Permanent pricing engine
* Credit system
* Reverse trial (30-day)
* Beta overlay architecture
* Company-level pricing control
* Account-level discount control
* Transition logic

This is the master gating system.

Beta is just a temporary multiplier.

---

# 13. What This Document Does NOT Cover

* Signal detection logic
* Infrastructure scaling
* ML architecture
* Signal contract definitions

Those belong to core product documentation.

---

# Final Clarification

Your system must behave like this:

Core Engine → Always Active
Reverse Trial → Always Active
Pricing Engine → Always Active
Beta → Optional Overlay
Credits → Always Real
Gating → Always Tier-Based

Beta must feel like a pricing event, not a product change.

---
