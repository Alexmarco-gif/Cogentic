# Cogent Platform — Technical Audit & Engineering Fix Plan

> **Date**: February 16, 2026
> **Scope**: Full-stack audit (backend, frontend, infrastructure, data layer)
> **Target**: Production readiness for 10,000+ users

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [System Flow Diagram](#2-system-flow-diagram)
3. [Phase 1 — Show-Stoppers](#phase-1--show-stoppers-fix-immediately)
4. [Phase 2 — Security Critical](#phase-2--security-critical-fix-before-production)
5. [Phase 3 — Data Integrity](#phase-3--data-integrity-fix-before-real-data-ingestion)
6. [Phase 4 — Performance & Reliability](#phase-4--performance--reliability)
7. [Phase 5 — Code Quality & Maintainability](#phase-5--code-quality--maintainability)
8. [Full Issue Registry](#full-issue-registry)
9. [Refactoring Recommendations](#refactoring-recommendations)
10. [Scalability Recommendations](#scalability-recommendations)

---

## 1. Architecture Overview

**Cogent** is an AI-powered market intelligence platform with a three-tier architecture:

| Layer | Technology | Role |
|-------|-----------|------|
| **Frontend** | Next.js 14 (App Router) + Tailwind + Auth0 SDK | SSR/CSR SPA, handles auth flow, renders dashboards |
| **Backend API** | FastAPI (async) + SQLAlchemy 2.0 + Pydantic v2 | REST API, JWT auth, business logic, AI orchestration |
| **Workers** | RQ (Redis Queue) + Python | Background jobs: signal acquisition, document analysis, ML training |
| **Data Stores** | PostgreSQL (Neon) + pgvector, Redis, Neo4j | Relational data, caching/queues, knowledge graph |

**Layered Architecture with Repository Pattern:**

```
Routes (api/v1/) → Services (services/) → Repositories (repositories/) → Models (models/) → PostgreSQL
                 ↘ AI layer (ai/)       → OpenAI API
                 ↘ ML layer (ml/)       → ONNX Runtime (local inference)
                 ↘ Signals (signals/)   → External data sources (RSS, APIs)
```

**Key Subsystems:**

- **Signal Intelligence Pipeline**: Fetchers → Processors → Dedup → Scoring → Storage
- **Causal Knowledge Graph**: Entity resolution → Relationship mapping → Causal inference (Neo4j + pgvector)
- **Intelligence Moat**: Feedback loops → Prediction backtesting → Replicability testing → Moat metrics
- **Chat Agent**: OpenAI-powered chat with tool calling, RAG over signals/briefs
- **Pricing & Feature Gating**: Tier-based access (Free → Starter → Professional → Enterprise)

---

## 2. System Flow Diagram

```
User Browser
    │
    ├─── Auth0 Login ──→ Auth0 ──→ JWT issued
    │
    ▼
Next.js Frontend (localhost:3000)
    │ fetch('/api/v1/...')        ← NO proxy configured (CORS issue)
    ▼
FastAPI Backend (localhost:8000)
    │
    ├── CORS Middleware (outermost)
    ├── RequestID Middleware
    ├── Metrics Middleware (Prometheus)
    ├── JWT Middleware (Auth0 JWKS validation)
    │          │
    │          ├── Token valid → request.state.token_payload
    │          └── Token invalid → 401
    │
    ├── Rate Limiter (slowapi) ← BROKEN: in-memory, never reads user ID
    │
    ▼
API v1 Router (146 endpoints)
    │
    ├── get_current_user() dependency → DB lookup → AuthContext
    │          │
    │          └── Auto-creates user if not found ← BUG: garbage email
    │
    ├── Service Layer ← Some routes bypass this (direct DB access)
    │      │
    │      ├── OpenAI API (chat, synthesis, embeddings)
    │      ├── ONNX Runtime (scoring, anomaly detection)
    │      └── Neo4j (causal graph queries)
    │
    ├── Repository Layer → SQLAlchemy AsyncSession → PostgreSQL (Neon)
    │
    └── Background Jobs → Redis Queue → RQ Worker ← BROKEN: won't start
              │
              └── Signal acquisition, document analysis, ML training
```

---

## Phase 1 — Show-Stoppers (Fix Immediately)

> These defects prevent basic functionality from working. **Nothing else should be attempted until Phase 1 is complete.**

### 1.1 Worker Cannot Start — `ImportError`

- **File**: `worker.py` (line 29)
- **Problem**: Imports `default_queue`, `high_priority_queue`, `low_priority_queue` from `backend.queue` — these names don't exist. The module uses lazy initialization via `_get_queue()` and private globals.
- **Impact**: **All background jobs are non-functional.** Signal acquisition, document analysis, ML training, brief generation — none execute.
- **Fix**:

In `backend/queue.py`, add public accessors at module level:

```python
# Add after the _get_queue function definition

# Public queue accessors for worker.py
def get_high_priority_queue() -> Queue:
    return _get_queue("high")

def get_default_queue() -> Queue:
    return _get_queue("default")

def get_low_priority_queue() -> Queue:
    return _get_queue("low")

# Convenience properties for backward compatibility
high_priority_queue = property(lambda self: _get_queue("high"))
default_queue = property(lambda self: _get_queue("default"))
low_priority_queue = property(lambda self: _get_queue("low"))
```

Then update `worker.py` to use the functions:

```python
# Replace:
from backend.queue import default_queue, high_priority_queue, low_priority_queue

# With:
from backend.queue import get_default_queue, get_high_priority_queue, get_low_priority_queue
```

And update the queue references in `main()`:

```python
if args.queue == "high":
    queues = [get_high_priority_queue()]
elif args.queue == "default":
    queues = [get_default_queue()]
elif args.queue == "low":
    queues = [get_low_priority_queue()]
else:
    queues = [get_high_priority_queue(), get_default_queue(), get_low_priority_queue()]
```

- **Effort**: 15 min
- **Verification**: Run `python worker.py --burst` — should start without import errors.

---

### 1.2 Model Router Casing Crash — `AttributeError`

- **File**: `backend/ai/model_router.py` (line 76)
- **Problem**: Uses `settings.OPENAI_API_KEY` (uppercase). Rest of codebase uses `settings.openai_api_key` (lowercase). Pydantic Settings uses lowercase attribute names.
- **Impact**: Model router crashes at instantiation → chat, synthesis, and any AI routing fails.
- **Fix**:

```python
# Replace:
self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

# With:
self.client = AsyncOpenAI(api_key=settings.openai_api_key)
```

- **Effort**: 2 min
- **Verification**: Import and instantiate `ModelRouter` in a Python shell.

---

### 1.3 Frontend CreditDisplay Broken Import

- **File**: `frontend/components/CreditDisplay.tsx` (line 4)
- **Problem**: Imports `useCreditWarning` from `@/lib/hooks/useFeatureGate` — this export doesn't exist. The correct hook is `useCredits` from `@/lib/hooks/useCredits`.
- **Impact**: CreditDisplay component crashes at runtime.
- **Fix**:

```tsx
// Replace:
import { useCreditWarning } from '@/lib/hooks/useFeatureGate';

// With:
import { useCredits } from '@/lib/hooks/useCredits';
```

Update the destructured variables to match the `useCredits` hook's return type.

- **Effort**: 5 min
- **Verification**: `npm run build` should compile without errors.

---

### 1.4 PricingProvider Not Mounted

- **File**: `frontend/app/layout.tsx`
- **Problem**: `PricingProvider` is never mounted in the component tree. All feature-gating components (`FeatureGate`, `BetaBanner`, `CreditDisplay`, `UpgradePrompt`) call `usePricing()` which throws because there's no `PricingProvider` ancestor.
- **Impact**: Entire dashboard unusable if any pricing component is rendered.
- **Fix**:

```tsx
import { PricingProvider } from '@/lib/contexts/PricingContext';

// In the layout JSX:
<UserProvider>
  <PricingProvider>
    {children}
  </PricingProvider>
</UserProvider>
```

- **Effort**: 10 min
- **Verification**: Dashboard loads without "usePricing must be used within PricingProvider" errors.

---

### 1.5 Missing Model Exports in `__init__.py`

- **File**: `backend/models/__init__.py`
- **Problem**: `BetaAccount`, `CreditTransaction`, `FeatureGate`, `PricingConfig` are not imported. Alembic only imports `from backend.models import Base`, so autogenerate won't detect these tables.
- **Impact**: Schema drift between code and database. Alembic migrations silently skip these 4 models.
- **Fix**:

Add imports and `__all__` entries:

```python
from backend.models.beta_account import BetaAccount
from backend.models.credit_transaction import CreditTransaction
from backend.models.feature_gate import FeatureGate
from backend.models.pricing_config import PricingConfig

# Add to __all__:
"BetaAccount",
"CreditTransaction",
"FeatureGate",
"PricingConfig",
```

- **Effort**: 5 min
- **Verification**: `alembic check` reports no pending autogenerate changes for these tables.

---

### 1.6 Missing npm Dependencies

- **File**: `frontend/package.json`
- **Problem**: `lucide-react` and `@headlessui/react` are used by `BetaBanner`, `CreditDisplay`, `UpgradePrompt`, `PricingModeToggle` but not listed in dependencies.
- **Impact**: Build fails.
- **Fix**:

```bash
cd frontend
npm install lucide-react @headlessui/react
```

- **Effort**: 2 min
- **Verification**: `npm run build` completes.

---

## Phase 2 — Security Critical (Fix Before Production)

> These issues expose the system to real attacks when deployed publicly. **Do not deploy without completing Phase 2.**

### 2.1 Rate Limiter Uses In-Memory Storage

- **File**: `backend/auth/rate_limit.py` (line 73)
- **Problem**: `storage_uri="memory://"` means each worker process has independent counters. With N workers, effective rate limit = N × configured limit.
- **Impact**: Rate limiting is trivially bypassed by distributing requests across workers. No brute-force protection.
- **Fix**:

```python
from backend.config import get_settings

settings = get_settings()

limiter = Limiter(
    key_func=get_rate_limit_key,
    storage_uri=settings.redis_url,  # Shared Redis storage
)
```

- **Effort**: 30 min (including testing)

---

### 2.2 Rate Limit Key Reads Wrong Attribute

- **File**: `backend/auth/rate_limit.py` (line 32)
- **Problem**: Reads `request.state.auth` but JWT middleware sets `request.state.token_payload`. Auth context is always `None` → all users get IP-based anonymous rate limit (20/min).
- **Fix**:

```python
def get_rate_limit_key(request: Request) -> str:
    # Fix: read token_payload, not auth
    token_payload = getattr(request.state, "token_payload", None)
    if token_payload and hasattr(token_payload, "sub"):
        return f"user:{token_payload.sub}"
    # Fallback to IP
    return f"ip:{request.client.host if request.client else 'unknown'}"
```

- **Effort**: 15 min

---

### 2.3 Dashboard Route Unprotected in Frontend

- **File**: `frontend/middleware.ts` (line 26)
- **Problem**: `/dashboard/:path*` matcher is commented out.
- **Fix**:

```ts
export const config = {
  matcher: [
    '/api/protected/:path*',
    '/dashboard/:path*',  // Uncomment this line
  ],
};
```

- **Effort**: 2 min

---

### 2.4 Webhook Signature Verification Optional

- **File**: `frontend/app/api/webhooks/auth0/route.ts` (line 231)
- **Problem**: When `AUTH0_WEBHOOK_SECRET` is not set, accepts any payload without verification.
- **Fix**:

```ts
if (!webhookSecret) {
  if (process.env.NODE_ENV === 'production') {
    console.error('[WEBHOOK] CRITICAL: No webhook secret configured in production');
    return NextResponse.json(
      { error: 'Webhook verification not configured' },
      { status: 500 }
    );
  }
  console.warn('[WEBHOOK] ⚠️  No webhook secret - skipping verification (dev only)');
}
```

- **Effort**: 15 min

---

### 2.5 SQL Injection via f-string Interpolation

- **Files**: `backend/services/deep_search.py` (line 218), `backend/ai/synthesis.py` (line 207)
- **Problem**: User-controllable values interpolated directly into SQL via f-strings.
- **Fix**: Use parameterized queries with `:parameter` placeholders:

```python
# Replace:
conditions.append(f"(s.org_id IS NULL OR s.org_id = '{org_id}')")

# With:
conditions.append("(s.org_id IS NULL OR s.org_id = :org_id)")
params["org_id"] = str(org_id)
```

Apply the same pattern to all f-string SQL in both files.

- **Effort**: 30 min

---

### 2.6 API Keys Stored in Plaintext

- **Files**: `backend/repositories/api_key.py`, `backend/auth/dependencies.py` (line 393)
- **Problem**: API keys are compared by plaintext value, implying they're stored unhashed. If DB is compromised, all API keys are usable.
- **Fix**:
  1. On key creation: generate key, return plaintext to user, store `sha256(key)` in DB.
  2. On key lookup: hash the incoming key, query by hash.

```python
import hashlib

def hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()

# Creation:
key_plaintext = generate_api_key()
key_hash = hash_api_key(key_plaintext)
# Store key_hash in DB, return key_plaintext to user

# Lookup:
key_hash = hash_api_key(api_key)
api_key_model = await api_key_repo.get_by_hash(key_hash)
```

- **Effort**: 1 hr

---

### 2.7 Missing Auth/Role Checks on 13 Endpoints

The following endpoints allow any authenticated user to perform privileged operations:

| Endpoint | File | Required Fix |
|----------|------|-------------|
| `PATCH /contracts/{id}` | `backend/api/v1/contracts.py:100` | Add `require_permissions(["admin", "owner"])` |
| `DELETE /contracts/{id}` | `backend/api/v1/contracts.py:118` | Add `require_permissions(["admin", "owner"])` |
| `POST /contracts/{id}/fetch` | `backend/api/v1/contracts.py:128` | Add `require_permissions(["admin", "owner"])` |
| `POST /contracts/{id}/activate` | `backend/api/v1/contracts.py:154` | Add `require_permissions(["admin", "owner"])` |
| `POST /contracts/{id}/deactivate` | `backend/api/v1/contracts.py:167` | Add `require_permissions(["admin", "owner"])` |
| `PATCH /briefs/{id}/status` | `backend/api/v1/briefs.py:170` | Add role check |
| `POST /briefs/refresh-all` | `backend/api/v1/briefs.py:213` | Add `require_permissions(["admin", "owner"])` |
| `POST /moat/snapshots` | `backend/api/v1/moat.py:170` | Add `require_permissions(["admin", "owner"])` |
| `POST /moat/replicability/blind-test` | `backend/api/v1/moat.py:288` | Add admin check (consumes OpenAI credits) |
| `POST /recommendations/generate` | `backend/api/v1/recommendations.py:70` | Add admin check |
| `POST /entities` | `backend/api/v1/entities.py:98` | Add role check |
| `POST /entities/relationships` | `backend/api/v1/entities.py:175` | Add role check |
| `GET /monitoring/*` (all 7) | `backend/api/v1/monitoring.py` | Add `require_permissions(["admin", "owner"])` |

- **Effort**: 2 hrs

---

### 2.8 Auth Bypass Path Too Broad

- **File**: `backend/auth/middleware.py` (line 60)
- **Problem**: `request.url.path.startswith("/webhooks")` matches `/webhooksanything`.
- **Fix**:

```python
# Replace:
request.url.path.startswith("/webhooks")

# With:
request.url.path.startswith("/webhooks/")
```

- **Effort**: 2 min

---

### 2.9 Raw JWT Stored on Request State

- **File**: `backend/auth/middleware.py` (line 80)
- **Problem**: `request.state.raw_token = token` — if any middleware or error handler serializes `request.state`, the bearer token leaks into logs.
- **Fix**: Remove the line. No downstream code uses `request.state.raw_token`.
- **Effort**: 5 min

---

### 2.10 Add Security Headers to Next.js

- **File**: `frontend/next.config.js`
- **Fix**:

```js
const nextConfig = {
  // ... existing config
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
          { key: 'X-XSS-Protection', value: '1; mode=block' },
          {
            key: 'Strict-Transport-Security',
            value: 'max-age=63072000; includeSubDomains; preload',
          },
          {
            key: 'Content-Security-Policy',
            value: "default-src 'self'; script-src 'self' 'unsafe-eval' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' https://*.auth0.com",
          },
        ],
      },
    ];
  },
};
```

- **Effort**: 20 min

---

### 2.11 Webhook Error Response Leaks Internal Messages

- **File**: `frontend/app/api/webhooks/auth0/route.ts` (line 296)
- **Fix**:

```ts
// Replace:
return NextResponse.json(
  { error: 'Internal server error', message: error instanceof Error ? error.message : 'Unknown error' },
  { status: 500 }
);

// With:
return NextResponse.json(
  { error: 'Internal server error' },
  { status: 500 }
);
```

- **Effort**: 2 min

---

## Phase 3 — Data Integrity (Fix Before Real Data Ingestion)

> These issues cause data corruption, orphan records, or silent data loss over time.

### 3.1 Add Foreign Key Constraints to `AIUsageLog`

- **File**: `backend/models/ai_usage_log.py` (line 17-18)
- **Problem**: `user_id` and `org_id` are bare UUID columns with no FK constraint. Orphan records can accumulate freely.
- **Fix**: Create an Alembic migration:

```python
op.create_foreign_key(
    'fk_ai_usage_logs_user_id', 'ai_usage_logs', 'users',
    ['user_id'], ['id'], ondelete='SET NULL'
)
op.create_foreign_key(
    'fk_ai_usage_logs_org_id', 'ai_usage_logs', 'organizations',
    ['org_id'], ['id'], ondelete='CASCADE'
)
```

- **Effort**: 30 min

---

### 3.2 Add Missing Indexes on Foreign Keys

Create a migration adding indexes to these unindexed FK columns:

| Table | Column | Why |
|-------|--------|-----|
| `regulatory_rules` | `event_id` | FK to `regulatory_events` — JOINs will full-scan |
| `regulatory_impacts` | `event_id` | FK to `regulatory_events` |
| `regulatory_impacts` | `rule_id` | FK to `regulatory_rules` |
| `regulatory_impacts` | `entity_id` | FK to `entities` |
| `ai_jobs` | `user_id` | FK to `users` |
| `credit_transactions` | `user_id` | FK to `users` |
| `regulatory_events` | `source_signal_id` | FK to `signals` |
| `regulatory_events` | `source_event_id` | Self-referential FK |
| `regulatory_events` | `created_by` | FK to `users` |
| `regulatory_rules` | `created_by` | FK to `users` |
| `regulatory_impacts` | `recorded_by` | FK to `users` |

```python
# In migration:
op.create_index('ix_regulatory_rules_event_id', 'regulatory_rules', ['event_id'])
op.create_index('ix_regulatory_impacts_event_id', 'regulatory_impacts', ['event_id'])
op.create_index('ix_regulatory_impacts_rule_id', 'regulatory_impacts', ['rule_id'])
op.create_index('ix_regulatory_impacts_entity_id', 'regulatory_impacts', ['entity_id'])
op.create_index('ix_ai_jobs_user_id', 'ai_jobs', ['user_id'])
op.create_index('ix_credit_transactions_user_id', 'credit_transactions', ['user_id'])
# ... etc
```

- **Effort**: 20 min

---

### 3.3 Add Missing Unique Constraints

| Table | Columns | Risk Without |
|-------|---------|-------------|
| `signal_scores` | `(signal_id, score_type)` | Duplicate scores per signal |
| `ml_model_registry` | `(model_name, model_version)` | Duplicate model registrations |
| `entity_aliases` | `(entity_id, alias_name)` | Duplicate aliases |
| `causal_edges` | `(cause_event_id, effect_event_id, relationship_label)` | Duplicate causal edges |
| `moat_metric_snapshots` | `snapshot_date` | Multiple snapshots per date |

```python
# In migration:
op.create_unique_constraint(
    'uq_signal_scores_signal_type', 'signal_scores',
    ['signal_id', 'score_type']
)
# ... etc for each
```

- **Effort**: 30 min

---

### 3.4 Fix Credit Consumption Race Condition

- **File**: `backend/services/credit_service.py` (line 96)
- **Problem**: `check_sufficient_credits()` and `consume_credits()` are separate non-atomic calls. Concurrent requests can both pass the check.
- **Fix**: Use `SELECT ... FOR UPDATE` or a Redis-based atomic decrement:

```python
async def consume_credits_atomic(self, org_id: UUID, amount: int, action: str) -> bool:
    """Atomically check and consume credits."""
    async with self.db.begin():
        result = await self.db.execute(
            select(Organization)
            .where(Organization.id == org_id)
            .with_for_update()
        )
        org = result.scalar_one_or_none()
        if not org or org.credits_remaining < amount:
            return False
        org.credits_remaining -= amount
        # Record transaction
        txn = CreditTransaction(org_id=org_id, amount=-amount, action_type=action)
        self.db.add(txn)
        return True
```

- **Effort**: 1 hr

---

### 3.5 Fix Idempotency Race Condition

- **File**: `backend/middleware/idempotency.py` (line 77)
- **Problem**: `GET` → execute → `SET` is not atomic. Concurrent requests with same key both execute.
- **Fix**: Use `SET NX` to atomically claim the idempotency key before execution:

```python
# Step 1: Try to claim the key
claimed = await redis.set(redis_key, "processing", nx=True, ex=ttl)
if not claimed:
    # Another request is processing — wait and return cached result
    for _ in range(50):  # Wait up to 5 seconds
        await asyncio.sleep(0.1)
        cached = await redis.get(redis_key)
        if cached and cached != "processing":
            return json.loads(cached)
    raise HTTPException(409, "Request is being processed")

# Step 2: Execute
result = await func(*args, **kwargs)

# Step 3: Store result
await redis.set(redis_key, json.dumps(result), ex=ttl)
```

Also: scope the key to user/org — `idempotency:{org_id}:{key}`.

- **Effort**: 1 hr

---

### 3.6 Fix SLO Metrics Data Loss

- **File**: `backend/services/slo_metrics.py` (line 45)
- **Problem**: `redis.zadd(key, {str(duration_ms): timestamp})` — duplicate `duration_ms` values overwrite each other in the sorted set, destroying data.
- **Fix**:

```python
# Use unique member (timestamp:random_suffix) with duration as the score
import uuid
member = f"{timestamp}:{uuid.uuid4().hex[:8]}"
redis.zadd(key, {member: duration_ms})  # Score = duration for percentile calc
```

- **Effort**: 30 min

---

### 3.7 Add Org-Scoping to Multi-Tenant Queries

Currently, these resources are globally visible to all authenticated users (no org filtering):

| Resource | Repository | Fix |
|----------|-----------|-----|
| Signals | `signal.py` | Add `org_id` filter to `list()`, `get()` |
| Signal Contracts | `signal_contract.py` | Add `org_id` filter |
| Entities | `entity.py` | Add `org_id` or industry-based scoping |
| Causal Events | Service-level | Filter by org's signals |
| Feedback | `user_feedback` | Filter by `org_id` on reads |

Compare with `documents.py` and `api_keys.py` which correctly scope by `org_id` in URL path.

- **Effort**: 4 hrs

---

## Phase 4 — Performance & Reliability

> These issues cause degraded performance or system instability under load.

### 4.1 Replace Sync Redis with Async Redis (5 Services)

**Problem**: These services use the synchronous `get_redis_client()` inside async FastAPI handlers, blocking the event loop:

| File | Calls |
|------|-------|
| `backend/services/cost_tracker.py` | `redis.incr()`, `redis.hincrbyfloat()` |
| `backend/services/slo_metrics.py` | `redis.zadd()`, `redis.zrangebyscore()` |
| `backend/services/cache_metrics.py` | `redis.incr()`, `redis.expire()` |
| `backend/services/circuit_breaker.py` | `redis.get()`, `redis.incr()`, `redis.set()` |
| `backend/middleware/idempotency.py` | `redis.get()`, `redis.setex()` |

**Fix**: Replace `get_redis_client()` with `get_redis()` (async), make all methods `async`, and `await` all Redis calls.

- **Effort**: 3 hrs

---

### 4.2 Add JWKS Cache Lock

- **File**: `backend/auth/jwks.py` (line 56)
- **Fix**:

```python
class JWKSClient:
    def __init__(self, ...):
        # ...
        self._lock = asyncio.Lock()

    async def get_signing_key(self, kid: str) -> Any:
        if self._is_cache_valid() and kid in self._keys:
            return self._keys[kid]
        async with self._lock:
            # Double-check after acquiring lock
            if self._is_cache_valid() and kid in self._keys:
                return self._keys[kid]
            await self._fetch_jwks()
            if kid not in self._keys:
                raise InvalidTokenError(f"Unknown key ID: {kid}")
            return self._keys[kid]
```

- **Effort**: 30 min

---

### 4.3 Fix N+1 Queries in Bulk Endpoints

- **File**: `backend/api/v1/bulk.py` (lines 100, 141, 168)
- **Problem**: Loops through IDs one at a time. Up to 100 individual DB queries per request.
- **Fix**:

```python
# Replace:
for sid in body.signal_ids:
    signal = await repo.get(sid)
    if signal:
        results.append(signal)

# With:
results = await repo.get_many(body.signal_ids)

# In repository, add:
async def get_many(self, ids: list[UUID]) -> list[Signal]:
    result = await self.db.execute(
        select(Signal).where(Signal.id.in_(ids))
    )
    return list(result.scalars().all())
```

- **Effort**: 1 hr

---

### 4.4 Cache Entity Graph in Influence Mapping

- **File**: `backend/services/influence_mapping.py`
- **Problem**: `_build_entity_graph()` loads the *entire* entity relationship table and builds a NetworkX graph — called once per entity in `identify_key_influencers()`.
- **Fix**:

```python
import functools
import time

_graph_cache = None
_graph_cache_time = 0
GRAPH_CACHE_TTL = 300  # 5 minutes

async def _get_or_build_graph(self, db) -> nx.DiGraph:
    global _graph_cache, _graph_cache_time
    if _graph_cache and (time.time() - _graph_cache_time) < GRAPH_CACHE_TTL:
        return _graph_cache
    graph = await self._build_entity_graph(db)
    _graph_cache = graph
    _graph_cache_time = time.time()
    return graph
```

- **Effort**: 1 hr

---

### 4.5 Sanitize Prometheus Endpoint Labels

- **File**: `backend/main.py` (line 79)
- **Problem**: `endpoint = request.url.path` — raw paths with UUIDs create unbounded label cardinality.
- **Fix**:

```python
import re

def sanitize_endpoint(path: str) -> str:
    """Replace UUIDs and numeric IDs with placeholders."""
    path = re.sub(
        r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
        '{id}', path
    )
    path = re.sub(r'/\d+', '/{id}', path)
    return path

# In MetricsMiddleware:
endpoint = sanitize_endpoint(request.url.path)
```

- **Effort**: 30 min

---

### 4.6 Add Error Boundaries to Frontend

Create these files:

**`frontend/app/error.tsx`**:
```tsx
'use client';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-center">
        <h2 className="text-2xl font-bold text-gray-900">Something went wrong</h2>
        <p className="mt-2 text-gray-600">{error.message}</p>
        <button
          onClick={reset}
          className="mt-4 rounded bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
        >
          Try again
        </button>
      </div>
    </div>
  );
}
```

**`frontend/app/global-error.tsx`**:
```tsx
'use client';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html>
      <body>
        <div style={{ padding: '2rem', textAlign: 'center' }}>
          <h2>Something went wrong</h2>
          <button onClick={reset}>Try again</button>
        </div>
      </body>
    </html>
  );
}
```

- **Effort**: 30 min

---

### 4.7 Fix Auto-Created User Email

- **File**: `backend/auth/dependencies.py` (line 225)
- **Problem**: Email parsed from `sub.split("|")[-1]` → gives opaque ID, not email. `payload.email` is available but unused.
- **Fix**:

```python
# Replace:
email = (
    payload.sub.split("|")[-1]
    if "|" in payload.sub
    else f"{payload.sub}@unknown.com"
)

# With:
email = payload.email or f"{payload.sub}@placeholder.cogent.ai"
```

- **Effort**: 10 min

---

## Phase 5 — Code Quality & Maintainability

> These improve long-term maintainability, developer experience, and audit-ability.

### 5.1 Consolidate Auth Patterns

**Current state**: 5 different auth patterns used interchangeably:

1. `Depends(get_current_user)` — most common
2. `Depends(require_permissions([...]))` — admin, influence, regulatory
3. `require_role(auth, "admin")` — imperative in-function guard
4. `require_admin(auth)` / `require_owner(auth)` — imperative helper
5. Inline `if auth.role not in ("admin", "owner")` — ad-hoc

**Target**: Standardize on 2 patterns:
- **Pattern A** — `Depends(get_current_user)` for "any authenticated user"
- **Pattern B** — `Depends(require_permissions(["admin", "owner"]))` for role-gated

Remove `require_role()`, `require_admin()`, `require_owner()`, and all inline checks.

- **Effort**: 4 hrs

---

### 5.2 Merge Duplicate Circuit Breakers

- `backend/services/circuit_breaker.py` — sync Redis, `.call()` method
- `backend/ai/circuit_breaker.py` — async Redis, `.async_call()`, raises `HTTPException(503)`

**Action**: Keep the `ai/` version (async-capable). Update all consumers to use it. Delete the sync version.

- **Effort**: 2 hrs

---

### 5.3 Merge Model Router + Model Selector

- `backend/ai/model_router.py` — routes by task type
- `backend/ai/model_selector.py` — routes by complexity score

**Action**: Merge into a single `ModelRouter` that considers both task type and complexity. Unify the pricing tables.

- **Effort**: 2 hrs

---

### 5.4 Add Response Models to ~40 Endpoints

Many endpoints return raw `dict` instead of Pydantic response models:

| File | Affected Endpoints |
|------|-------------------|
| `admin.py` | 5 of 6 |
| `auth.py` | All 3 |
| `monitoring.py` | All 7 |
| `moat.py` | 12 of 13 |
| `entities.py` | 3 |
| `feedback.py` | 2 |
| `regulatory.py` | 7 |

**Why it matters**: No schema validation on responses, no consistent error shape, incomplete OpenAPI docs.

- **Effort**: 8 hrs

---

### 5.5 Extract Regulatory Repository

- **File**: `backend/api/v1/regulatory.py`
- **Problem**: 7+ endpoints do raw `db.add()`, `db.execute(select(...))` inline in route handlers.
- **Action**: Create `backend/repositories/regulatory.py` and move all DB access there.
- **Effort**: 3 hrs

---

### 5.6 Standardize Mixin Usage

These models don't use the standard `UUIDMixin`/`TimestampMixin` from `base.py`:

| Model | Current | Fix |
|-------|---------|-----|
| `RegulatoryEvent` | Manual UUID + timestamps | Use `UUIDMixin`, `TimestampMixin` |
| `RegulatoryRule` | Manual UUID + timestamps | Same |
| `RegulatoryImpact` | Manual UUID + timestamps | Same |
| `RegulatoryPattern` | Manual UUID + timestamps | Same |
| `FeatureGate` | Integer PK | Convert to UUID |
| `PricingConfig` | Integer PK | Convert to UUID |
| `CreditTransaction` | UUID only, no `updated_at` | Add `TimestampMixin` |
| `BetaAccount` | UUID only, no `updated_at` | Add `TimestampMixin` |

- **Effort**: 2 hrs (plus migration)

---

### 5.7 Replace Deprecated `datetime.utcnow()`

`datetime.utcnow()` was deprecated in Python 3.12. Used in ~10 files:

- `backend/auth/jwks.py`
- `backend/auth/utils.py`
- `backend/job_handlers.py`
- `backend/middleware/cost_tracking.py`
- `backend/services/pricing_service.py`
- `backend/services/trial_service.py`
- `backend/services/beta_lifecycle_service.py`
- `backend/services/cost_tracker.py`

**Fix**: Replace with `datetime.now(timezone.utc)` everywhere:

```python
from datetime import datetime, timezone

# Replace:
datetime.utcnow()

# With:
datetime.now(timezone.utc)
```

- **Effort**: 1 hr

---

### 5.8 Add Frontend API Proxy

- **File**: `frontend/next.config.js`
- **Problem**: No proxy/rewrites for API calls. Frontend fetches to `/api/v1/*` will fail if backend is on a different origin.
- **Fix**:

```js
const nextConfig = {
  // ... existing config
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: `${process.env.BACKEND_URL || 'http://localhost:8000'}/api/v1/:path*`,
      },
    ];
  },
};
```

- **Effort**: 15 min

---

### 5.9 Add Pagination to Unpaginated Endpoints

These list endpoints have no `skip`/`offset` parameter:

| Endpoint | File |
|----------|------|
| `GET /contracts/degraded` | `contracts.py:67` |
| `GET /feedback/predictions/accuracy` | `feedback.py:140` |
| `GET /moat/*` (all listing endpoints) | `moat.py` |
| `GET /regulatory/events` | `regulatory.py:132` (has `limit` but no `skip`) |
| `GET /regulatory/patterns` | `regulatory.py:490` |
| `GET /ml/runs` | `ml.py:93` |
| `GET /ml/registry` | `ml.py:110` |
| `GET /signals/trending` | `signals.py:49` |

Add standard pagination parameters:

```python
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    ...
):
```

- **Effort**: 3 hrs

---

### 5.10 Create Frontend `fetchWithAuth()` Utility

- **Problem**: No API calls include auth headers. No centralized API client.
- **Fix**: Create `frontend/lib/api.ts`:

```ts
export async function fetchWithAuth(
  url: string,
  options: RequestInit = {}
): Promise<Response> {
  const res = await fetch('/api/auth/token');
  const { accessToken } = await res.json();

  return fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      'Content-Type': 'application/json',
      Authorization: `Bearer ${accessToken}`,
    },
  });
}
```

Update all existing `fetch('/api/v1/...')` calls to use `fetchWithAuth`.

- **Effort**: 1 hr

---

## Full Issue Registry

### Critical Issues (8)

| ID | Component | Issue |
|----|-----------|-------|
| C1 | `worker.py:29` | Imports non-existent queue variables — worker crashes on startup |
| C2 | `rate_limit.py:73` | In-memory rate limits not shared across workers |
| C3 | `rate_limit.py:32` | Rate limit key reads wrong attribute — always falls back to IP |
| C4 | `deep_search.py:218`, `synthesis.py:207` | SQL injection via f-string interpolation |
| C5 | `frontend/middleware.ts:26` | Dashboard route matcher commented out — unprotected |
| C6 | `frontend/webhooks/auth0/route.ts:231` | Webhook signature verification skipped when no secret |
| C7 | `backend/models/__init__.py` | 4 models not imported — Alembic won't detect them |
| C8 | `slo_metrics.py:45` | Redis sorted set member collision — SLO data lost |

### High Issues (17)

| ID | Component | Issue |
|----|-----------|-------|
| H1 | `idempotency.py:77` | No atomicity — duplicate execution race condition |
| H2 | `idempotency.py:75` | Synchronous Redis blocks async event loop |
| H3 | `jwks.py:56` | No lock — thundering herd on JWKS refresh |
| H4 | `dependencies.py:225` | Auto-created user gets garbage email |
| H5 | `dependencies.py:296` | `get_optional_user` catches all exceptions silently |
| H6 | `credit_service.py:96` | Credit check+consume non-atomic — race condition |
| H7 | 13 API endpoints | Missing role/admin checks on sensitive operations |
| H8 | `CreditDisplay.tsx:4` | Imports non-existent export |
| H9 | `frontend/layout.tsx` | PricingProvider never mounted |
| H10 | Frontend (global) | Zero React Error Boundaries |
| H11 | `bulk.py:100` | N+1 query: loops through IDs one at a time |
| H12 | `influence_mapping.py` | Graph rebuilt per-entity — O(N×M) |
| H13 | Database (6 columns) | Missing indexes on FK columns |
| H14 | Database (5 constraints) | Missing unique constraints |
| H15 | `ai_usage_log.py:17` | No FK constraints on user_id/org_id |
| H16 | `model_router.py:76` | Settings attribute casing mismatch |
| H17 | Auth system-wide | 5 different auth patterns used interchangeably |

### Medium Issues (18)

| ID | Component | Issue |
|----|-----------|-------|
| M1 | `middleware.py:80` | Raw JWT stored on request.state |
| M2 | `middleware.py:60` | Webhook auth bypass too broad |
| M3 | `cost_tracking.py:87` | Daily cost key has no date — rolling window |
| M4 | `dependencies.py:225` | Auto-created user gets garbage email from `sub` |
| M5 | `queue.py:62` | No retry configuration for failed jobs |
| M6 | `queue.py` | No dead letter queue handling |
| M7 | `job_handlers.py:296` | Webhook handler: no retry, no HMAC, SSRF risk |
| M8 | `redis_client.py:25` | No connection health check or reconnect logic |
| M9 | `gating_service.py:67` | Role check is a `pass` — no-op |
| M10 | `feature_flags.py` | Plan enforcement is log-only — never blocks |
| M11 | ~10 files | Deprecated `datetime.utcnow()` usage |
| M12 | `trial_service.py`, `beta_lifecycle_service.py` | Direct `db.commit()` breaks unit-of-work |
| M13 | `embeddings.py` | Text truncation by chars not tokens |
| M14 | `guardrails.py` | Injection pattern too broad — false positives |
| M15 | `embedding_cache.py` | Lowercases text before hashing — wrong embeddings for proper nouns |
| M16 | `model_router.py`, `model_selector.py` | Duplicate model routing logic |
| M17 | `next.config.js` | No security headers, deprecated `domains` config |
| M18 | `frontend/webhooks/auth0/route.ts:283` | Re-reads consumed request body in error handler |

### Low Issues (15)

| ID | Component | Issue |
|----|-----------|-------|
| L1 | `dependencies.py:58` | `require_permissions` has phantom "analyst" role |
| L2 | `jwks.py:101` | `datetime.utcnow()` deprecated |
| L3 | `utils.py:94` | `TokenExpiredError` reports current time as `expired_at` |
| L4 | `dependencies.py:399` | API key prefix log leaks 1 char of secret |
| L5 | `feature_gating.py:15` | Unused `select` import |
| L6 | `feature_gating.py:168` | `check_credit_balance` is a complete no-op |
| L7 | `redis_client.py:68` | Sync Redis close() doesn't disconnect pool |
| L8 | `queue.py:68` | `func.__name__` crashes on string function refs |
| L9 | `beta_lifecycle_service.py` | Notifications use `print()` |
| L10 | `cache_metrics.py:34` | Redundant `_get_redis()` calls |
| L11 | `causal_intelligence.py` | Non-reproducible Granger causality (no random seed) |
| L12 | `prediction_backtest.py` | Self-referential validation inflates accuracy |
| L13 | `replicability_test.py` | `EmbeddingService()` instantiated without `db` param |
| L14 | `synthesis.py:402` | Silent `except Exception: pass` in intelligence enrichment |
| L15 | Organization + BetaAccount | Beta data duplicated across 2 tables |

---

## Refactoring Recommendations

| # | Area | Recommendation | Priority |
|---|------|----------------|----------|
| R1 | Auth patterns | Consolidate 5 patterns → 2 standard approaches | High |
| R2 | Circuit breaker | Merge sync + async implementations → single async | Medium |
| R3 | Model routing | Merge router + selector → single unified router | Medium |
| R4 | Redis clients | Eliminate all sync Redis usage in async code paths | High |
| R5 | Regulatory routes | Extract direct ORM access → `RegulatoryRepository` | Medium |
| R6 | Beta data | Remove beta fields from Organization; use BetaAccount only | Low |
| R7 | Entity aliases | Deprecate `Entity.aliases` JSONB; use `entity_aliases` table | Low |
| R8 | Response models | Add Pydantic models to ~40 endpoints returning `dict` | Medium |
| R9 | Duplicate endpoints | Merge/differentiate: trending signals, prediction accuracy, user profile, health, features | Medium |
| R10 | Lazy imports | Move deferred imports to module level; fix import graph | Low |
| R11 | Frontend API client | Create shared `fetchWithAuth()` with auto-attached bearer token | High |
| R12 | Mixin consistency | Refactor all models to use standard `UUIDMixin`/`TimestampMixin` | Low |
| R13 | Org-scoping | Add `org_id` filtering to signals, contracts, entities, causal data | High |

---

## Scalability Recommendations

| # | Recommendation | Why | At what scale it breaks |
|---|---------------|-----|------------------------|
| SC1 | Switch rate limiter to Redis backend | Per-process memory counters don't aggregate | Immediately (multi-worker) |
| SC2 | Add database read replicas | Write primary will saturate on read-heavy dashboards | ~5K concurrent users |
| SC3 | Request coalescing for JWKS | Thundering herd hits Auth0 every 30 min | ~100 concurrent requests |
| SC4 | Sanitize Prometheus labels | UUID cardinality → Prometheus OOM | ~1M unique URLs |
| SC5 | Add pagination everywhere | Unbounded queries OOM on large datasets | ~100K signals |
| SC6 | Batch embedding requests | Single-item OpenAI calls waste rate limit capacity | ~1K embeddings/day |
| SC7 | Neo4j connection pooling | Per-request connections saturate at ~50 concurrent | ~50 concurrent causal queries |
| SC8 | Cache causal graph | Full table scan + graph build per query | ~10K entity relationships |
| SC9 | Implement job retries | Failed jobs stay failed permanently | Any failed external API call |
| SC10 | WebSocket horizontal scaling | Verify Redis Pub/Sub works across instances | Multi-instance deployment |

---

## Effort Summary

| Phase | Description | Estimated Hours |
|-------|-------------|:-:|
| Phase 1 | Show-Stoppers | 0.5 |
| Phase 2 | Security Critical | 5 |
| Phase 3 | Data Integrity | 8 |
| Phase 4 | Performance & Reliability | 7 |
| Phase 5 | Code Quality | 25 |
| **Total** | | **~45 hrs** |

**Phases 1 and 2 are non-negotiable before any deployment.** The worker cannot start (C1), rate limiting is defeated (C2/C3), the dashboard is unprotected (C5), and SQL injection exists (C4).
