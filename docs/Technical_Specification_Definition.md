# ESIP Technical Specification Definition

**Document Version:** 2.0
**Last Updated:** February 9, 2026
**Status:** Approved for Implementation
**Classification:** Internal Engineering

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Overview](#2-system-overview)
3. [Architecture Specification](#3-architecture-specification)
4. [Data Models & Schema Design](#4-data-models--schema-design)
5. [API Contracts](#5-api-contracts)
6. [Signal Processing Pipeline](#6-signal-processing-pipeline)
7. [AI Chat Agent](#7-ai-chat-agent)
8. [Deep Live Search Engine](#8-deep-live-search-engine)
9. [Lightweight ML Engine](#9-lightweight-ml-engine)
10. [Industry Ontology & Enterprise Signal Catalog](#10-industry-ontology--enterprise-signal-catalog)
11. [Integration Specifications](#11-integration-specifications)
12. [Security Requirements](#12-security-requirements)
13. [Performance Requirements](#13-performance-requirements)
14. [Infrastructure Specification](#14-infrastructure-specification)
15. [Observability & Monitoring](#15-observability--monitoring)
16. [Testing Requirements](#16-testing-requirements)
17. [Deployment Specification](#17-deployment-specification)
18. [Technical Constraints & Boundaries](#18-technical-constraints--boundaries)
19. [Glossary](#19-glossary)

---

## 1. Executive Summary

### 1.1 Purpose

This document defines the complete technical specification for the Enterprise Signal Intelligence Platform (ESIP). It provides engineering teams with all information required to implement, test, and deploy the system without ambiguity.

### 1.2 Product Definition

ESIP is an enterprise-grade signal intelligence platform that:
- **Ingests** structured and unstructured data from multiple live sources across industries and domains
- **Refines** raw observations into normalized, enriched records using lightweight ML models and domain ontologies
- **Synthesizes** validated signals with enterprise-grade confidence scores (≥0.85) and full lineage
- **Reasons** via an AI Chat Agent that provides adaptive, context-aware intelligence conversations
- **Discovers** through deep live search that orchestrates multi-source parallel retrieval with semantic ranking
- **Delivers** decision-ready intelligence with actionable recommendations via APIs, PWA, webhooks, and notifications

### 1.3 Intelligence Philosophy

ESIP intelligence is **non-static, adaptive, and reasoning-based**:

| Principle | Application |
|-----------|------------|
| **Adaptive** | Models retrain on new data patterns; signals evolve with market conditions |
| **Reasoning-Based** | Not rule engines — ML models + LLM synthesis that generalize across domains |
| **Ontology-Driven** | Industry-specific domain taxonomies ensure signals are contextually accurate |
| **High-Confidence** | Minimum 0.85 confidence threshold; below that = flagged, not delivered |
| **Recommendation-First** | Every signal includes actionable recommendations, not just data |
| **Trustable** | Full evidence lineage, confidence decomposition, limitation disclosure |

### 1.4 Key Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Backend Framework | FastAPI (Python 3.11+) | Async-first, type hints, auto-docs |
| Database | PostgreSQL (Neon Serverless) + pgvector | ACID compliance, JSONB, vector search, cost-efficient |
| Cache/Queue | Redis (Upstash) | Serverless, low latency, pub/sub support |
| Background Jobs | Redis Queue (RQ) or Celery | Simple, reliable, observable |
| Search | Deep Live Search Engine (multi-source parallel) | Enterprise-grade discovery, not basic text search |
| Auth | Auth0 + JWT | Enterprise SSO, RBAC, compliance |
| Hosting | Azure Container Apps | Serverless scaling, cost control |
| Frontend | Next.js 14+ as **PWA** | Installable, offline-capable, push notifications, app-like UX |
| AI Chat | LLM-powered conversational agent | Natural language signal interaction, adaptive reasoning |
| ML Engine | Lightweight models (scikit-learn, ONNX) | Signal scoring, anomaly detection, entity resolution |
| Ontology | Industry domain taxonomies | Contextually accurate signals across enterprise verticals |

### 1.5 Non-Goals (Explicitly Out of Scope)

- Real-time streaming (Kafka) — DEFERRED to Phase 4
- Multi-region deployment — DEFERRED to Phase 4
- SOC 2 Compliance — DEFERRED to Phase 4
- Native mobile applications — PWA replaces this need
- Heavy GPU-based model training — lightweight models only, inference-focused

> **Note:** ML models, AI Chat Agent, Deep Search, PWA, and Industry Ontologies are **IN SCOPE** for MVP.

---

## 2. System Overview

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│  PWA Web App     │  AI Chat Agent    │  API Consumers  │  Webhooks          │
│  (Next.js PWA)   │  (Conversational) │  (REST/SDK)     │  (Push)            │
└──────────┬───────┴─────────┬─────────┴────────┬────────┴────────┬───────────┘
           │                 │                   │                 │
           ▼                 ▼                   ▼                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API GATEWAY                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  Rate Limiting  │  JWT Validation  │  Request Routing  │  Metrics           │
└──────────┬──────────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           APPLICATION LAYER                                  │
├──────────────┬──────────────┬──────────────┬──────────────┬─────────────────┤
│  Auth Svc    │  Signal Svc  │ Analytics Svc│  Chat Agent  │  Admin Svc      │
├──────────────┼──────────────┼──────────────┼──────────────┼─────────────────┤
│ • JWT valid  │ • Signal CRUD│ • Trends     │ • Conv mgmt  │ • User mgmt     │
│ • RBAC       │ • Contracts  │ • Comparisons│ • Tool use   │ • Org mgmt      │
│ • API keys   │ • Synthesis  │ • Aggregation│ • Streaming  │ • Billing        │
│              │ • Search     │ • Recommend  │ • Context    │                  │
└──────────────┴──────┬───────┴──────────────┴──────────────┴─────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        INTELLIGENCE LAYER                                    │
├──────────────┬──────────────┬──────────────┬──────────────┬─────────────────┤
│ Acquisition  │ Refinement   │ ML Engine    │ Deep Search  │ Recommendation  │
│ Engine       │ Engine       │              │ Engine       │ Engine          │
├──────────────┼──────────────┼──────────────┼──────────────┼─────────────────┤
│ • Adapters   │ • Normalize  │ • Anomaly ML │ • Multi-src  │ • Action recs   │
│ • Scheduler  │ • Entity res │ • Scoring ML │ • Parallel   │ • Risk assess   │
│ • Rate limit │ • Enrich     │ • Clustering │ • Semantic   │ • Opportunity   │
│              │ • Ontology   │ • Forecast   │ • Relevance  │ • Confidence    │
└──────────────┴──────┬───────┴──────────────┴──────────────┴─────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        ONTOLOGY & KNOWLEDGE LAYER                            │
├──────────────┬──────────────┬──────────────┬────────────────────────────────┤
│ Industry     │ Domain       │ Enterprise   │ Signal Catalog                  │
│ Ontologies   │ Taxonomies   │ Hierarchies  │                                │
├──────────────┼──────────────┼──────────────┼────────────────────────────────┤
│ • Fintech    │ • Entities   │ • Org trees  │ • Template contracts            │
│ • FMCG       │ • Relations  │ • Dept maps  │ • Pre-built signals             │
│ • Energy     │ • Properties │ • Role maps  │ • Industry benchmarks           │
│ • Real Estate│ • Constraints│              │ • Best-practice configs          │
│ • Agriculture│              │              │                                 │
└──────────────┴──────┬───────┴──────────────┴────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            DATA LAYER                                        │
├──────────────┬──────────────┬──────────────┬────────────────────────────────┤
│  PostgreSQL  │    Redis     │ Blob Storage │ Vector Store (pgvector)         │
├──────────────┼──────────────┼──────────────┼────────────────────────────────┤
│ • Signals    │ • Job queue  │ • Documents  │ • Evidence embeddings           │
│ • Contracts  │ • Cache      │ • PDFs       │ • Ontology embeddings           │
│ • Ontologies │ • Rate limits│ • ML models  │ • Chat history embeddings       │
│ • Chat hist  │ • Sessions   │ • Evidence   │ • Semantic search index          │
│ • ML registry│ • Chat ctx   │              │                                 │
└──────────────┴──────────────┴──────────────┴────────────────────────────────┘
```

### 2.2 Component Responsibilities

| Component | Responsibility | Technology |
|-----------|---------------|------------|
| **API Gateway** | Request routing, auth, rate limiting | FastAPI middleware |
| **Auth Service** | Identity, access control, API keys | Auth0 + custom JWT |
| **Signal Service** | Core signal operations, contracts | FastAPI + SQLAlchemy |
| **AI Chat Agent** | Conversational intelligence, tool orchestration | LLM + streaming + tool-use |
| **Deep Search Engine** | Multi-source parallel search, semantic ranking | Python + pgvector + live fetch |
| **Acquisition Engine** | Source fetching, scheduling | Background workers |
| **Refinement Engine** | Data normalization, ontology enrichment | Python pipelines + ontology |
| **ML Engine** | Signal scoring, anomaly detection, entity resolution | scikit-learn + ONNX |
| **Recommendation Engine** | Actionable insights, risk/opportunity assessment | LLM + ML scoring |
| **Intelligence Layer** | Analytics, trends, anomalies, forecasting | Python + ML + SQL |
| **Ontology Layer** | Industry domain knowledge, taxonomies | PostgreSQL JSONB + embeddings |

### 2.3 Request Flow

```
1. Client Request → API Gateway (PWA / Chat / API)
2. JWT Validation → Auth Service
3. Rate Limit Check → Redis
4. Route to Service → Application Layer
5. If Chat: → Chat Agent → Tool Orchestration → Signal/Search/ML Services
6. If Search: → Deep Search Engine → Multi-Source Parallel Fetch → Semantic Rank
7. Business Logic → Service Layer (Ontology-Aware)
8. ML Scoring → Lightweight ML Engine (if applicable)
9. Data Operations → Repository Layer
10. Persistence → Database
11. Recommendation Generation → Recommendation Engine
12. Response Construction → Service Layer
13. Audit Logging → Async Queue
14. Response → Client (with recommendations + confidence decomposition)
```

---

## 3. Architecture Specification

### 3.1 Backend Architecture

#### 3.1.1 Directory Structure

```
backend/
├── __init__.py
├── main.py                 # FastAPI app entry point
├── config.py               # Settings management
├── database.py             # Database session management
├── redis_client.py         # Redis connection
├── observability.py        # Logging, metrics, tracing
│
├── api/
│   ├── __init__.py
│   └── v1/
│       ├── __init__.py     # Router aggregator
│       ├── auth.py         # Auth endpoints
│       ├── signals.py      # Signal CRUD
│       ├── contracts.py    # Contract management
│       ├── sources.py      # Source management
│       ├── analytics.py    # Analytics endpoints
│       ├── chat.py         # AI Chat Agent endpoints
│       ├── search.py       # Deep Search endpoints
│       ├── ontology.py     # Ontology & catalog endpoints
│       ├── recommendations.py  # Recommendation endpoints
│       ├── orgs.py         # Organization management
│       ├── users.py        # User management
│       └── health.py       # Health checks
│
├── auth/
│   ├── __init__.py
│   ├── dependencies.py     # Auth dependencies
│   ├── guards.py           # Permission guards
│   ├── jwks.py             # JWKS client
│   ├── middleware.py       # JWT middleware
│   ├── permissions.py      # RBAC definitions
│   ├── rate_limit.py       # Rate limiting
│   └── schemas.py          # Auth schemas
│
├── models/
│   ├── __init__.py
│   ├── base.py             # Base model with common fields
│   ├── user.py
│   ├── organization.py
│   ├── signal.py           # Core signal model
│   ├── signal_contract.py  # Contract definition
│   ├── signal_value.py     # Time-series values
│   ├── source.py           # Data source
│   ├── evidence.py         # Evidence/lineage
│   ├── entity.py           # Resolved entities
│   ├── audit_log.py
│   ├── chat_session.py     # Chat sessions
│   ├── chat_message.py     # Chat messages
│   ├── ontology.py         # Industry ontologies
│   ├── domain_taxonomy.py  # Domain taxonomies
│   ├── ml_model.py         # ML model registry
│   └── recommendation.py   # Recommendation records
│
├── repositories/
│   ├── __init__.py
│   ├── base.py             # Generic repository
│   ├── signal.py
│   ├── contract.py
│   ├── source.py
│   ├── user.py
│   ├── chat.py             # Chat session/message repo
│   ├── ontology.py         # Ontology repo
│   └── ml_model.py         # ML model repo
│
├── services/
│   ├── __init__.py
│   ├── signal_service.py       # Signal business logic
│   ├── acquisition_service.py  # Source fetching
│   ├── refinement_service.py   # Data processing
│   ├── synthesis_service.py    # Signal synthesis
│   ├── analytics_service.py    # Analytics/trends
│   ├── notification_service.py # Alerts/webhooks
│   ├── chat_agent_service.py   # AI Chat Agent orchestration
│   ├── deep_search_service.py  # Deep live search
│   ├── ml_engine_service.py    # ML model inference
│   ├── ontology_service.py     # Ontology management
│   ├── recommendation_service.py # Recommendation engine
│   └── catalog_service.py      # Enterprise signal catalog
│
├── agent/
│   ├── __init__.py
│   ├── agent.py            # Chat agent core
│   ├── tools.py            # Agent tool definitions
│   ├── context.py          # Conversation context manager
│   ├── memory.py           # Short/long-term memory
│   └── prompts.py          # System prompts per domain
│
├── ml/
│   ├── __init__.py
│   ├── anomaly_detector.py     # Anomaly detection models
│   ├── signal_scorer.py        # Signal confidence ML scorer
│   ├── entity_resolver_ml.py   # ML-based entity resolution
│   ├── trend_forecaster.py     # Lightweight trend forecasting
│   ├── cluster_engine.py       # Signal clustering
│   ├── model_registry.py       # Model versioning & loading
│   └── simulation.py           # Simulation mode for starter tier
│
├── search/
│   ├── __init__.py
│   ├── orchestrator.py     # Search orchestration
│   ├── parallel_fetcher.py # Multi-source parallel fetch
│   ├── semantic_ranker.py  # Semantic relevance ranking
│   ├── result_synthesizer.py # Result fusion & dedup
│   └── source_discovery.py # Dynamic source discovery
│
├── ontology/
│   ├── __init__.py
│   ├── loader.py           # Ontology loading & caching
│   ├── matcher.py          # Ontology-aware entity matching
│   ├── taxonomy.py         # Domain taxonomy management
│   └── catalog.py          # Enterprise signal catalog
│
├── schemas/
│   ├── __init__.py
│   ├── signal.py           # Signal Pydantic schemas
│   ├── contract.py
│   ├── source.py
│   ├── analytics.py
│   ├── chat.py             # Chat schemas
│   ├── search.py           # Search schemas
│   ├── ontology.py         # Ontology schemas
│   ├── recommendation.py   # Recommendation schemas
│   └── common.py           # Shared schemas
│
├── jobs/
│   ├── __init__.py
│   ├── acquisition_job.py  # Source fetch jobs
│   ├── refinement_job.py   # Processing jobs
│   ├── notification_job.py # Alert delivery jobs
│   ├── ml_training_job.py  # Lightweight model retraining
│   └── ontology_sync_job.py # Ontology update jobs
│
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_e2e_signals.py
    ├── test_e2e_contracts.py
    ├── test_e2e_analytics.py
    ├── test_e2e_chat.py
    ├── test_e2e_search.py
    ├── test_e2e_ml.py
    └── test_e2e_ontology.py
```

#### 3.1.2 Layer Responsibilities

| Layer | Responsibility | Rules |
|-------|---------------|-------|
| **API** | HTTP handling, request/response | No business logic, validation only |
| **Schema** | Data validation, serialization | Pydantic models, no DB access |
| **Service** | Business logic, orchestration | Can call multiple repos, no HTTP |
| **Agent** | Chat agent orchestration, tool use | Calls services via tools, manages conversation |
| **ML** | Model inference, scoring, detection | Stateless inference, model registry |
| **Search** | Multi-source discovery, ranking | Parallel fetch, semantic scoring |
| **Ontology** | Domain knowledge, taxonomies | Read-heavy, cached, enrichment |
| **Repository** | Data access, queries | Single entity focus, no business logic |
| **Model** | ORM definitions, relationships | No logic beyond field validation |

### 3.2 Frontend Architecture (PWA)

#### 3.2.1 Directory Structure

```
frontend/
├── app/
│   ├── layout.tsx          # Root layout
│   ├── page.tsx            # Landing page
│   ├── globals.css
│   ├── manifest.json       # PWA manifest
│   ├── sw.ts               # Service worker
│   ├── offline.tsx         # Offline fallback page
│   │
│   ├── (auth)/
│   │   ├── login/
│   │   └── callback/
│   │
│   ├── (dashboard)/
│   │   ├── layout.tsx      # Dashboard layout
│   │   ├── page.tsx        # Dashboard home
│   │   │
│   │   ├── signals/
│   │   │   ├── page.tsx    # Signal list
│   │   │   ├── [id]/
│   │   │   │   └── page.tsx
│   │   │   └── new/
│   │   │       └── page.tsx
│   │   │
│   │   ├── contracts/
│   │   │   ├── page.tsx
│   │   │   └── [id]/
│   │   │       └── page.tsx
│   │   │
│   │   ├── chat/           # AI Chat Interface
│   │   │   ├── page.tsx    # Chat home (new conversation)
│   │   │   └── [id]/
│   │   │       └── page.tsx # Chat session
│   │   │
│   │   ├── search/         # Deep Search Interface
│   │   │   └── page.tsx
│   │   │
│   │   ├── analytics/
│   │   │   ├── page.tsx
│   │   │   ├── trends/
│   │   │   │   └── page.tsx
│   │   │   └── recommendations/
│   │   │       └── page.tsx
│   │   │
│   │   ├── ontology/       # Ontology Explorer
│   │   │   ├── page.tsx
│   │   │   └── [domain]/
│   │   │       └── page.tsx
│   │   │
│   │   └── settings/
│   │       ├── page.tsx
│   │       ├── organization/
│   │       ├── api-keys/
│   │       └── webhooks/
│   │
│   └── api/
│       └── [...proxy]/     # API proxy routes
│
├── components/
│   ├── ui/                 # Shadcn/ui components
│   ├── signals/
│   │   ├── SignalCard.tsx
│   │   ├── SignalList.tsx
│   │   ├── SignalDetail.tsx
│   │   ├── SignalChart.tsx
│   │   └── ConfidenceBar.tsx    # Visual confidence decomposition
│   ├── chat/
│   │   ├── ChatInterface.tsx     # Main chat component
│   │   ├── ChatMessage.tsx       # Message bubble with citations
│   │   ├── ChatInput.tsx         # Input with suggestions
│   │   ├── ChatToolOutput.tsx    # Tool execution display
│   │   └── ChatSidebar.tsx       # Session history
│   ├── search/
│   │   ├── SearchBar.tsx         # Deep search input
│   │   ├── SearchResults.tsx     # Ranked results
│   │   ├── SourceCard.tsx        # Source attribution
│   │   └── SearchFilters.tsx     # Domain/ontology filters
│   ├── recommendations/
│   │   ├── RecommendationCard.tsx
│   │   └── ActionableInsight.tsx
│   ├── contracts/
│   ├── analytics/
│   ├── ontology/
│   │   ├── OntologyBrowser.tsx
│   │   └── DomainSelector.tsx
│   ├── pwa/
│   │   ├── InstallPrompt.tsx     # PWA install prompt
│   │   ├── OfflineIndicator.tsx  # Offline status
│   │   └── PushNotification.tsx  # Push notification setup
│   └── layout/
│       ├── Header.tsx
│       ├── Sidebar.tsx
│       └── Footer.tsx
│
├── lib/
│   ├── api.ts              # API client
│   ├── auth.ts             # Auth utilities
│   ├── utils.ts            # Helper functions
│   ├── pwa.ts              # PWA registration & utilities
│   ├── push.ts             # Push notification client
│   └── hooks/
│       ├── useSignals.ts
│       ├── useContracts.ts
│       ├── useAnalytics.ts
│       ├── useChat.ts       # Chat hook with streaming
│       ├── useSearch.ts     # Deep search hook
│       └── usePWA.ts        # PWA install/update hooks
│
├── public/
│   ├── icons/              # PWA icons (192x192, 512x512, maskable)
│   ├── manifest.json       # PWA web app manifest
│   └── sw.js               # Compiled service worker
│
└── types/
    ├── signal.ts
    ├── contract.ts
    ├── chat.ts
    ├── search.ts
    ├── ontology.ts
    └── api.ts
```

#### 3.2.2 PWA Configuration

```json
// public/manifest.json
{
  "name": "ESIP - Enterprise Signal Intelligence",
  "short_name": "ESIP",
  "description": "Enterprise-grade signal intelligence at your fingertips",
  "start_url": "/dashboard",
  "display": "standalone",
  "background_color": "#0F172A",
  "theme_color": "#3B82F6",
  "orientation": "any",
  "icons": [
    { "src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png" },
    { "src": "/icons/icon-maskable.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable" }
  ],
  "categories": ["business", "productivity"],
  "shortcuts": [
    { "name": "Chat with ESIP", "url": "/dashboard/chat", "icons": [{"src": "/icons/chat.png"}] },
    { "name": "Search Signals", "url": "/dashboard/search", "icons": [{"src": "/icons/search.png"}] }
  ]
}
```

#### 3.2.3 Service Worker Strategy

```typescript
// Service worker caching strategy
const CACHE_STRATEGIES = {
  // App shell: Cache-first (HTML, CSS, JS bundles)
  appShell: 'CacheFirst',

  // API responses: Network-first with cache fallback
  apiCalls: 'NetworkFirst',

  // Signal data: Stale-while-revalidate (show cached, update in background)
  signalData: 'StaleWhileRevalidate',

  // Chat history: Cache-first (immutable once created)
  chatHistory: 'CacheFirst',

  // Ontology data: Cache-first with daily refresh
  ontologyData: 'CacheFirst',

  // Images/icons: Cache-first
  assets: 'CacheFirst'
};
```

---

## 4. Data Models & Schema Design

### 4.1 Core Domain Models

#### 4.1.1 Entity Relationship Diagram

```
┌──────────────────┐       ┌──────────────────┐       ┌──────────────────┐
│   Organization   │───────│      User        │───────│     OrgUser      │
│                  │  1:N  │                  │  M:N  │  (junction)      │
├──────────────────┤       ├──────────────────┤       ├──────────────────┤
│ id (PK)          │       │ id (PK)          │       │ org_id (FK)      │
│ name             │       │ auth0_id         │       │ user_id (FK)     │
│ slug             │       │ email            │       │ role             │
│ tier             │       │ name             │       │ created_at       │
│ settings (JSONB) │       │ status           │       └──────────────────┘
│ industry (FK)    │       └──────────────────┘
└──────────────────┘
        │
        │ 1:N
        ▼
┌──────────────────┐       ┌──────────────────┐       ┌──────────────────┐
│ SignalContract   │───────│     Signal       │───────│   SignalValue    │
│                  │  1:N  │                  │  1:N  │  (time-series)   │
├──────────────────┤       ├──────────────────┤       ├──────────────────┤
│ id (PK)          │       │ id (PK)          │       │ id (PK)          │
│ org_id (FK)      │       │ contract_id (FK) │       │ signal_id (FK)   │
│ ontology_id (FK) │       │ entity_id (FK)   │       │ timestamp        │
│ name             │       │ status           │       │ value (JSONB)    │
│ entity_type      │       │ confidence       │       │ confidence       │
│ schema (JSONB)   │       │ ml_score         │       │ ml_score         │
│ dimensions       │       │ recommendation   │       │ source_id (FK)   │
│ freshness_sla    │       │ last_updated     │       │ evidence_ids     │
│ confidence_min   │       │ metadata (JSONB) │       └──────────────────┘
│ temporal_rules   │       └──────────────────┘
│ industry_domain  │               │
└──────────────────┘               │ M:N
        │                          ▼
        │              ┌──────────────────┐       ┌──────────────────┐
        │              │    Evidence      │───────│     Entity       │
        │              │                  │  M:N  │                  │
        │              ├──────────────────┤       ├──────────────────┤
        │              │ id (PK)          │       │ id (PK)          │
        │              │ source_id (FK)   │       │ org_id (FK)      │
        │              │ content          │       │ type             │
        │              │ extracted_at     │       │ name             │
        │              │ url              │       │ ontology_id (FK) │
        │              │ snippet          │       │ canonical_id     │
        │              │ confidence       │       │ aliases (JSONB)  │
        │              └──────────────────┘       │ metadata (JSONB) │
        │                                         └──────────────────┘
        ▼
┌──────────────────┐       ┌──────────────────┐       ┌──────────────────┐
│ IndustryOntology │───────│ DomainTaxonomy   │───────│ OntologyNode     │
│                  │  1:N  │                  │  1:N  │                  │
├──────────────────┤       ├──────────────────┤       ├──────────────────┤
│ id (PK)          │       │ id (PK)          │       │ id (PK)          │
│ industry_code    │       │ ontology_id (FK) │       │ taxonomy_id (FK) │
│ name             │       │ domain_name      │       │ parent_id (FK)   │
│ description      │       │ entity_types     │       │ label            │
│ version          │       │ signal_types     │       │ properties       │
│ schema (JSONB)   │       │ measures         │       │ embedding        │
│ regions          │       │ benchmarks       │       │ depth            │
└──────────────────┘       └──────────────────┘       └──────────────────┘

┌──────────────────┐       ┌──────────────────┐       ┌──────────────────┐
│ ChatSession      │───────│  ChatMessage     │       │ MLModelRegistry  │
│                  │  1:N  │                  │       │                  │
├──────────────────┤       ├──────────────────┤       ├──────────────────┤
│ id (PK)          │       │ id (PK)          │       │ id (PK)          │
│ org_id (FK)      │       │ session_id (FK)  │       │ name             │
│ user_id (FK)     │       │ role             │       │ version          │
│ title            │       │ content          │       │ model_type       │
│ context (JSONB)  │       │ tool_calls       │       │ artifact_path    │
│ industry_domain  │       │ citations        │       │ metrics (JSONB)  │
│ status           │       │ created_at       │       │ status           │
└──────────────────┘       └──────────────────┘       │ trained_at       │
                                                      └──────────────────┘

┌──────────────────┐       ┌──────────────────┐
│  Recommendation  │       │     Source       │
│                  │       │                  │
├──────────────────┤       ├──────────────────┤
│ id (PK)          │       │ id (PK)          │
│ signal_id (FK)   │       │ org_id (FK)      │
│ org_id (FK)      │       │ name             │
│ type             │       │ type             │
│ title            │       │ config (JSONB)   │
│ description      │       │ health_score     │
│ confidence       │       │ last_fetch       │
│ action_items     │       │ fetch_interval   │
│ risk_level       │       │ industry_tags    │
│ evidence_ids     │       │ ontology_ids     │
│ status           │       └──────────────────┘
│ created_at       │
└──────────────────┘
```

### 4.2 Database Schema (PostgreSQL)

#### 4.2.1 Core Tables

```sql
-- Organizations (with industry linkage)
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) NOT NULL UNIQUE,
    tier VARCHAR(50) NOT NULL DEFAULT 'free',
    industry_ontology_id UUID REFERENCES industry_ontologies(id),
    settings JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_organizations_slug ON organizations(slug) WHERE deleted_at IS NULL;

-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    auth0_id VARCHAR(255) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255),
    avatar_url TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login_at TIMESTAMPTZ
);

CREATE INDEX idx_users_auth0_id ON users(auth0_id);
CREATE INDEX idx_users_email ON users(email);

-- Organization-User relationship
CREATE TABLE org_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL DEFAULT 'member',
    permissions JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(org_id, user_id)
);

CREATE INDEX idx_org_users_org_id ON org_users(org_id);
CREATE INDEX idx_org_users_user_id ON org_users(user_id);

-- Signal Contracts (enterprise-grade, ontology-aware)
CREATE TABLE signal_contracts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    ontology_id UUID REFERENCES industry_ontologies(id),
    taxonomy_id UUID REFERENCES domain_taxonomies(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    entity_type VARCHAR(100) NOT NULL,
    industry_domain VARCHAR(100),
    schema JSONB NOT NULL,
    dimensions JSONB NOT NULL DEFAULT '[]',
    measures JSONB NOT NULL DEFAULT '[]',
    freshness_sla_hours INTEGER NOT NULL DEFAULT 24,
    confidence_threshold DECIMAL(3,2) NOT NULL DEFAULT 0.85,
    temporal_rules JSONB NOT NULL DEFAULT '{}',
    regional_config JSONB NOT NULL DEFAULT '{}',
    recommendation_config JSONB NOT NULL DEFAULT '{}',
    ml_scoring_enabled BOOLEAN NOT NULL DEFAULT true,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    version INTEGER NOT NULL DEFAULT 1,
    catalog_template_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(org_id, name)
);

CREATE INDEX idx_signal_contracts_org_id ON signal_contracts(org_id);
CREATE INDEX idx_signal_contracts_entity_type ON signal_contracts(entity_type);
CREATE INDEX idx_signal_contracts_status ON signal_contracts(status);
CREATE INDEX idx_signal_contracts_industry ON signal_contracts(industry_domain);
CREATE INDEX idx_signal_contracts_ontology ON signal_contracts(ontology_id);

-- Entities (resolved business entities, ontology-linked)
CREATE TABLE entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    type VARCHAR(100) NOT NULL,
    name VARCHAR(500) NOT NULL,
    canonical_id VARCHAR(255),
    ontology_node_id UUID REFERENCES ontology_nodes(id),
    aliases JSONB NOT NULL DEFAULT '[]',
    metadata JSONB NOT NULL DEFAULT '{}',
    embedding vector(1536),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_entities_org_id ON entities(org_id);
CREATE INDEX idx_entities_type ON entities(type);
CREATE INDEX idx_entities_canonical_id ON entities(canonical_id);
CREATE INDEX idx_entities_name_gin ON entities USING gin(to_tsvector('english', name));
CREATE INDEX idx_entities_embedding ON entities USING ivfflat(embedding vector_cosine_ops) WITH (lists = 100);

-- Signals (with ML scoring and recommendations)
CREATE TABLE signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contract_id UUID NOT NULL REFERENCES signal_contracts(id) ON DELETE CASCADE,
    entity_id UUID REFERENCES entities(id) ON DELETE SET NULL,
    dimensions JSONB NOT NULL DEFAULT '{}',
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    current_confidence DECIMAL(3,2),
    ml_anomaly_score DECIMAL(3,2),
    ml_trend_direction VARCHAR(20),
    last_value JSONB,
    last_updated_at TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_signals_contract_id ON signals(contract_id);
CREATE INDEX idx_signals_entity_id ON signals(entity_id);
CREATE INDEX idx_signals_status ON signals(status);
CREATE INDEX idx_signals_dimensions_gin ON signals USING gin(dimensions);
CREATE INDEX idx_signals_active ON signals(contract_id) WHERE status = 'active';

-- Signal Values (time-series data with ML scores)
CREATE TABLE signal_values (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    signal_id UUID NOT NULL REFERENCES signals(id) ON DELETE CASCADE,
    timestamp TIMESTAMPTZ NOT NULL,
    value JSONB NOT NULL,
    confidence DECIMAL(3,2) NOT NULL,
    ml_score DECIMAL(3,2),
    source_id UUID,
    evidence_ids UUID[] NOT NULL DEFAULT '{}',
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_signal_values_signal_id ON signal_values(signal_id);
CREATE INDEX idx_signal_values_timestamp ON signal_values(timestamp DESC);
CREATE INDEX idx_signal_values_signal_timestamp ON signal_values(signal_id, timestamp DESC);

-- Sources (industry-tagged, ontology-linked)
CREATE TABLE sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(100) NOT NULL,
    config JSONB NOT NULL DEFAULT '{}',
    auth_config JSONB NOT NULL DEFAULT '{}',
    health_score DECIMAL(3,2) NOT NULL DEFAULT 1.00,
    last_fetch_at TIMESTAMPTZ,
    last_success_at TIMESTAMPTZ,
    fetch_interval_minutes INTEGER NOT NULL DEFAULT 60,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    error_count INTEGER NOT NULL DEFAULT 0,
    industry_tags JSONB NOT NULL DEFAULT '[]',
    ontology_ids JSONB NOT NULL DEFAULT '[]',
    reliability_score DECIMAL(3,2) NOT NULL DEFAULT 0.80,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_sources_org_id ON sources(org_id);
CREATE INDEX idx_sources_type ON sources(type);
CREATE INDEX idx_sources_status ON sources(status);
CREATE INDEX idx_sources_active ON sources(org_id) WHERE status = 'active';
CREATE INDEX idx_sources_industry_tags ON sources USING gin(industry_tags);

-- Evidence (provenance/lineage with embeddings)
CREATE TABLE evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID REFERENCES sources(id) ON DELETE SET NULL,
    content TEXT NOT NULL,
    snippet TEXT,
    url TEXT,
    document_type VARCHAR(100),
    extracted_at TIMESTAMPTZ NOT NULL,
    confidence DECIMAL(3,2) NOT NULL DEFAULT 0.80,
    metadata JSONB NOT NULL DEFAULT '{}',
    embedding vector(1536),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_evidence_source_id ON evidence(source_id);
CREATE INDEX idx_evidence_extracted_at ON evidence(extracted_at DESC);
CREATE INDEX idx_evidence_embedding ON evidence USING ivfflat(embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_evidence_search ON evidence USING gin(to_tsvector('english', content));

-- Audit Logs
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id UUID,
    changes JSONB NOT NULL DEFAULT '{}',
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_org_id ON audit_logs(org_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at DESC);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);

-- API Keys
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    key_hash VARCHAR(255) NOT NULL UNIQUE,
    key_prefix VARCHAR(10) NOT NULL,
    permissions JSONB NOT NULL DEFAULT '[]',
    rate_limit INTEGER NOT NULL DEFAULT 1000,
    expires_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_api_keys_key_hash ON api_keys(key_hash);
CREATE INDEX idx_api_keys_org_id ON api_keys(org_id);
```

#### 4.2.2 Industry Ontology Tables

```sql
-- Industry Ontologies (top-level industry definitions)
CREATE TABLE industry_ontologies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    industry_code VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    schema JSONB NOT NULL DEFAULT '{}',
    regions JSONB NOT NULL DEFAULT '[]',
    default_signal_types JSONB NOT NULL DEFAULT '[]',
    default_entity_types JSONB NOT NULL DEFAULT '[]',
    benchmarks JSONB NOT NULL DEFAULT '{}',
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Industry codes: fintech, fmcg, energy, real_estate, agriculture,
--   manufacturing, healthcare, logistics, telecom, retail, education

-- Domain Taxonomies (sub-domains within an industry)
CREATE TABLE domain_taxonomies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ontology_id UUID NOT NULL REFERENCES industry_ontologies(id) ON DELETE CASCADE,
    domain_name VARCHAR(255) NOT NULL,
    description TEXT,
    entity_types JSONB NOT NULL DEFAULT '[]',
    signal_types JSONB NOT NULL DEFAULT '[]',
    measures JSONB NOT NULL DEFAULT '[]',
    dimensions JSONB NOT NULL DEFAULT '[]',
    benchmarks JSONB NOT NULL DEFAULT '{}',
    freshness_requirements JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(ontology_id, domain_name)
);

CREATE INDEX idx_domain_taxonomies_ontology_id ON domain_taxonomies(ontology_id);

-- Ontology Nodes (hierarchical knowledge graph within a taxonomy)
CREATE TABLE ontology_nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    taxonomy_id UUID NOT NULL REFERENCES domain_taxonomies(id) ON DELETE CASCADE,
    parent_id UUID REFERENCES ontology_nodes(id) ON DELETE CASCADE,
    label VARCHAR(500) NOT NULL,
    node_type VARCHAR(100) NOT NULL,
    properties JSONB NOT NULL DEFAULT '{}',
    embedding vector(1536),
    depth INTEGER NOT NULL DEFAULT 0,
    path JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_ontology_nodes_taxonomy_id ON ontology_nodes(taxonomy_id);
CREATE INDEX idx_ontology_nodes_parent_id ON ontology_nodes(parent_id);
CREATE INDEX idx_ontology_nodes_type ON ontology_nodes(node_type);
CREATE INDEX idx_ontology_nodes_embedding ON ontology_nodes USING ivfflat(embedding vector_cosine_ops) WITH (lists = 50);

-- Enterprise Signal Catalog (pre-built signal templates per industry)
CREATE TABLE signal_catalog (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ontology_id UUID NOT NULL REFERENCES industry_ontologies(id) ON DELETE CASCADE,
    taxonomy_id UUID REFERENCES domain_taxonomies(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    entity_type VARCHAR(100) NOT NULL,
    default_schema JSONB NOT NULL,
    default_dimensions JSONB NOT NULL DEFAULT '[]',
    default_measures JSONB NOT NULL DEFAULT '[]',
    recommended_freshness_hours INTEGER NOT NULL DEFAULT 24,
    recommended_confidence DECIMAL(3,2) NOT NULL DEFAULT 0.85,
    recommended_sources JSONB NOT NULL DEFAULT '[]',
    complexity_tier VARCHAR(20) NOT NULL DEFAULT 'standard',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_signal_catalog_ontology ON signal_catalog(ontology_id);
CREATE INDEX idx_signal_catalog_entity_type ON signal_catalog(entity_type);
```

#### 4.2.3 Chat & ML Tables

```sql
-- Chat Sessions
CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(500),
    industry_domain VARCHAR(100),
    context JSONB NOT NULL DEFAULT '{}',
    signal_refs JSONB NOT NULL DEFAULT '[]',
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    message_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_chat_sessions_org_user ON chat_sessions(org_id, user_id);
CREATE INDEX idx_chat_sessions_updated ON chat_sessions(updated_at DESC);

-- Chat Messages
CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    tool_calls JSONB DEFAULT '[]',
    tool_results JSONB DEFAULT '[]',
    citations JSONB DEFAULT '[]',
    signal_refs JSONB DEFAULT '[]',
    confidence DECIMAL(3,2),
    token_count INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_chat_messages_session ON chat_messages(session_id, created_at);

-- ML Model Registry
CREATE TABLE ml_model_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    version VARCHAR(50) NOT NULL,
    model_type VARCHAR(100) NOT NULL,
    artifact_path TEXT NOT NULL,
    input_schema JSONB NOT NULL DEFAULT '{}',
    output_schema JSONB NOT NULL DEFAULT '{}',
    metrics JSONB NOT NULL DEFAULT '{}',
    hyperparameters JSONB NOT NULL DEFAULT '{}',
    training_data_info JSONB NOT NULL DEFAULT '{}',
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    trained_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(name, version)
);

-- Model types: anomaly_detector, signal_scorer, entity_resolver,
--   trend_forecaster, cluster_engine, confidence_calibrator

CREATE INDEX idx_ml_models_name ON ml_model_registry(name);
CREATE INDEX idx_ml_models_type ON ml_model_registry(model_type);
CREATE INDEX idx_ml_models_status ON ml_model_registry(status);

-- Recommendations
CREATE TABLE recommendations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    signal_id UUID REFERENCES signals(id) ON DELETE SET NULL,
    type VARCHAR(100) NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    confidence DECIMAL(3,2) NOT NULL,
    action_items JSONB NOT NULL DEFAULT '[]',
    risk_level VARCHAR(20),
    opportunity_score DECIMAL(3,2),
    evidence_ids UUID[] NOT NULL DEFAULT '{}',
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Recommendation types: risk_alert, opportunity, trend_insight,
--   anomaly_action, competitive_signal, regulatory_change

CREATE INDEX idx_recommendations_org ON recommendations(org_id);
CREATE INDEX idx_recommendations_signal ON recommendations(signal_id);
CREATE INDEX idx_recommendations_type ON recommendations(type);
CREATE INDEX idx_recommendations_status ON recommendations(status);
```

### 4.3 Key SQLAlchemy Models

> Full SQLAlchemy models for all entities are defined in `backend/models/`. Key models shown below.

#### 4.3.1 Signal Contract Model (Enterprise-Grade)

```python
# backend/models/signal_contract.py
from sqlalchemy import Column, String, Integer, ForeignKey, Numeric, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from backend.models.base import Base, TimestampMixin
import uuid

class SignalContract(Base, TimestampMixin):
    __tablename__ = "signal_contracts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    ontology_id = Column(UUID(as_uuid=True), ForeignKey("industry_ontologies.id"))
    taxonomy_id = Column(UUID(as_uuid=True), ForeignKey("domain_taxonomies.id"))
    name = Column(String(255), nullable=False)
    description = Column(Text)
    entity_type = Column(String(100), nullable=False)
    industry_domain = Column(String(100))
    schema = Column(JSONB, nullable=False)
    dimensions = Column(JSONB, nullable=False, default=list)
    measures = Column(JSONB, nullable=False, default=list)
    freshness_sla_hours = Column(Integer, nullable=False, default=24)
    confidence_threshold = Column(Numeric(3, 2), nullable=False, default=0.85)
    temporal_rules = Column(JSONB, nullable=False, default=dict)
    regional_config = Column(JSONB, nullable=False, default=dict)
    recommendation_config = Column(JSONB, nullable=False, default=dict)
    ml_scoring_enabled = Column(Boolean, nullable=False, default=True)
    status = Column(String(50), nullable=False, default="active")
    version = Column(Integer, nullable=False, default=1)
    catalog_template_id = Column(UUID(as_uuid=True))

    organization = relationship("Organization", back_populates="signal_contracts")
    ontology = relationship("IndustryOntology")
    taxonomy = relationship("DomainTaxonomy")
    signals = relationship("Signal", back_populates="contract", cascade="all, delete-orphan")
```

#### 4.3.2 Signal Model (ML-Enhanced)

```python
# backend/models/signal.py
from sqlalchemy import Column, String, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP
from sqlalchemy.orm import relationship
from backend.models.base import Base, TimestampMixin
import uuid

class Signal(Base, TimestampMixin):
    __tablename__ = "signals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id = Column(UUID(as_uuid=True), ForeignKey("signal_contracts.id", ondelete="CASCADE"), nullable=False)
    entity_id = Column(UUID(as_uuid=True), ForeignKey("entities.id", ondelete="SET NULL"))
    dimensions = Column(JSONB, nullable=False, default=dict)
    status = Column(String(50), nullable=False, default="active")
    current_confidence = Column(Numeric(3, 2))
    ml_anomaly_score = Column(Numeric(3, 2))
    ml_trend_direction = Column(String(20))
    last_value = Column(JSONB)
    last_updated_at = Column(TIMESTAMP(timezone=True))
    metadata = Column(JSONB, nullable=False, default=dict)

    contract = relationship("SignalContract", back_populates="signals")
    entity = relationship("Entity", back_populates="signals")
    values = relationship("SignalValue", back_populates="signal", cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="signal")
```

---

## 5. API Contracts

### 5.1 API Design Principles

1. **RESTful** — Resources as nouns, HTTP verbs for actions
2. **Versioned** — All endpoints under `/api/v1/`
3. **Consistent** — Uniform response format with confidence decomposition
4. **Documented** — OpenAPI/Swagger auto-generated
5. **Paginated** — All list endpoints support pagination
6. **Filterable** — Query parameters for filtering
7. **Ontology-Aware** — Endpoints support industry/domain context
8. **Recommendation-First** — Signal responses include actionable recommendations

### 5.2 Response Format

#### Success Response
```json
{
  "success": true,
  "data": { },
  "meta": { "request_id": "uuid", "timestamp": "ISO8601", "industry_context": "fintech" }
}
```

#### Error Response
```json
{
  "success": false,
  "error": { "code": "ERROR_CODE", "message": "Human readable message", "details": { } },
  "meta": { "request_id": "uuid", "timestamp": "ISO8601" }
}
```

#### Paginated Response
```json
{
  "success": true,
  "data": [ ],
  "pagination": { "page": 1, "page_size": 20, "total_items": 150, "total_pages": 8, "has_next": true, "has_prev": false },
  "meta": { }
}
```

### 5.3 Core API Endpoints

#### 5.3.1 Signal Contracts

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/contracts` | List contracts (filterable by industry/domain) |
| `POST` | `/api/v1/contracts` | Create contract (ontology-validated) |
| `GET` | `/api/v1/contracts/{id}` | Get contract with recommendations config |
| `PUT` | `/api/v1/contracts/{id}` | Update contract |
| `DELETE` | `/api/v1/contracts/{id}` | Delete contract |
| `POST` | `/api/v1/contracts/{id}/activate` | Activate contract |
| `POST` | `/api/v1/contracts/{id}/deactivate` | Deactivate contract |
| `POST` | `/api/v1/contracts/from-catalog` | Create from enterprise catalog template |

#### 5.3.2 Signals

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/signals` | List signals with ML scores |
| `GET` | `/api/v1/signals/{id}` | Get signal with confidence decomposition |
| `GET` | `/api/v1/signals/{id}/history` | Get signal time-series |
| `GET` | `/api/v1/signals/{id}/evidence` | Get signal evidence chain |
| `GET` | `/api/v1/signals/{id}/recommendations` | Get signal recommendations |
| `POST` | `/api/v1/signals/query` | Query signals with ontology filters |
| `POST` | `/api/v1/signals/synthesize` | On-demand signal synthesis |

#### 5.3.3 AI Chat Agent

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/chat/sessions` | Create new chat session |
| `GET` | `/api/v1/chat/sessions` | List chat sessions |
| `GET` | `/api/v1/chat/sessions/{id}` | Get chat session with messages |
| `POST` | `/api/v1/chat/sessions/{id}/messages` | Send message (streaming SSE) |
| `DELETE` | `/api/v1/chat/sessions/{id}` | Delete chat session |
| `POST` | `/api/v1/chat/sessions/{id}/feedback` | Provide feedback on response |

#### 5.3.4 Deep Search

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/search` | Execute deep live search |
| `POST` | `/api/v1/search/discover` | Discover new sources for a topic |
| `GET` | `/api/v1/search/history` | Get search history |

#### 5.3.5 Analytics

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/analytics/trends` | Get signal trends (ML-enhanced) |
| `GET` | `/api/v1/analytics/anomalies` | Get ML-detected anomalies |
| `POST` | `/api/v1/analytics/compare` | Compare signals |
| `GET` | `/api/v1/analytics/coverage` | Get signal coverage report |
| `GET` | `/api/v1/analytics/recommendations` | Get all active recommendations |
| `GET` | `/api/v1/analytics/forecast` | Get ML trend forecasts |
| `GET` | `/api/v1/analytics/industry/{code}` | Get industry-specific analytics |

#### 5.3.6 Ontology & Catalog

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/ontology/industries` | List available industries |
| `GET` | `/api/v1/ontology/industries/{code}` | Get industry detail |
| `GET` | `/api/v1/ontology/industries/{code}/taxonomies` | Get domain taxonomies |
| `GET` | `/api/v1/ontology/industries/{code}/catalog` | Get signal catalog |
| `GET` | `/api/v1/ontology/nodes/{id}` | Get ontology node |
| `POST` | `/api/v1/ontology/search` | Semantic search across ontologies |

#### 5.3.7 Sources

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/sources` | List sources (filterable by industry) |
| `POST` | `/api/v1/sources` | Create source |
| `GET` | `/api/v1/sources/{id}` | Get source |
| `PUT` | `/api/v1/sources/{id}` | Update source |
| `DELETE` | `/api/v1/sources/{id}` | Delete source |
| `POST` | `/api/v1/sources/{id}/test` | Test source connectivity |
| `GET` | `/api/v1/sources/{id}/health` | Get source health |

### 5.4 Key Pydantic Schemas

```python
# backend/schemas/signal.py
class SignalContractCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    entity_type: str = Field(..., min_length=1, max_length=100)
    industry_domain: Optional[str] = None
    ontology_id: Optional[UUID] = None
    taxonomy_id: Optional[UUID] = None
    schema: dict[str, Any]
    dimensions: list[dict[str, Any]] = []
    measures: list[str] = []
    freshness_sla_hours: int = Field(default=24, ge=1, le=720)
    confidence_threshold: float = Field(default=0.85, ge=0.5, le=1.0)
    temporal_rules: dict[str, Any] = {}
    recommendation_config: dict[str, Any] = {}
    ml_scoring_enabled: bool = True

class ConfidenceDecomposition(BaseModel):
    source_coverage: float
    freshness: float
    agreement: float
    ml_score: Optional[float] = None

class ConfidenceResponse(BaseModel):
    overall: float
    decomposition: ConfidenceDecomposition

class MLInsightsResponse(BaseModel):
    anomaly_score: Optional[float] = None
    trend_direction: Optional[str] = None
    forecast_next_24h: Optional[dict[str, Any]] = None

class RecommendationResponse(BaseModel):
    id: UUID
    type: str
    title: str
    description: str
    confidence: float
    action_items: list[str]
    risk_level: Optional[str] = None

class SignalResponse(BaseModel):
    id: UUID
    contract_name: str
    industry_domain: Optional[str]
    current_value: Optional[dict[str, Any]]
    confidence: ConfidenceResponse
    ml_insights: MLInsightsResponse
    recommendations: list[RecommendationResponse] = []
    evidence_count: int = 0
    last_updated: Optional[datetime]

class SignalSynthesizeRequest(BaseModel):
    question: str = Field(..., min_length=10, max_length=1000)
    context: dict[str, Any] = {}
    industry: Optional[str] = None
    max_sources: int = Field(default=10, ge=1, le=20)
    min_confidence: float = Field(default=0.85, ge=0.5, le=1.0)
    include_recommendations: bool = True

# backend/schemas/chat.py
class ChatMessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)
    context_override: Optional[dict[str, Any]] = None

# backend/schemas/search.py
class DeepSearchRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=1000)
    industry: Optional[str] = None
    search_depth: str = Field(default="deep", pattern="^(quick|standard|deep)$")
    max_sources: int = Field(default=10, ge=1, le=30)
    include_live: bool = True
    semantic_expansion: bool = True
    filters: Optional[dict[str, Any]] = None
```

---

## 6. Signal Processing Pipeline

### 6.1 Pipeline Overview (ML-Enhanced)

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  ACQUIRE    │ -> │   REFINE    │ -> │  ML SCORE   │ -> │  SYNTHESIZE │ -> │   DELIVER   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
     │                   │                   │                   │                   │
     ▼                   ▼                   ▼                   ▼                   ▼
 • Fetch data       • Normalize         • Anomaly detect    • Detect change     • Store signal
 • Deep search      • Entity resolve    • Confidence ML     • Recommendations   • Trigger alerts
 • Rate limit       • Ontology enrich   • Trend forecast    • Track lineage     • Update cache
 • Error handle     • Domain validate   • Clustering        • Score confidence  • Push notify
```

> Detailed pipeline code specifications for Acquisition Engine, Refinement Engine (Ontology-Enhanced), Signal Engine (ML-Powered), and On-Demand Synthesis are provided in the corresponding `backend/services/` modules. See Section 7-9 for Chat Agent, Deep Search, and ML Engine specifications.

---

## 7. AI Chat Agent

### 7.1 Architecture

The AI Chat Agent is a conversational layer on top of all ESIP services. It provides natural language access to signals, search, analytics, and recommendations.

```
User Message → Context Manager → LLM Reasoning → Tool Selection → Tool Execution → Response Stream
                                                      │
                          ┌───────────────────────────┼─────────────────────────┐
                          │              │              │              │         │
                     Signal Query   Deep Search   Analytics   Ontology Lookup   Contract Mgmt
```

### 7.2 Agent Tools

| Tool | Purpose | When Used |
|------|---------|-----------|
| `search_signals` | Query existing signals | User asks about current values |
| `deep_search` | Multi-source live search | No existing coverage |
| `synthesize_signal` | Create signal from live data | Gap discovered |
| `get_analytics` | Trends, anomalies, forecasts | Pattern/prediction questions |
| `get_recommendations` | Actionable advice | "What should I do?" questions |
| `browse_ontology` | Domain context lookup | Industry-specific questions |
| `create_contract` | Create new signal contract | User wants to track something |

### 7.3 Streaming Response (SSE)

```
event: thinking → event: tool_call → event: tool_result → event: content → event: citation → event: recommendation → event: done
```

---

## 8. Deep Live Search Engine

### 8.1 Architecture

Multi-source parallel search with semantic ranking and ontology expansion.

```
Query → Query Expansion (ontology) → Parallel Source Fetch → Semantic Ranking → Result Synthesis
            │                              │                        │
     Synonyms, related concepts    Internal + Live + Cached    Relevance + Reliability + Freshness
```

### 8.2 Ranking Factors

| Factor | Weight | Description |
|--------|--------|-------------|
| Semantic relevance | 40% | Embedding cosine similarity |
| Source reliability | 20% | Historical accuracy score |
| Freshness | 20% | Time decay function |
| Ontology alignment | 20% | Industry domain match bonus |

---

## 9. Lightweight ML Engine

### 9.1 Model Types

| Model | Algorithm | Size | Inference |
|-------|-----------|------|-----------|
| Anomaly Detector | Isolation Forest + statistical | ~10MB | <50ms |
| Signal Scorer | Gradient Boosted Trees | ~5MB | <20ms |
| Entity Resolver | Sentence Transformers (small) | ~50MB | <80ms |
| Trend Forecaster | Prophet-lite / ARIMA | ~2MB | <30ms |
| Cluster Engine | K-Means + DBSCAN | ~5MB | <40ms |

### 9.2 Simulation Mode (Starter Tier)

Generates realistic simulated signal data based on industry ontology patterns, historical benchmarks, and configurable volatility. Allows organizations to explore ESIP before connecting live sources.

---

## 10. Industry Ontology & Enterprise Signal Catalog

### 10.1 Supported Industries

| Industry | Domains | Catalog Signals |
|----------|---------|-----------------|
| Fintech | Payments, Lending, Regulatory, Insurance | 15+ |
| FMCG | Pricing, Supply Chain, Distribution | 12+ |
| Energy | Oil & Gas, Power, Renewable | 10+ |
| Real Estate | Commercial, Residential, Land | 8+ |
| Agriculture | Crop Pricing, Input Costs, Weather | 10+ |
| Manufacturing | Production, Quality, Supply | 8+ |
| Healthcare | Pharma, Hospital, Insurance | 8+ |
| Logistics | Shipping, Warehousing, Fleet | 8+ |
| Telecom | Network, Subscriber, Regulatory | 6+ |
| Retail | POS, Inventory, Pricing | 8+ |

### 10.2 Ontology Structure

```
Industry → Domain Taxonomies → Ontology Nodes (hierarchical)
                                    ├── Entity Types
                                    ├── Signal Types
                                    ├── Measures & Dimensions
                                    └── Benchmarks
```

---

## 11. Integration Specifications

### 11.1 Authentication (Auth0)

Standard Auth0 JWT validation with RS256 + JWKS rotation. Extended RBAC includes chat, search, and ontology permissions.

### 11.2 Webhook Events

| Event | Trigger |
|-------|---------|
| `signal.created` | New signal instantiated |
| `signal.updated` | Signal value changed |
| `signal.anomaly` | ML anomaly detected |
| `recommendation.new` | New recommendation generated |
| `source.unhealthy` | Source health drops |
| `ontology.updated` | Industry ontology updated |

### 11.3 LLM Integration

OpenAI GPT-4 Turbo for: signal synthesis, chat agent reasoning, intent parsing, recommendation generation.

---

## 12. Security Requirements

| Area | Requirements |
|------|-------------|
| Auth | JWT RS256, 1h expiry, JWKS rotation, API key SHA-256 |
| Data | TLS 1.3, PostgreSQL TDE, Azure Key Vault, PII hashing |
| API | Pydantic strict, parameterized queries, CORS whitelist, 10MB limit |
| Chat | Session isolation per org+user, 30 msg/min rate limit |
| Search | 10 deep searches/min, source respect rate limits |
| ML | Signed model artifacts, no PII in training data |

---

## 13. Performance Requirements

### 13.1 Latency Targets

| Operation | P50 | P95 | P99 |
|-----------|-----|-----|-----|
| Signal read | 50ms | 100ms | 200ms |
| Signal query | 100ms | 300ms | 500ms |
| On-demand synthesis | 3s | 8s | 15s |
| Chat (first token) | 500ms | 1.5s | 3s |
| Deep search | 2s | 5s | 10s |
| ML inference | 20ms | 50ms | 100ms |
| Ontology query | 10ms | 50ms | 100ms |

### 13.2 Caching Strategy

| Cache | TTL | Purpose |
|-------|-----|---------|
| Signal current | 5 min | Current values |
| Contract | 1 hour | Definitions |
| Chat context | 30 min | Active sessions |
| Ontology | 24 hours | Industry data |
| Search results | 10 min | Recent searches |
| JWKS | 1 hour | JWT validation |

---

## 14. Infrastructure Specification

### 14.1 Cloud Resources

| Resource | Service | Config |
|----------|---------|--------|
| Compute | Azure Container Apps | 0.5-4 vCPU, 1-8 GB RAM |
| Database | Neon PostgreSQL + pgvector | Serverless |
| Cache | Upstash Redis | Serverless |
| Storage | Azure Blob | Hot tier (ML models, evidence) |
| Secrets | Azure Key Vault | Standard |
| CDN | Azure Front Door | PWA static assets |

### 14.2 Docker (Development)

Uses `pgvector/pgvector:pg16` image for vector support. ML models stored in mounted volume.

---

## 15. Observability & Monitoring

Key metrics tracked: HTTP requests, signal confidence, chat tool calls, search duration, ML inference time, anomalies detected, recommendations generated/actioned.

### Alerting Rules

| Alert | Condition | Severity |
|-------|-----------|----------|
| High error rate | 5xx > 5% for 5 min | Critical |
| High latency | P95 > 2s for 5 min | Warning |
| Chat failures | > 5% fail for 10 min | Warning |
| ML model stale | No retrain for 7 days | Info |
| Confidence drop | Avg < 0.80 for 1 hour | Warning |

---

## 16. Testing Requirements

### Coverage Targets

| Component | Minimum |
|-----------|---------|
| API endpoints | 90% |
| Services | 85% |
| Chat Agent | 85% |
| Deep Search | 85% |
| ML Models | 80% |
| Overall | 80% |

---

## 17. Deployment Specification

| Environment | URL |
|-------------|-----|
| Development | localhost:8000 |
| Staging | staging-api.esip.io |
| Production | api.esip.io |
| PWA | app.esip.io |

CI/CD via GitHub Actions → Azure Container Apps. Database migrations via Alembic.

---

## 18. Technical Constraints & Boundaries

### 18.1 Hard Constraints

| Constraint | Value |
|------------|-------|
| Max DB connections | 20 (Neon) |
| Max request body | 10 MB |
| Max synthesis time | 30s |
| Chat rate limit | 30 msg/min |
| Search rate limit | 10/min |
| ML model max size | 100 MB |
| ML inference max | 100 ms |

### 18.2 Deferred to Phase 4

| Feature | Reason |
|---------|--------|
| Real-time streaming (Kafka) | Complexity |
| Multi-region deployment | Scale not needed |
| SOC 2 Compliance | Enterprise deals |
| GPU-based ML training | Heavy infrastructure |
| Voice interface | Complexity |

### 18.3 Technology Boundaries

| Category | Allowed | Not Allowed |
|----------|---------|-------------|
| Languages | Python, TypeScript | Java, Go, Rust |
| Databases | PostgreSQL + pgvector | MongoDB, Cassandra |
| Queue | Redis | Kafka, RabbitMQ |
| Search | Deep Search Engine (custom) | Elasticsearch |
| ML (inference) | scikit-learn, ONNX, lightweight PyTorch | GPU models, self-hosted LLMs |
| LLM | OpenAI API / Azure OpenAI | Self-hosted LLMs |
| Frontend | Next.js PWA | React Native, Flutter |

---

## 19. Glossary

| Term | Definition |
|------|------------|
| **Signal** | A verified change or observation with confidence, lineage, and ML scoring |
| **Signal Contract** | Enterprise-grade declarative spec validated against industry ontology |
| **Confidence** | Decomposed 0-1 score: source coverage + freshness + agreement + ML |
| **AI Chat Agent** | Conversational interface for natural language signal interaction |
| **Deep Live Search** | Multi-source parallel search with semantic ranking |
| **Industry Ontology** | Structured domain knowledge per industry vertical |
| **Domain Taxonomy** | Hierarchical classification within an industry |
| **Signal Catalog** | Pre-built, industry-validated signal contract templates |
| **Recommendation** | Actionable insight with confidence and action items |
| **ML Engine** | Lightweight CPU-based ML for anomaly detection, scoring, forecasting |
| **Simulation Mode** | Simulated data for starter tier exploration |
| **PWA** | Progressive Web Application — installable, offline-capable |
| **Ontology Node** | Single concept in the domain knowledge graph |
| **Evidence** | Raw data with provenance supporting a signal value |
| **Synthesis** | Creating signals from raw evidence using LLM + ML |
| **Lineage** | Traceable path from raw data to signal to recommendation |

---

**End of Technical Specification Definition v2.0**
