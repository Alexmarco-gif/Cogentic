# WP-0.3 — Environment Setup Deliverable

**Document Version:** 1.0
**Date:** 2026-02-10
**Status:** ✅ APPROVED
**Phase:** 0 — Strategy & Discovery
**Work Package:** WP-0.3 — Environment Setup

---

## Table of Contents

1. [Repository Structure](#1-repository-structure)
2. [Branch Strategy](#2-branch-strategy)
3. [New Directories (Phase 3)](#3-new-directories-phase-3)
4. [Dependencies Installed](#4-dependencies-installed)
5. [CI/CD Pipelines](#5-cicd-pipelines)
6. [Environment Configuration](#6-environment-configuration)
7. [Exit Criteria Checklist](#7-exit-criteria-checklist)

---

## 1. Repository Structure

**Type:** Monorepo (backend + frontend in single repo)

```
cogent/
├── backend/
│   ├── api/v1/              # API endpoint routers
│   ├── auth/                # Auth0 JWT + RBAC (11 files)
│   ├── models/              # SQLAlchemy models (8 existing + 13 new)
│   ├── repositories/        # Data access layer
│   ├── services/            # Business logic
│   ├── tests/               # E2E tests (87 existing)
│   ├── webhooks/            # Auth0 webhook handlers
│   ├── config/              # Feature flags (YAML)
│   ├── signals/             # NEW — Signal acquisition pipeline
│   │   ├── contracts/       # Signal contract definitions
│   │   ├── fetchers/        # API, scraper, RSS, social fetchers
│   │   ├── processors/      # Extraction, dedup, scoring
│   │   └── scheduler.py     # Cron scheduling logic
│   ├── ai/                  # NEW — AI engine
│   │   ├── synthesis.py     # RAG + GPT-4o synthesis
│   │   ├── chat.py          # Chat agent + function-calling
│   │   ├── embeddings.py    # Embedding generation
│   │   └── guardrails.py    # Prompt injection defense
│   ├── ml/                  # NEW — ML pipeline
│   │   ├── models/          # Trained model artifacts
│   │   ├── training/        # Training scripts
│   │   ├── inference.py     # ONNX runtime inference
│   │   └── scoring.py       # Anomaly, trending, confidence
│   ├── compliance/          # NEW — GDPR/NDPR/HIPAA handlers
│   │   ├── deletion.py      # Right to be forgotten
│   │   ├── export.py        # Data portability
│   │   └── consent.py       # Consent management
│   └── briefs/              # NEW — Intelligence brief engine
│       ├── generator.py     # Brief generation from signals
│       ├── templates/       # Brief templates per industry
│       └── refresh.py       # Auto-refresh logic
├── frontend/                # Next.js 14 + Tailwind (UI deferred)
├── infrastructure/          # IaC scripts
├── scripts/                 # Setup scripts
├── docs/                    # Planning documents
│   ├── WP-0.1_Requirements_Finalization.md
│   ├── WP-0.2_Technical_Planning.md
│   └── WP-0.3_Environment_Setup.md
├── alembic/                 # Database migrations
├── .github/workflows/       # CI/CD pipelines
│   ├── ci.yml
│   ├── deploy-staging.yml
│   └── deploy-prod.yml
├── .env.example             # All config vars documented
├── docker-compose.yml       # Local dev (PostgreSQL + Redis)
├── Dockerfile               # API container
├── Dockerfile.worker        # Worker container
├── pyproject.toml           # Python project config
└── requirements.txt         # Frozen dependencies
```

---

## 2. Branch Strategy

| Branch | Purpose | Protection |
|---|---|---|
| `main` | Production-ready code | PR required, 1 approval, CI must pass |
| `develop` | Integration branch (created ✅) | PR required, CI must pass |
| `feature/*` | Feature branches | No protection |
| `hotfix/*` | Production hotfixes | PR to main, fast-track |

**Legacy branches** (from Phase 1): `dev`, `staging`, `production` — to be deprecated after migration.

---

## 3. New Directories (Phase 3)

All directories created with `__init__.py` files and placeholder modules:

| Directory | Files | Purpose |
|---|---|---|
| `backend/signals/` | `__init__.py`, `scheduler.py` | Signal acquisition orchestration |
| `backend/signals/contracts/` | `__init__.py` | Signal contract definitions |
| `backend/signals/fetchers/` | `__init__.py` | API, scraper, RSS, social fetchers |
| `backend/signals/processors/` | `__init__.py` | Extraction, dedup, confidence scoring |
| `backend/ai/` | `__init__.py`, `synthesis.py`, `chat.py`, `embeddings.py`, `guardrails.py` | AI engine |
| `backend/ml/` | `__init__.py`, `inference.py`, `scoring.py` | ML pipeline |
| `backend/ml/models/` | `__init__.py` | Model artifact storage |
| `backend/ml/training/` | `__init__.py` | Training scripts |
| `backend/compliance/` | `__init__.py`, `deletion.py`, `export.py`, `consent.py` | Compliance handlers |
| `backend/briefs/` | `__init__.py`, `generator.py`, `refresh.py` | Intelligence brief engine |
| `backend/briefs/templates/` | `__init__.py` | Industry brief templates |
| `.github/workflows/` | `ci.yml`, `deploy-staging.yml`, `deploy-prod.yml` | CI/CD pipelines |

---

## 4. Dependencies Installed

### 4.1 Python Environment
- **Type:** Virtual Environment (`.venv/`)
- **Python Version:** 3.12.6

### 4.2 New Packages (19 — Phase 3)

| Package | Version | Category |
|---|---|---|
| `openai` | 2.18.0 | AI — LLM & Embeddings |
| `tiktoken` | 0.12.0 | AI — Token counting |
| `pgvector` | latest | Database — Vector embeddings |
| `scikit-learn` | latest | ML — Model training |
| `onnx` | latest | ML — Model export |
| `onnxruntime` | latest | ML — Fast inference |
| `httpx` | latest | Acquisition — Async HTTP client |
| `selectolax` | latest | Acquisition — HTML parsing |
| `feedparser` | latest | Acquisition — RSS/Atom feeds |
| `apscheduler` | latest | Acquisition — Cron scheduler |
| `sse-starlette` | ≥1.0 | Streaming — Server-Sent Events |
| `websockets` | latest | Streaming — WebSocket support |
| `azure-storage-blob` | latest | Storage — Azure Blob SDK |
| `azure-identity` | latest | Infra — Azure credentials |
| `azure-keyvault-secrets` | latest | Infra — Key Vault access |
| `opentelemetry-api` | latest | Observability — Tracing API |
| `opentelemetry-sdk` | latest | Observability — Tracing SDK |
| `opentelemetry-exporter-otlp` | latest | Observability — Grafana export |
| `prometheus-client` | latest | Observability — Metrics |

### 4.3 Existing Packages (Phase 1 — retained)
FastAPI, uvicorn, SQLAlchemy, asyncpg, alembic, pydantic, python-jose, rq, redis, pytest, ruff, mypy, etc.

---

## 5. CI/CD Pipelines

### 5.1 `ci.yml` — Continuous Integration
- **Trigger:** Push/PR to `main` or `develop`
- **Jobs:**
  - Backend lint (ruff check + format)
  - Backend tests (pytest with PostgreSQL 15 + Redis 7 services)
  - Frontend lint (eslint + tsc) — when frontend is built

### 5.2 `deploy-staging.yml` — Staging Deployment
- **Trigger:** Push to `main`
- **Actions:** Build Docker → Push to ACR → Deploy to Azure Container Apps (staging)

### 5.3 `deploy-prod.yml` — Production Deployment
- **Trigger:** Tag `v*` + **manual approval**
- **Actions:** Build Docker → Push to ACR → Deploy to Azure Container Apps (production)

---

## 6. Environment Configuration

### 6.1 `.env.example` — Complete Configuration
All config variables documented with placeholder values:

| Section | Variables |
|---|---|
| Application | `ENVIRONMENT`, `DEBUG`, `SECRET_KEY` |
| Database | `DATABASE_URL`, pool settings |
| Redis | `REDIS_URL`, max connections |
| Auth0 | `AUTH0_DOMAIN`, `AUTH0_AUDIENCE`, M2M credentials, claims namespace |
| OpenAI | `OPENAI_API_KEY`, model, embedding model, max tokens, temperature |
| Signal Acquisition | `NEWSAPI_KEY`, `BING_NEWS_API_KEY`, `TWITTER_BEARER_TOKEN`, Reddit credentials |
| Azure Services | Blob storage, Key Vault URL |
| Grafana Cloud | OTLP endpoint, instance ID, API key |
| Rate Limiting | AI per-user (30/min), AI per-org (100/min), search per-user |
| ML Pipeline | Model storage mode, local path, retrain schedule |
| Data Retention | Signal (90d), chat (90d), search (90d), audit (365d) |

---

## 7. Exit Criteria Checklist

| # | Criterion | Status |
|---|---|---|
| 1 | Monorepo structure confirmed | ✅ |
| 2 | New Phase 3 directories created with init files | ✅ |
| 3 | Branch strategy implemented (main + develop + feature/*) | ✅ |
| 4 | `develop` branch created | ✅ |
| 5 | 19 new Python packages installed | ✅ |
| 6 | `requirements.txt` frozen | ✅ |
| 7 | `.env.example` updated with all Phase 3 config | ✅ |
| 8 | CI/CD workflows created (ci, staging, prod) | ✅ |
| 9 | Local dev setup documented | ✅ |
| 10 | All packages import successfully | ✅ |

**WP-0.3 STATUS: ✅ COMPLETE — All exit criteria met.**

---

*Document generated as part of Phase 0: Strategy & Discovery*
*Next: Phase 0 Exit Criteria Validation*
