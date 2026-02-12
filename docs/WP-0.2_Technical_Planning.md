# WP-0.2 — Technical Planning Deliverable

**Document Version:** 1.0
**Date:** 2026-02-10
**Status:** ✅ APPROVED
**Phase:** 0 — Strategy & Discovery
**Work Package:** WP-0.2 — Technical Planning

---

## Table of Contents

1. [Database Schema Design](#1-database-schema-design)
2. [API Contract Design](#2-api-contract-design)
3. [AI & ML Architecture](#3-ai--ml-architecture)
4. [Signal Acquisition Architecture](#4-signal-acquisition-architecture)
5. [Frontend Architecture](#5-frontend-architecture)
6. [Infrastructure & DevOps](#6-infrastructure--devops)
7. [Security & Compliance](#7-security--compliance)
8. [Architecture Diagram](#8-architecture-diagram)
9. [Cost Estimation](#9-cost-estimation)
10. [Technology Stack — Final Lock](#10-technology-stack--final-lock)
11. [Exit Criteria Checklist](#11-exit-criteria-checklist)

---

## 1. Database Schema Design

### 1.1 Existing Tables (8 — Phase 1)

| Table | Purpose | Status |
|---|---|---|
| `users` | User profiles, Auth0 sync | ✅ Built |
| `organizations` | Multi-tenant org records | ✅ Built |
| `org_users` | User-org membership + roles | ✅ Built |
| `documents` | Uploaded documents | ✅ Built |
| `ai_jobs` | Async job tracking | ✅ Built |
| `subscriptions` | Billing/plan management | ✅ Built |
| `audit_logs` | All user actions logged | ✅ Built |
| `api_keys` | SHA-256 hashed API keys | ✅ Built |

### 1.2 New Tables (13 — Phase 3)

| # | Table | Purpose | Key Columns |
|---|---|---|---|
| 1 | `signal_contracts` | Defines HOW to acquire a signal | id, industry, entity, source_url, source_type, refresh_cron, extraction_config, is_active |
| 2 | `signals` | Raw acquired signal instances | id, contract_id, raw_content, extracted_data, confidence, fetched_at, org_id, **embedding (pgvector)** |
| 3 | `entities` | Companies, products, people, brands | id, name, type, industry, aliases, metadata, **embedding (pgvector)** |
| 4 | `signal_entities` | Many-to-many: signals ↔ entities | signal_id, entity_id, relevance_score |
| 5 | `industries` | Industry taxonomy (4 + sub-verticals) | id, name, slug, parent_id, metadata |
| 6 | `intelligence_briefs` | Pre-built and auto-generated briefs | id, industry_id, title, bluf, body_json, outlook, status, refreshed_at, org_id |
| 7 | `brief_signals` | Many-to-many: briefs ↔ signals | brief_id, signal_id, relevance_rank |
| 8 | `chat_sessions` | AI Chat Agent conversations | id, user_id, org_id, industry_id, created_at |
| 9 | `chat_messages` | Individual messages in a session | id, session_id, role, content, sources_json, created_at |
| 10 | `search_queries` | Deep Live Search log + cache | id, user_id, query_text, results_json, source_count, created_at |
| 11 | `recommendations` | Precomputed suggestions | id, source_type, source_id, target_type, target_id, score, reason |
| 12 | `ml_model_runs` | ML pipeline audit trail | id, model_name, model_version, input_hash, output_json, ran_at |
| 13 | `signal_scores` | ML-computed scores per signal | id, signal_id, score_type, score_value, model_run_id |

### 1.3 Schema Decisions

| Decision | Choice |
|---|---|
| Multi-tenancy model | **Global signals + org-scoped briefs/customizations** |
| Signal history retention | **90 days hot (PostgreSQL) → archive to Azure Blob Storage** |
| Vector embeddings | **pgvector columns on `signals` and `entities`** |
| Total tables | **21** (8 existing + 13 new) |

---

## 2. API Contract Design

### 2.1 Existing Endpoints (30 — Phase 1)
Auth, health, organizations, documents, users, API keys, features.

### 2.2 New Endpoint Groups (~30 new → ~60 total)

#### Signals
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/signals` | Browse/filter/search signal catalog |
| GET | `/api/v1/signals/{id}` | Single signal detail + entity links |
| GET | `/api/v1/signals/trending` | ML-ranked trending signals |
| GET | `/api/v1/signals/feed` | Real-time signal feed (paginated, filterable) |

#### Intelligence Briefs
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/briefs` | List intelligence briefs (by industry) |
| GET | `/api/v1/briefs/{id}` | Full brief with BLUF, evidence, outlook |
| POST | `/api/v1/briefs/{id}/refresh` | Force-refresh brief from latest signals |

#### Deep Live Search
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/search` | Deep Live Search — query → synthesis |
| GET | `/api/v1/search/history` | User's past search queries |

#### AI Chat
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/chat/sessions` | Start new AI Chat session |
| POST | `/api/v1/chat/sessions/{id}/messages` | Send message → SSE streaming response |
| GET | `/api/v1/chat/sessions` | List user's chat sessions |
| GET | `/api/v1/chat/sessions/{id}` | Full chat history |

#### Entities
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/entities` | Browse entities |
| GET | `/api/v1/entities/{id}` | Entity detail + related signals |
| GET | `/api/v1/entities/{id}/signals` | All signals for entity |

#### Industries
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/industries` | List industry taxonomies |
| GET | `/api/v1/industries/{id}` | Industry detail + sub-verticals |
| GET | `/api/v1/industries/{id}/briefs` | All briefs for industry |
| GET | `/api/v1/industries/{id}/signals` | All signals in industry |

#### Recommendations
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/recommendations` | Personalized suggestions |

#### Situation Room
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/situation-room/{industry}` | Live dashboard data |
| WS | `/api/v1/situation-room/{industry}/live` | WebSocket real-time push |

#### ML
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/ml/scores/{signal_id}` | ML scores for signal |
| POST | `/api/v1/ml/anomalies` | Query anomaly detection results |

#### Compliance
| Method | Endpoint | Description |
|---|---|---|
| DELETE | `/api/v1/users/me` | Right to be forgotten (GDPR/NDPR) |
| GET | `/api/v1/users/me/export` | Data portability export |
| POST | `/api/v1/users/me/consent` | Record consent preferences |
| GET | `/api/v1/audit-logs` | Admin audit log viewer |
| GET | `/api/v1/compliance/data-map` | Admin data map for user |

### 2.3 Streaming & Real-time

| Feature | Protocol | Rationale |
|---|---|---|
| AI Chat responses | **SSE** (Server-Sent Events) | Simpler, proxy-friendly, same as OpenAI |
| Situation Room | **WebSocket** | True real-time, bidirectional |
| Signal feed | SSE polling (30s) | Lightweight, no persistent connection |

---

## 3. AI & ML Architecture

### 3.1 AI Synthesis Engine

| Decision | Choice |
|---|---|
| Provider | **OpenAI (direct)** |
| Model | **GPT-4o** |
| Embedding model | **text-embedding-3-small** |
| Context strategy | **RAG** — pgvector embeddings + top-K retrieval → synthesize |
| Caching | **Redis, 15min TTL** for identical queries |
| Rate management | **RQ workers** — all AI calls queued through existing infra |
| HIPAA compliance | **OpenAI BAA required** (Enterprise/Business tier), zero data retention enabled |

### 3.2 AI Chat Agent

| Decision | Choice |
|---|---|
| Architecture | **Session-with-memory** — last 10 messages as context |
| Tool use | **Function-calling** — search signals, pull briefs, query entities |
| Guardrails | **System prompt + content filtering** |
| Streaming | **SSE** |

### 3.3 ML Pipeline

| Decision | Choice |
|---|---|
| Runtime | **RQ workers** (async, doesn't block API) |
| Day-1 models (3) | (1) Anomaly detection (Isolation Forest), (2) Trending scorer (time-series slope), (3) Confidence calibrator (logistic regression) |
| Training | **Pre-trained on seeded data + weekly retrain via cron** |
| Model storage | **Azure Blob Storage** (versioned) |
| Inference | **ONNX Runtime** (3-5x faster than raw scikit-learn) |

### 3.4 Prompt Injection Defense

```
User Input → Sanitize (strip injection patterns)
  → System Prompt (hardcoded, not user-modifiable)
    → Context Window (signals from RAG, not user-supplied raw)
      → GPT-4o Response
        → Content filter (block harmful outputs)
          → Return to user
```

---

## 4. Signal Acquisition Architecture

### 4.1 Pipeline Flow

```
Signal Contract (DB) → Scheduler (cron) → Fetcher Worker (RQ)
  → API Fetcher OR Web Scraper OR RSS Parser OR Social Listener
    → Raw Response
      → Extraction (NLP / regex / JSON path)
        → Deduplication (SHA-256 hash + cosine > 0.95)
          → Confidence scoring
            → Embedding generation (text-embedding-3-small)
              → Store to PostgreSQL (signals + pgvector)
                → Trigger brief refresh if relevant
```

### 4.2 Fetcher Types

| Type | Technology | Use Case | % of Signals |
|---|---|---|---|
| API Fetcher | `httpx` async | News APIs, financial feeds, social APIs | ~40% |
| Web Scraper | `httpx` + `selectolax` | Company sites, press releases, job boards | ~35% |
| RSS/Atom Parser | `feedparser` | News feeds, blog feeds, government updates | ~15% |
| Social Listener | Platform APIs | Twitter/X, Reddit, LinkedIn | ~10% |

### 4.3 Data Sources

| Source | Provider | Cost |
|---|---|---|
| News (primary) | NewsAPI.org | Free tier – $49/mo |
| News (secondary) | Bing News Search API (Azure) | Free tier (1000 req/mo) |
| Social — Twitter/X | Twitter/X API (to acquire) | ~$100/mo |
| Social — Reddit | Reddit API (to acquire) | Free (rate-limited) |
| Web scraping | httpx + selectolax | $0 (compute only) |
| RSS feeds | feedparser | $0 |

### 4.4 Scheduling Strategy

| Frequency | Signal Type | Examples |
|---|---|---|
| Every 15 min | Breaking/critical | News APIs, social mentions, market data |
| Every 1 hour | Standard monitoring | Job postings, press releases, app store |
| Every 6 hours | Slow-moving | Regulatory filings, patents, SEC |
| Daily | Bulk/archival | Industry reports, government gazettes |

### 4.5 Failure Handling
- Exponential backoff: 3 retries (1min, 5min, 30min)
- After 3 failures: mark contract as `degraded` → alert
- Deduplication: content hash (SHA-256) + semantic similarity (cosine > 0.95)

---

## 5. Frontend Architecture

### 5.1 Technology Stack (Locked)

| Layer | Technology |
|---|---|
| Framework | Next.js 14 + TypeScript |
| Styling | Tailwind CSS |
| Components | Shadcn/ui |
| Charts/Viz | Tremor |
| Data fetching | TanStack Query (React Query) |
| State management | Zustand |
| Forms | React Hook Form + Zod |
| PWA | next-pwa |

### 5.2 Real-time Features

| Feature | Technology |
|---|---|
| Chat streaming | SSE via EventSource API |
| Situation Room | Native WebSocket → Zustand store |
| Signal feed | SSE polling (every 30s) |

### 5.3 UI Design
**⏸️ DEFERRED** — User will provide wireframe designs. All visual design decisions (pages, layout, color theme, component styling) are user-owned. Architecture and stack decisions locked above.

---

## 6. Infrastructure & DevOps

### 6.1 CI/CD Pipeline (GitHub Actions)

| Stage | Trigger | Actions |
|---|---|---|
| Lint & Type Check | Every PR | ruff + mypy (backend), eslint + tsc (frontend) |
| Unit/E2E Tests | Every PR | pytest (87+ tests), vitest (frontend) |
| Build | Merge to `main` | Docker multi-stage build (API + Worker) |
| Deploy Pre-prod | Merge to `main` | Push to ACR → Azure Container Apps (staging) |
| Deploy Production | Tag `v*` + manual approval | Push to ACR → Azure Container Apps (prod) |

### 6.2 Environments

| Environment | Purpose | URL |
|---|---|---|
| Local | Development | `localhost:8000` / `localhost:3000` |
| Pre-prod | Testing, QA, demo | `staging.cogent-api.azurecontainerapps.io` |
| Production | Live | `api.cogent.ai` (custom domain) |

### 6.3 Observability — Grafana Cloud (Free Tier)

| Layer | Tool | Limit |
|---|---|---|
| Logging | Loki | 50GB/mo |
| Metrics | Prometheus | 10K series |
| Traces | Tempo | 50GB/mo |
| Dashboard | Grafana | Unlimited |
| Alerts | Grafana Alerting | Included |

### 6.4 Secrets Management
- **Azure Key Vault** — all secrets (DB, Redis, OpenAI, Auth0, API keys)
- CI/CD pulls via GitHub OIDC → Key Vault

---

## 7. Security & Compliance

### 7.1 Critical Bug — Must Fix

| Bug | Fix |
|---|---|
| Auth namespace mismatch: frontend `https://cogent-ai.com` vs backend `https://cogent.ai/claims/` | Align to `https://cogent.ai/claims/` everywhere |

### 7.2 Security Layers

| Layer | Status |
|---|---|
| JWT validation (Auth0 JWKS) | ✅ Built |
| RBAC (owner/admin/member/viewer) | ✅ Built |
| API Key auth (SHA-256 hashed) | ✅ Built |
| Rate limiting (Redis-backed) | ✅ Built |
| CORS (configurable origins) | ✅ Built |
| HMAC webhook verification | ✅ Built |
| Input validation (Pydantic strict) | ⬜ Harden for new endpoints |
| Prompt injection defense | ⬜ New |
| Content Safety filtering | ⬜ New |
| Signal source validation | ⬜ New |

### 7.3 Rate Limits

| Scope | Limit |
|---|---|
| AI calls per user | **30/min** |
| AI calls per org | **100/min** |
| Search queries | 30 req/min |
| General API | Existing rate limiter |

### 7.4 Compliance Framework

| Framework | Status | Day-1 Requirement |
|---|---|---|
| **GDPR** | Day-1 mandatory (EU users confirmed) | RTBF, export, consent, 72hr breach notification |
| **NDPR** | Day-1 mandatory (Nigerian users confirmed) | Same as GDPR + data residency considerations |
| **HIPAA** | Day-1 technical controls (PHI confirmed) | BAA with OpenAI required, zero data retention, PHI sanitization |
| **SOC 2** | Architecture-ready, formal audit post-MVP | Build controls now, certify when revenue justifies |

### 7.5 Compliance Endpoints

| Endpoint | Purpose | Framework |
|---|---|---|
| `DELETE /api/v1/users/me` | Right to be forgotten | GDPR, NDPR |
| `GET /api/v1/users/me/export` | Data portability | GDPR, NDPR, HIPAA |
| `POST /api/v1/users/me/consent` | Consent preferences | GDPR, NDPR |
| `GET /api/v1/audit-logs` | Admin audit viewer | SOC 2, HIPAA |
| `GET /api/v1/compliance/data-map` | Admin data map | SOC 2 |

### 7.6 Data Classification

| Data Type | Classification | Handling |
|---|---|---|
| Signal data (public sources) | Public | Standard storage |
| User PII | Sensitive - PII | Encrypted, access-logged, deletable |
| Chat conversations | Confidential | Encrypted, user-scoped, 90-day retention |
| Search queries | Confidential | User-scoped, 90-day retention |
| Health-related signals (PHI) | Protected Health Info | Encrypt, audit all access, BAA required |
| API keys | Secret | SHA-256 hashed, never plaintext |

### 7.7 Data Retention

| Data Type | Hot (PostgreSQL) | Archive (Azure Blob) |
|---|---|---|
| Signals | 90 days | Indefinite |
| Chat sessions | 90 days | Deleted |
| Search queries | 90 days | Deleted |
| Audit logs | 1 year | 7 years (compliance) |
| ML model artifacts | Latest 3 versions | All versions |

---

## 8. Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    FRONTEND (Next.js 14)                 │
│  Shadcn/ui · TanStack Query · Zustand · Tremor · PWA   │
│  SSE (Chat) · WebSocket (Situation Room)                │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTPS
┌──────────────────────▼──────────────────────────────────┐
│               BACKEND API (FastAPI)                      │
│  Auth0 JWT · RBAC · Rate Limiting · CORS                │
│  ~60 endpoints · Pydantic strict · HIPAA audit logging  │
├─────────────┬──────────────┬────────────────────────────┤
│  AI Engine  │  Search      │  Signal Acquisition        │
│  GPT-4o     │  pgvector    │  httpx · selectolax        │
│  RAG        │  Deep Live   │  feedparser · schedulers   │
│  Chat Agent │  Synthesis   │  280 signal contracts      │
│  Func-call  │              │  4 fetcher types           │
└──────┬──────┴──────┬───────┴──────────┬─────────────────┘
       │             │                  │
┌──────▼──────┐ ┌────▼─────┐  ┌────────▼────────┐
│  OpenAI API │ │PostgreSQL│  │  RQ Workers      │
│  GPT-4o     │ │ Neon     │  │  Azure Container │
│  Embeddings │ │ pgvector │  │  ML (ONNX)       │
│  BAA/HIPAA  │ │ 21 tables│  │  Signal fetchers │
└─────────────┘ └────┬─────┘  └────────┬─────────┘
                     │                  │
                ┌────▼─────┐  ┌────────▼────────┐
                │  Redis   │  │  Azure Blob     │
                │  Upstash │  │  ML models      │
                │  Cache   │  │  Signal archive  │
                │  Queue   │  │  (90-day rotate) │
                └──────────┘  └─────────────────┘
                     │
              ┌──────▼──────┐
              │ Grafana Cloud│
              │ Loki · Prom  │
              │ Free Tier    │
              └──────────────┘
```

---

## 9. Cost Estimation

### Monthly MVP Cost

| Category | Service | Cost |
|---|---|---|
| AI/ML | OpenAI GPT-4o + embeddings | ~$52/mo |
| Data Acquisition | NewsAPI + Bing News + Twitter/X + Reddit | ~$150/mo |
| Compute | Azure Container Apps (API + Worker × 2) | ~$30/mo |
| Database | Neon PostgreSQL (Pro) | $0–19/mo |
| Cache | Upstash Redis (Pro) | $0–10/mo |
| Storage | Azure Blob (models + archives) | ~$2/mo |
| Observability | Grafana Cloud (free tier) | $0/mo |
| Auth | Auth0 (free tier, 7K MAU) | $0/mo |
| CI/CD | GitHub Actions (free tier) | $0/mo |
| DNS | Azure DNS / Cloudflare | ~$1/mo |
| **TOTAL** | | **~$235–264/mo** |

---

## 10. Technology Stack — Final Lock

| Layer | Technology | Version |
|---|---|---|
| Backend | FastAPI + Uvicorn | 0.109+ |
| Language | Python | 3.11+ |
| ORM | SQLAlchemy (async) | 2.0+ |
| Database | PostgreSQL + pgvector (Neon Serverless) | 15 |
| Cache/Queue | Redis (Upstash) + RQ | 7 |
| AI — LLM | OpenAI GPT-4o (direct, BAA for HIPAA) | Latest |
| AI — Embeddings | OpenAI text-embedding-3-small | Latest |
| ML — Training | scikit-learn | Latest |
| ML — Inference | ONNX Runtime | Latest |
| Frontend | Next.js + TypeScript + Tailwind | 14 |
| UI Components | Shadcn/ui + Tremor | Latest |
| State | TanStack Query + Zustand | Latest |
| Forms | React Hook Form + Zod | Latest |
| PWA | next-pwa | Latest |
| Auth | Auth0 + JWT | Latest |
| Scraping | httpx + selectolax + feedparser | Latest |
| Compute | Azure Container Apps | Latest |
| CI/CD | GitHub Actions | Latest |
| Observability | Grafana Cloud (Loki + Prometheus + Tempo) | Free Tier |
| Secrets | Azure Key Vault | Latest |
| Storage | Azure Blob Storage | Latest |

---

## 11. Exit Criteria Checklist

| # | Criterion | Status |
|---|---|---|
| 1 | Database schema designed (21 tables) | ✅ |
| 2 | API contracts defined (~60 endpoints) | ✅ |
| 3 | AI/ML architecture locked (GPT-4o, RAG, 3 ML models) | ✅ |
| 4 | Signal acquisition pipeline designed (4 fetcher types) | ✅ |
| 5 | Frontend stack confirmed (Shadcn + TanStack + Zustand + Tremor) | ✅ |
| 6 | UI design deferred to user wireframes | ✅ |
| 7 | CI/CD pipeline designed (GitHub Actions, manual prod approval) | ✅ |
| 8 | Observability stack chosen (Grafana Cloud free tier) | ✅ |
| 9 | Security hardening plan documented | ✅ |
| 10 | Compliance architecture defined (GDPR, NDPR, HIPAA, SOC 2) | ✅ |
| 11 | Monthly cost estimated (~$235-264/mo) | ✅ |
| 12 | Technology stack final-locked | ✅ |
| 13 | Architecture diagram produced | ✅ |
| 14 | Auth namespace bug identified with fix plan | ✅ |

**WP-0.2 STATUS: ✅ COMPLETE — All exit criteria met.**

---

*Document generated as part of Phase 0: Strategy & Discovery*
*Next: WP-0.3 — Environment Setup*
