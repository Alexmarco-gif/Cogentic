Perfect.

We’ll design a **clean, scalable Stripe structure** that:

* Works immediately
* Supports reverse trial
* Supports 50% beta
* Supports credits
* Doesn’t over-engineer
* Can scale to mid-market & enterprise later

We’ll keep it V1 clean.

We’ll use **Stripe**.

---

# 🎯 Core Philosophy for V1

Stripe handles:

* Subscriptions
* Invoices
* Payment collection
* Discounts
* Renewal

Your system handles:

* Feature gating
* Credit allocation
* Credit consumption
* Trial logic

Stripe does not manage credits.

---

# 1️⃣ Stripe Product Structure (Exact Setup)

You will create:

## 4 Stripe Products (One per tier)

### 1. Explorer

* Product name: `ESIP Explorer`
* Price: $0
* Billing: Free
* No subscription required

---

### 2. Growth

* Product name: `ESIP Growth`
* Price: $X / month
* Billing: Monthly recurring

---

### 3. Mid-Market

* Product name: `ESIP Mid-Market`
* Price: $X / month
* Billing: Monthly recurring

---

### 4. Enterprise

* Product name: `ESIP Enterprise`
* Price: Custom
* Billing: Manual invoice (NOT checkout)

---

# 2️⃣ Stripe Price Configuration (Important)

For each paid tier (Growth + Mid-Market):

Create 1 recurring price:

```
Billing period: Monthly
Usage type: Licensed (not metered)
```

Do NOT enable metered billing yet.
Keep V1 simple.

---

# 3️⃣ Beta 50% Implementation (Simple + Clean)

Inside Stripe:

Create one coupon:

```
Name: beta_50
Type: Percentage
Amount: 50%
Duration: repeating
Duration: 3 months
```

When beta user subscribes:

* Apply coupon during checkout

Stripe automatically:

* Applies 50% discount
* Stops discount after 3 cycles
* Renews at full price

No backend complexity needed.

---

# 4️⃣ Reverse Trial Implementation (Correct Way)

Do NOT use Stripe’s free trial feature.

Instead:

Handle trial fully in your backend.

Flow:

User signs up →
You set:

```
account.status = "trial"
account.trial_end_date = now + 30 days
```

No Stripe object created yet.

When user clicks "Upgrade":

Then you create Stripe checkout session.

Why?

Because Stripe trial:

* Requires card upfront
* Complicates downgrade logic
* Creates billing confusion

You want frictionless reverse trial.

---

# 5️⃣ Exact Stripe Checkout Flow

When user subscribes:

Backend creates:

```
Stripe Checkout Session:
- customer_email
- line_items:
    price_id: growth_monthly
- discounts:
    coupon: beta_50 (if beta account)
- mode: subscription
```

Stripe returns checkout URL.

User completes payment.

---

# 6️⃣ Webhook Events You MUST Handle

Minimum required events:

### subscription.created

→ Set account.status = active
→ Assign pricing tier

### invoice.paid

→ Allocate credits
→ Reset credit counter

### invoice.payment_failed

→ Set status = past_due
→ Start grace period

### customer.subscription.deleted

→ Downgrade to Explorer

That’s enough for V1.

---

# 7️⃣ Credit Allocation Logic (Backend Only)

Stripe does NOT know about credits.

After `invoice.paid`:

```
if tier == growth:
    credits = 10,000

if tier == mid_market:
    credits = 50,000
```

Credits tied to billing cycle.

At renewal:
Reset credits.

---

# 8️⃣ Account State Machine (Simple Version)

Your system should support:

```
trial
active
past_due
suspended
canceled
```

Feature gating checks this FIRST.

---

# 9️⃣ Grace Period Logic (Very Important)

If payment fails:

Stripe retries automatically.

Your system:

```
invoice.payment_failed →
account.status = past_due
```

After 7 days without payment:

```
account.status = suspended
```

Then:

* Disable premium features
* Do not delete data

---

# 🔟 Enterprise Setup (V1 Simple)

For enterprise:

* Do NOT use checkout
* Create Stripe customer manually
* Send invoice via Stripe invoice API
* Mark account as:

```
billing_mode = manual
```

Credits allocated manually after invoice paid.

No automation needed initially.

---

# 11️⃣ What We Are NOT Doing in V1

We are NOT:

* Using metered billing
* Charging automatic overage
* Using multiple add-ons
* Creating credit top-up SKUs
* Complex usage tiers

That comes later.

---

# 12️⃣ Final Stripe Structure Summary

Stripe Dashboard Should Contain:

Products:

* ESIP Growth
* ESIP Mid-Market
* ESIP Enterprise

Prices:

* Growth Monthly
* Mid-Market Monthly

Coupon:

* beta_50 (3 months repeating)

Webhooks:

* 4 events configured

That’s it.

Clean.

Scalable.

---

# 13️⃣ Why This Works for Your Stage

You currently have:

* Feature gating built
* Credit system designed
* Reverse trial designed
* Beta discount plan

This Stripe setup:

* Supports beta cleanly
* Supports downgrade
* Supports credit reset
* Keeps backend in control
* Avoids early complexity

---

# 🚀 When You’re Ready for V2

Later you can add:

* Metered usage for overage
* Credit top-ups
* Annual plans
* Seat-based pricing
* Add-on modules
* API usage billing

But not yet.

---
# 📌 Key Takeaways
1. Use Stripe for subscriptions, not trials.
2. Handle trials and credits in your backend.
3. Keep Stripe structure simple: 4 products, 2 prices, 1 coupon.
4. Implement webhooks for core billing events.
5. Avoid over-engineering for V1; focus on clean, scalable design.
