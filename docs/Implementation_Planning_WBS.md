# ESIP Implementation Planning & Work Breakdown Structure

**Document Version:** 2.0
**Last Updated:** February 9, 2026
**Status:** Approved for Implementation
**Classification:** Internal Engineering

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Implementation Phases Overview](#2-implementation-phases-overview)
3. [Phase 0: Strategy & Discovery](#3-phase-0-strategy--discovery)
4. [Phase 1: Foundation](#4-phase-1-foundation)
5. [Phase 2: Infrastructure Validation](#5-phase-2-infrastructure-validation)
6. [Phase 3: Product Construction (MVP)](#6-phase-3-product-construction-mvp)
7. [Phase 4: Scale & Hardening (Post-PMF)](#7-phase-4-scale--hardening-post-pmf)
8. [Work Breakdown Structure (WBS)](#8-work-breakdown-structure-wbs)
9. [Resource Allocation](#9-resource-allocation)
10. [Risk Management](#10-risk-management)
11. [Quality Gates](#11-quality-gates)
12. [Dependencies & Critical Path](#12-dependencies--critical-path)
13. [Communication Plan](#13-communication-plan)
14. [Success Metrics](#14-success-metrics)
15. [Appendices](#15-appendices)

---

## 1. Executive Summary

### 1.1 Purpose

This document provides a comprehensive implementation plan for the Enterprise Signal Intelligence Platform (ESIP). It defines:
- All work packages broken down to actionable tasks
- Dependencies between tasks
- Resource requirements and team allocation
- Timeline estimates
- Quality gates and acceptance criteria
- New work packages for: AI Chat Agent, Deep Live Search, Lightweight ML Engine, Industry Ontology System, PWA Setup, Recommendation Engine, and Simulation Mode

### 1.2 Implementation Philosophy

| Principle | Application |
|-----------|------------|
| **Ship Fast** | 2-week sprint cycles, daily deployments |
| **Build for Today** | No speculative architecture |
| **Rent Boring** | Use managed services for non-differentiators |
| **Own Core** | Build signal processing, ML models, chat agent, deep search in-house |
| **Validate Early** | User feedback after each phase |
| **Intelligence-First** | Every feature ships with ML scoring, recommendations, and ontology context |

### 1.3 Timeline Overview

```
Phase 0: Strategy & Discovery      [Week 1-2]        ████░░░░░░░░░░░░░░░░░░░░░░░░░░░░
Phase 1: Foundation                [Week 3-6]        ░░░░████████░░░░░░░░░░░░░░░░░░░░
Phase 2: Infrastructure Validation [Week 7-10]       ░░░░░░░░░░░░████████░░░░░░░░░░░░
Phase 3: Product Construction      [Week 11-26]      ░░░░░░░░░░░░░░░░░░░░████████████████████████████████
Phase 4: Scale & Hardening         [Post-PMF]        (Deferred)

Total MVP Timeline: 26 weeks (~6.5 months)
```

> Phase 3 expanded from 10 to 16 weeks to accommodate AI Chat Agent, Deep Live Search, Lightweight ML Engine, Industry Ontology System, PWA infrastructure, Recommendation Engine, and Simulation Mode — all IN SCOPE for MVP.

### 1.4 Team Structure

| Role | Count | Responsibility |
|------|-------|----------------|
| Tech Lead / CTO | 1 | Architecture, decisions, code review, ML oversight |
| Backend Engineer | 2 | API, services, data layer, ML integration |
| ML / Intelligence Engineer | 1 | ML models, ontology, search ranking, recommendations |
| Frontend Engineer | 1 | PWA, chat UI, search UI, dashboards |
| DevOps Engineer | 0.5 | Infrastructure, CI/CD |
| Product Manager | 0.5 | Requirements, prioritization |

**Total Team Size:** 6 FTEs

> Added ML / Intelligence Engineer role to handle lightweight ML models, ontology system, deep search ranking, and recommendation engine.

---

## 2. Implementation Phases Overview

### 2.1 Phase Definitions

| Phase | Name | Goal | Duration |
|-------|------|------|----------|
| **0** | Strategy & Discovery | Define scope, validate assumptions, ontology design | 2 weeks |
| **1** | Foundation | Identity, auth, data, runtime, pgvector | 4 weeks |
| **2** | Infrastructure Validation | Pre-prod environment, CI/CD, PWA setup | 4 weeks |
| **3** | Product Construction | Core features + chat + search + ML + ontology + PWA | 16 weeks |
| **4** | Scale & Hardening | Post-PMF optimization | Deferred |

### 2.2 Phase Gate Criteria

Each phase must pass these criteria before advancing:

| Phase | Exit Criteria |
|-------|---------------|
| **0** | Technical spec signed off, industry ontology v1 designed, risks identified |
| **1** | Auth working, DB + pgvector migrations running, basic CRUD |
| **2** | Staging deployed, CI/CD green, monitoring active, PWA installable |
| **3** | Core user job works E2E, chat agent functional, search returns results, ML scores active, 10 beta users |
| **4** | 1000 users, P95 < 500ms, 99.9% uptime |

### 2.3 Decision Framework

Before ANY implementation decision:

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Does this help ship a feature in the next 30 days?       │
│    → NO: DEFER                                              │
│                                                             │
│ 2. Does this reduce existential risk (security, data loss)? │
│    → YES: IMPLEMENT NOW                                     │
│                                                             │
│ 3. Can this be rented or deferred?                          │
│    → YES: RENT / DEFER                                      │
│                                                             │
│ 4. Does this support intelligence quality (≥0.85)?          │
│    → YES: PRIORITIZE (confidence is non-negotiable)         │
│                                                             │
│ 5. Is this hard to undo later?                              │
│    → YES: Design carefully, then implement                  │
│    → NO: Implement fast, iterate                            │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Phase 0: Strategy & Discovery

**Duration:** 2 weeks
**Goal:** Validate assumptions, define scope, design industry ontology v1, identify risks

### 3.1 Objectives

1. ✅ Finalize PRD and technical specification
2. ✅ Identify initial beta customers
3. ✅ Define MVP scope (what's IN and what's OUT)
4. ✅ Select technology stack (including ML, search, ontology choices)
5. ✅ Establish development environment standards
6. ✅ Design initial industry ontology structure
7. ✅ Define chat agent tool interface

### 3.2 Work Packages

#### WP-0.1: Requirements Finalization
| Task | Owner | Duration | Deliverable |
|------|-------|----------|-------------|
| Review PRD with stakeholders | PM | 2 days | Signed PRD |
| Define user personas | PM | 1 day | Persona document |
| Map user journeys (incl. chat + search) | PM + Tech | 2 days | Journey diagrams |
| Identify MVP features | PM + Tech | 1 day | Feature priority list |

#### WP-0.2: Technical Planning
| Task | Owner | Duration | Deliverable |
|------|-------|----------|-------------|
| Architecture design (incl. ML, chat, search layers) | Tech Lead | 3 days | Architecture doc |
| Technology selection | Tech Lead | 1 day | Tech stack decision |
| Database schema design (incl. pgvector, ontology tables) | Backend + ML | 2 days | ERD + SQL scripts |
| API contract definition (incl. chat, search, ontology) | Backend | 2 days | OpenAPI spec |
| Industry ontology v1 design | ML Engineer | 3 days | Ontology schema + seed data |

#### WP-0.3: Environment Setup
| Task | Owner | Duration | Deliverable |
|------|-------|----------|-------------|
| Development environment setup | DevOps | 1 day | Dev env guide |
| Code repository setup | DevOps | 0.5 day | GitHub repo |
| Project board setup | PM | 0.5 day | Jira/Linear board |
| Documentation structure | Tech Lead | 0.5 day | Docs folder |

### 3.3 Phase 0 Deliverables

- [x] Signed PRD document
- [x] Technical Specification Definition v2.0
- [x] Implementation Planning (this document)
- [ ] Industry Ontology v1 schema
- [ ] Development environment guide
- [ ] Initial backlog with estimates

### 3.4 Phase 0 Exit Criteria

| Criterion | Validation Method |
|-----------|-------------------|
| PRD approved | Stakeholder sign-off |
| Tech spec approved (v2.0) | Engineering review |
| MVP scope defined (incl. chat, search, ML, ontology) | Feature list with priorities |
| Industry ontology v1 designed | Schema review |
| Team aligned | Kickoff meeting completed |

---

## 4. Phase 1: Foundation

**Duration:** 4 weeks
**Goal:** Establish identity, authentication, data layer (with pgvector), and basic runtime

### 4.1 Sprint Breakdown

| Sprint | Focus | Duration |
|--------|-------|----------|
| 1.1 | Authentication & Identity | 2 weeks |
| 1.2 | Data Layer & Core Models (pgvector) | 2 weeks |

### 4.2 Work Packages

#### WP-1.1: Authentication System

**Objective:** Users can sign up, log in, and access protected resources

| Task ID | Task | Owner | Est. | Dependencies | Status |
|---------|------|-------|------|--------------|--------|
| 1.1.1 | Auth0 tenant setup | DevOps | 4h | None | ⬜ |
| 1.1.2 | Configure Auth0 application | DevOps | 2h | 1.1.1 | ⬜ |
| 1.1.3 | Set up Auth0 rules/actions | Backend | 4h | 1.1.2 | ⬜ |
| 1.1.4 | Implement JWKS client | Backend | 4h | 1.1.2 | ⬜ |
| 1.1.5 | Create JWT validation middleware | Backend | 8h | 1.1.4 | ⬜ |
| 1.1.6 | Implement user sync webhook | Backend | 8h | 1.1.5 | ⬜ |
| 1.1.7 | Create auth dependencies | Backend | 4h | 1.1.5 | ⬜ |
| 1.1.8 | Implement RBAC permissions (incl. chat/search/ontology perms) | Backend | 8h | 1.1.7 | ⬜ |
| 1.1.9 | Create permission guards | Backend | 4h | 1.1.8 | ⬜ |
| 1.1.10 | Frontend: Auth provider setup | Frontend | 8h | 1.1.2 | ⬜ |
| 1.1.11 | Frontend: Login/logout flow | Frontend | 8h | 1.1.10 | ⬜ |
| 1.1.12 | Frontend: Protected routes | Frontend | 4h | 1.1.11 | ⬜ |
| 1.1.13 | E2E auth tests | Backend | 8h | 1.1.9 | ⬜ |

**Acceptance Criteria:**
- [ ] User can sign up via Auth0
- [ ] User can log in and receive JWT
- [ ] Protected endpoints reject invalid tokens
- [ ] RBAC permissions enforced (including chat, search, ontology)
- [ ] User data syncs to local database

#### WP-1.2: Organization & User Management

**Objective:** Multi-tenant organization structure with user roles and industry linkage

| Task ID | Task | Owner | Est. | Dependencies | Status |
|---------|------|-------|------|--------------|--------|
| 1.2.1 | Organization model (with industry_ontology_id FK) | Backend | 4h | None | ⬜ |
| 1.2.2 | User model | Backend | 4h | None | ⬜ |
| 1.2.3 | OrgUser junction model | Backend | 4h | 1.2.1, 1.2.2 | ⬜ |
| 1.2.4 | Organization repository | Backend | 8h | 1.2.1 | ⬜ |
| 1.2.5 | User repository | Backend | 8h | 1.2.2 | ⬜ |
| 1.2.6 | Organization service | Backend | 8h | 1.2.4 | ⬜ |
| 1.2.7 | Organization API endpoints | Backend | 8h | 1.2.6 | ⬜ |
| 1.2.8 | User API endpoints | Backend | 8h | 1.2.5 | ⬜ |
| 1.2.9 | Org context middleware | Backend | 4h | 1.2.3 | ⬜ |
| 1.2.10 | E2E org/user tests | Backend | 8h | 1.2.7, 1.2.8 | ⬜ |

**Acceptance Criteria:**
- [ ] Organizations can be created with industry linkage
- [ ] Users can be invited to organizations
- [ ] Users can have different roles per organization
- [ ] API endpoints scoped to organization context

#### WP-1.3: Database Setup (pgvector-Enabled)

**Objective:** Production-ready database with migrations and vector search support

| Task ID | Task | Owner | Est. | Dependencies | Status |
|---------|------|-------|------|--------------|--------|
| 1.3.1 | Neon PostgreSQL account setup | DevOps | 2h | None | ⬜ |
| 1.3.2 | Create development database | DevOps | 1h | 1.3.1 | ⬜ |
| 1.3.3 | Create staging database | DevOps | 1h | 1.3.1 | ⬜ |
| 1.3.4 | Enable pgvector extension | DevOps | 2h | 1.3.2 | ⬜ |
| 1.3.5 | Configure connection pooling | DevOps | 2h | 1.3.2 | ⬜ |
| 1.3.6 | Alembic setup | Backend | 4h | 1.3.2 | ⬜ |
| 1.3.7 | Initial migration (users, orgs, ontology tables) | Backend | 8h | 1.3.6 | ⬜ |
| 1.3.8 | Database session management | Backend | 4h | 1.3.5 | ⬜ |
| 1.3.9 | Query performance monitoring | Backend | 4h | 1.3.8 | ⬜ |
| 1.3.10 | Docker compose with pgvector image | DevOps | 4h | None | ⬜ |
| 1.3.11 | Seed data script (incl. industry ontology seeds) | ML Eng | 8h | 1.3.7 | ⬜ |

**Acceptance Criteria:**
- [ ] Migrations run successfully (including pgvector extension)
- [ ] Connections pooled correctly
- [ ] Vector operations functional
- [ ] Industry ontology seed data loads for development

#### WP-1.4: Redis Setup

**Objective:** Cache and queue infrastructure

| Task ID | Task | Owner | Est. | Dependencies | Status |
|---------|------|-------|------|--------------|--------|
| 1.4.1 | Upstash Redis account setup | DevOps | 2h | None | ⬜ |
| 1.4.2 | Redis client implementation | Backend | 4h | 1.4.1 | ⬜ |
| 1.4.3 | Rate limiting implementation | Backend | 8h | 1.4.2 | ⬜ |
| 1.4.4 | Session cache implementation | Backend | 4h | 1.4.2 | ⬜ |
| 1.4.5 | Job queue setup | Backend | 8h | 1.4.2 | ⬜ |
| 1.4.6 | Worker process setup | Backend | 4h | 1.4.5 | ⬜ |

**Acceptance Criteria:**
- [ ] Rate limiting works per-user (with chat/search-specific limits)
- [ ] Background jobs enqueue and process
- [ ] Cache hit/miss metrics available

#### WP-1.5: API Framework

**Objective:** Production-ready FastAPI setup

| Task ID | Task | Owner | Est. | Dependencies | Status |
|---------|------|-------|------|--------------|--------|
| 1.5.1 | FastAPI application setup | Backend | 4h | None | ⬜ |
| 1.5.2 | Request ID middleware | Backend | 2h | 1.5.1 | ⬜ |
| 1.5.3 | Error handling middleware | Backend | 4h | 1.5.1 | ⬜ |
| 1.5.4 | CORS configuration | Backend | 2h | 1.5.1 | ⬜ |
| 1.5.5 | Health check endpoints | Backend | 4h | 1.5.1 | ⬜ |
| 1.5.6 | OpenAPI documentation | Backend | 4h | 1.5.1 | ⬜ |
| 1.5.7 | Response standardization (with confidence decomposition) | Backend | 4h | 1.5.1 | ⬜ |
| 1.5.8 | Input validation schemas | Backend | 8h | 1.5.1 | ⬜ |
| 1.5.9 | SSE streaming endpoint base | Backend | 8h | 1.5.1 | ⬜ |

**Acceptance Criteria:**
- [ ] All requests have request IDs
- [ ] Errors return consistent format
- [ ] OpenAPI docs accessible
- [ ] SSE streaming works for chat
- [ ] Health checks pass

### 4.3 Phase 1 Deliverables

| Deliverable | Description |
|-------------|-------------|
| Auth system | Working Auth0 integration with extended RBAC |
| User/Org models | Database schema and APIs with industry linkage |
| API framework | FastAPI with middleware (incl. SSE streaming) |
| Database | pgvector-enabled PostgreSQL with ontology seeds |
| Dev environment | Docker compose with pgvector image |
| Test suite | Unit + integration tests |

### 4.4 Phase 1 Exit Criteria

| Criterion | Validation |
|-----------|------------|
| User can sign up | E2E test passes |
| User can log in | E2E test passes |
| Org can be created (with industry) | E2E test passes |
| Protected routes work | E2E test passes |
| Database migrations run (pgvector) | CI pipeline passes |
| Vector operations functional | E2E test passes |
| Test coverage > 80% | Coverage report |

---

## 5. Phase 2: Infrastructure Validation

**Duration:** 4 weeks
**Goal:** Production-ready infrastructure, CI/CD, observability, PWA base setup

### 5.1 Sprint Breakdown

| Sprint | Focus | Duration |
|--------|-------|----------|
| 2.1 | CI/CD & Deployment | 2 weeks |
| 2.2 | Observability, Security & PWA Setup | 2 weeks |

### 5.2 Work Packages

#### WP-2.1: CI/CD Pipeline

**Objective:** Automated testing and deployment

| Task ID | Task | Owner | Est. | Dependencies | Status |
|---------|------|-------|------|--------------|--------|
| 2.1.1 | GitHub Actions workflow setup | DevOps | 4h | None | ⬜ |
| 2.1.2 | Test job configuration | DevOps | 4h | 2.1.1 | ⬜ |
| 2.1.3 | Lint/format job configuration | DevOps | 2h | 2.1.1 | ⬜ |
| 2.1.4 | Docker build job | DevOps | 4h | 2.1.1 | ⬜ |
| 2.1.5 | Container registry setup (ACR) | DevOps | 4h | 2.1.4 | ⬜ |
| 2.1.6 | Staging deployment job | DevOps | 8h | 2.1.5 | ⬜ |
| 2.1.7 | Production deployment job | DevOps | 8h | 2.1.6 | ⬜ |
| 2.1.8 | Rollback procedure | DevOps | 4h | 2.1.7 | ⬜ |
| 2.1.9 | Branch protection rules | DevOps | 2h | 2.1.2 | ⬜ |

**Acceptance Criteria:**
- [ ] Push to main triggers tests
- [ ] Tests pass before merge
- [ ] Staging auto-deploys on main
- [ ] Production requires approval
- [ ] Rollback works in < 5 minutes

#### WP-2.2: Azure Infrastructure

**Objective:** Production cloud infrastructure

| Task ID | Task | Owner | Est. | Dependencies | Status |
|---------|------|-------|------|--------------|--------|
| 2.2.1 | Azure subscription setup | DevOps | 2h | None | ⬜ |
| 2.2.2 | Resource group creation | DevOps | 1h | 2.2.1 | ⬜ |
| 2.2.3 | Azure Container Apps setup | DevOps | 8h | 2.2.2 | ⬜ |
| 2.2.4 | Container Apps environment config | DevOps | 4h | 2.2.3 | ⬜ |
| 2.2.5 | Azure Key Vault setup | DevOps | 4h | 2.2.2 | ⬜ |
| 2.2.6 | Key Vault integration | DevOps | 4h | 2.2.5 | ⬜ |
| 2.2.7 | Azure Blob Storage setup (for ML models + evidence) | DevOps | 4h | 2.2.2 | ⬜ |
| 2.2.8 | Custom domain & SSL | DevOps | 4h | 2.2.3 | ⬜ |
| 2.2.9 | Azure Front Door setup (CDN for PWA) | DevOps | 8h | 2.2.8 | ⬜ |

**Acceptance Criteria:**
- [ ] Containers deploy and scale
- [ ] Secrets load from Key Vault
- [ ] HTTPS works with custom domain
- [ ] CDN serves PWA static assets with proper caching
- [ ] Blob storage accessible for ML models

#### WP-2.3: Observability Stack

**Objective:** Logging, metrics, and alerting (including chat/search/ML metrics)

| Task ID | Task | Owner | Est. | Dependencies | Status |
|---------|------|-------|------|--------------|--------|
| 2.3.1 | Structured logging setup | Backend | 4h | None | ⬜ |
| 2.3.2 | Log aggregation (Azure Monitor) | DevOps | 4h | 2.3.1 | ⬜ |
| 2.3.3 | Prometheus metrics setup | Backend | 8h | None | ⬜ |
| 2.3.4 | Metrics endpoint exposure | Backend | 2h | 2.3.3 | ⬜ |
| 2.3.5 | Grafana dashboard setup (with ML/chat/search panels) | DevOps | 8h | 2.3.4 | ⬜ |
| 2.3.6 | Alert rules configuration (incl. confidence drop, ML stale) | DevOps | 4h | 2.3.5 | ⬜ |
| 2.3.7 | Sentry error tracking setup | DevOps | 4h | None | ⬜ |
| 2.3.8 | Sentry integration in code | Backend | 4h | 2.3.7 | ⬜ |
| 2.3.9 | Health check dashboard | DevOps | 4h | 2.3.5 | ⬜ |

**Acceptance Criteria:**
- [ ] Logs searchable in Azure Monitor
- [ ] Metrics visible in Grafana (including ML, chat, search panels)
- [ ] Alerts fire on error spike and confidence drop
- [ ] Errors tracked in Sentry

#### WP-2.4: Security Hardening

**Objective:** Production security baseline (including chat/search rate limits)

| Task ID | Task | Owner | Est. | Dependencies | Status |
|---------|------|-------|------|--------------|--------|
| 2.4.1 | Security headers middleware | Backend | 4h | None | ⬜ |
| 2.4.2 | Input sanitization audit | Backend | 8h | None | ⬜ |
| 2.4.3 | SQL injection testing | Backend | 4h | None | ⬜ |
| 2.4.4 | API key implementation | Backend | 8h | None | ⬜ |
| 2.4.5 | API key management endpoints | Backend | 8h | 2.4.4 | ⬜ |
| 2.4.6 | Audit logging implementation | Backend | 8h | None | ⬜ |
| 2.4.7 | Rate limiting per endpoint (chat: 30/min, search: 10/min) | Backend | 8h | None | ⬜ |
| 2.4.8 | Chat session isolation (per org+user) | Backend | 4h | None | ⬜ |
| 2.4.9 | OWASP checklist review | Tech Lead | 8h | All | ⬜ |

**Acceptance Criteria:**
- [ ] Security headers on all responses
- [ ] No SQL injection vulnerabilities
- [ ] API keys working
- [ ] Audit logs capture mutations
- [ ] Chat/search rate limits enforced
- [ ] Chat sessions isolated per org+user
- [ ] OWASP top 10 addressed

#### WP-2.5: Frontend Infrastructure (PWA)

**Objective:** Production PWA deployment with installability and offline capability

| Task ID | Task | Owner | Est. | Dependencies | Status |
|---------|------|-------|------|--------------|--------|
| 2.5.1 | Next.js project setup | Frontend | 4h | None | ⬜ |
| 2.5.2 | Tailwind + Shadcn/UI component library | Frontend | 8h | 2.5.1 | ⬜ |
| 2.5.3 | API client setup (with SSE streaming support) | Frontend | 8h | 2.5.1 | ⬜ |
| 2.5.4 | Auth integration | Frontend | 8h | 2.5.3 | ⬜ |
| 2.5.5 | Error boundary setup | Frontend | 4h | 2.5.1 | ⬜ |
| 2.5.6 | PWA manifest.json configuration | Frontend | 4h | 2.5.1 | ⬜ |
| 2.5.7 | Service worker implementation | Frontend | 16h | 2.5.1 | ⬜ |
| 2.5.8 | PWA install prompt component | Frontend | 4h | 2.5.6 | ⬜ |
| 2.5.9 | Offline indicator component | Frontend | 4h | 2.5.7 | ⬜ |
| 2.5.10 | Push notification setup | Frontend | 8h | 2.5.7 | ⬜ |
| 2.5.11 | PWA icon generation (192, 512, maskable) | Frontend | 4h | 2.5.6 | ⬜ |
| 2.5.12 | Vercel/Azure deployment setup | DevOps | 4h | 2.5.1 | ⬜ |
| 2.5.13 | Environment configuration | DevOps | 2h | 2.5.12 | ⬜ |

**Acceptance Criteria:**
- [ ] PWA installable on desktop and mobile browsers
- [ ] Service worker caches app shell (cache-first)
- [ ] API calls use network-first with cache fallback
- [ ] Offline indicator displays when disconnected
- [ ] Push notifications registered
- [ ] Auth flow works E2E
- [ ] Lighthouse PWA audit score > 90

### 5.3 Phase 2 Deliverables

| Deliverable | Description |
|-------------|-------------|
| CI/CD pipeline | GitHub Actions → Azure |
| Staging environment | Fully functional pre-prod |
| Observability | Logs, metrics, alerts (with ML/chat/search panels) |
| Security baseline | Hardened application (with chat/search rate limits) |
| PWA shell | Installable, offline-capable dashboard |

### 5.4 Phase 2 Exit Criteria

| Criterion | Validation |
|-----------|------------|
| CI/CD works | Automated deployment successful |
| Staging accessible | Team can use staging |
| Metrics dashboard | Grafana shows data (ML/chat panels ready) |
| Alerts configured | Test alert fires |
| Security audit | OWASP checklist complete |
| PWA installable | Lighthouse audit > 90 |

---

## 6. Phase 3: Product Construction (MVP)

**Duration:** 16 weeks
**Goal:** Deliver core user value — enterprise signal intelligence with AI chat, deep search, ML scoring, industry ontologies, recommendations, and simulation mode

### 6.1 Sprint Breakdown

| Sprint | Focus | Duration |
|--------|-------|----------|
| 3.1 | Industry Ontology & Signal Catalog | 2 weeks |
| 3.2 | Signal Contract System (Ontology-Aware) | 2 weeks |
| 3.3 | Entity Management & ML Entity Resolution | 2 weeks |
| 3.4 | Signal Core + Source Management | 2 weeks |
| 3.5 | Acquisition & Refinement Pipelines | 2 weeks |
| 3.6 | Lightweight ML Engine & Recommendations | 2 weeks |
| 3.7 | Deep Live Search & On-Demand Synthesis | 2 weeks |
| 3.8 | AI Chat Agent & Analytics | 2 weeks |

### 6.2 Core User Jobs

> **Job 1:** "As an enterprise analyst, I want to track signals about my market so I can make informed decisions faster."
> **Job 2:** "As a decision-maker, I want to ask questions in natural language and get actionable intelligence with recommendations."
> **Job 3:** "As a new user, I want to explore the platform with simulated data before connecting live sources."

### 6.3 Work Packages

#### WP-3.1: Industry Ontology & Enterprise Signal Catalog

**Objective:** Industry domain knowledge system with pre-built signal templates

| Task ID | Task | Owner | Est. | Dependencies | Status |
|---------|------|-------|------|--------------|--------|
| 3.1.1 | IndustryOntology model | ML Eng | 4h | None | ⬜ |
| 3.1.2 | DomainTaxonomy model | ML Eng | 4h | 3.1.1 | ⬜ |
| 3.1.3 | OntologyNode model (hierarchical) | ML Eng | 8h | 3.1.2 | ⬜ |
| 3.1.4 | SignalCatalog model | ML Eng | 4h | 3.1.1 | ⬜ |
| 3.1.5 | Ontology migrations (with vector columns) | ML Eng | 4h | 3.1.3 | ⬜ |
| 3.1.6 | Ontology repository | Backend | 8h | 3.1.3 | ⬜ |
| 3.1.7 | Ontology loader & cache (Redis, 24h TTL) | ML Eng | 8h | 3.1.6 | ⬜ |
| 3.1.8 | Ontology matcher (embedding-based) | ML Eng | 16h | 3.1.7 | ⬜ |
| 3.1.9 | Industry seed data: Fintech | ML Eng | 8h | 3.1.5 | ⬜ |
| 3.1.10 | Industry seed data: FMCG | ML Eng | 8h | 3.1.5 | ⬜ |
| 3.1.11 | Industry seed data: Energy | ML Eng | 8h | 3.1.5 | ⬜ |
| 3.1.12 | Industry seed data: Agriculture, Real Estate | ML Eng | 8h | 3.1.5 | ⬜ |
| 3.1.13 | Industry seed data: Healthcare, Manufacturing | ML Eng | 8h | 3.1.5 | ⬜ |
| 3.1.14 | Industry seed data: Logistics, Telecom, Retail | ML Eng | 8h | 3.1.5 | ⬜ |
| 3.1.15 | Catalog service (template instantiation) | Backend | 8h | 3.1.4, 3.1.6 | ⬜ |
| 3.1.16 | Ontology API - List industries | Backend | 4h | 3.1.6 | ⬜ |
| 3.1.17 | Ontology API - Get industry detail | Backend | 4h | 3.1.6 | ⬜ |
| 3.1.18 | Ontology API - Get taxonomies | Backend | 4h | 3.1.6 | ⬜ |
| 3.1.19 | Ontology API - Semantic search | Backend | 8h | 3.1.8 | ⬜ |
| 3.1.20 | Ontology API - Get catalog | Backend | 4h | 3.1.15 | ⬜ |
| 3.1.21 | Frontend: Ontology browser | Frontend | 16h | 3.1.16 | ⬜ |
| 3.1.22 | Frontend: Domain selector | Frontend | 8h | 3.1.17 | ⬜ |
| 3.1.23 | E2E ontology tests | Backend | 8h | 3.1.20 | ⬜ |

**Acceptance Criteria:**
- [ ] 10+ industry ontologies seeded with domain taxonomies
- [ ] Ontology nodes form valid hierarchies
- [ ] Embedding-based semantic search across ontologies works
- [ ] Signal catalog contains 100+ pre-built templates
- [ ] Ontology browser navigable in frontend

#### WP-3.2: Signal Contract System (Enterprise-Grade, Ontology-Aware)

**Objective:** Users can define enterprise-grade signal contracts validated against industry ontologies

| Task ID | Task | Owner | Est. | Dependencies | Status |
|---------|------|-------|------|--------------|--------|
| 3.2.1 | SignalContract model (with ontology_id, confidence_threshold=0.85, ml_scoring_enabled) | Backend | 8h | 3.1.1 | ⬜ |
| 3.2.2 | SignalContract migration | Backend | 2h | 3.2.1 | ⬜ |
| 3.2.3 | SignalContract repository | Backend | 8h | 3.2.1 | ⬜ |
| 3.2.4 | SignalContract service (ontology validation) | Backend | 16h | 3.2.3, 3.1.7 | ⬜ |
| 3.2.5 | Contract validation logic (enterprise-grade schema + ontology) | Backend | 16h | 3.2.4 | ⬜ |
| 3.2.6 | Contract versioning logic | Backend | 4h | 3.2.4 | ⬜ |
| 3.2.7 | Contract API - Create (with ontology validation) | Backend | 4h | 3.2.4 | ⬜ |
| 3.2.8 | Contract API - Read | Backend | 4h | 3.2.4 | ⬜ |
| 3.2.9 | Contract API - Update | Backend | 4h | 3.2.4 | ⬜ |
| 3.2.10 | Contract API - Delete | Backend | 4h | 3.2.4 | ⬜ |
| 3.2.11 | Contract API - Activate/Deactivate | Backend | 4h | 3.2.4 | ⬜ |
| 3.2.12 | Contract API - Create from catalog template | Backend | 8h | 3.2.4, 3.1.15 | ⬜ |
| 3.2.13 | Frontend: Contract list page (with industry filter) | Frontend | 8h | 3.2.8 | ⬜ |
| 3.2.14 | Frontend: Contract create form (with ontology selector) | Frontend | 16h | 3.2.7, 3.1.22 | ⬜ |
| 3.2.15 | Frontend: Contract detail page (with confidence config) | Frontend | 8h | 3.2.8 | ⬜ |
| 3.2.16 | Frontend: Create from catalog wizard | Frontend | 16h | 3.2.12 | ⬜ |
| 3.2.17 | E2E contract tests | Backend | 8h | 3.2.12 | ⬜ |

**Acceptance Criteria:**
- [ ] User can create a signal contract with ontology linkage
- [ ] Contract schema validated against industry ontology
- [ ] Default confidence threshold is 0.85
- [ ] ML scoring enabled by default
- [ ] Catalog templates can be instantiated as contracts
- [ ] Contract create form has ontology selector and catalog wizard

#### WP-3.3: Entity Management (ML-Enhanced)

**Objective:** Track business entities with ML-based entity resolution

| Task ID | Task | Owner | Est. | Dependencies | Status |
|---------|------|-------|------|--------------|--------|
| 3.3.1 | Entity model (with ontology_node_id FK, embedding column) | Backend | 4h | 3.1.3 | ⬜ |
| 3.3.2 | Entity migration | Backend | 2h | 3.3.1 | ⬜ |
| 3.3.3 | Entity repository (with vector search) | Backend | 8h | 3.3.1 | ⬜ |
| 3.3.4 | Entity service | Backend | 8h | 3.3.3 | ⬜ |
| 3.3.5 | ML entity resolution logic (sentence transformers) | ML Eng | 24h | 3.3.4 | ⬜ |
| 3.3.6 | Entity merge logic | Backend | 8h | 3.3.4 | ⬜ |
| 3.3.7 | Entity API - CRUD | Backend | 8h | 3.3.4 | ⬜ |
| 3.3.8 | Entity search (semantic + fuzzy) | Backend | 8h | 3.3.3 | ⬜ |
| 3.3.9 | Frontend: Entity list | Frontend | 8h | 3.3.7 | ⬜ |
| 3.3.10 | E2E entity tests | Backend | 8h | 3.3.7 | ⬜ |

**Acceptance Criteria:**
- [ ] Entities can be created and searched (semantic + fuzzy)
- [ ] ML entity resolution matches variants with >90% accuracy
- [ ] Duplicate entities can be merged
- [ ] Entities linked to ontology nodes

#### WP-3.4: Signal Core + Source Management

**Objective:** Signals instantiated from contracts; sources managed with industry tagging

| Task ID | Task | Owner | Est. | Dependencies | Status |
|---------|------|-------|------|--------------|--------|
| 3.4.1 | Signal model (with ml_anomaly_score, ml_trend_direction) | Backend | 4h | 3.2.1 | ⬜ |
| 3.4.2 | SignalValue model (with ml_score) | Backend | 4h | 3.4.1 | ⬜ |
| 3.4.3 | Signal/Value migrations | Backend | 4h | 3.4.2 | ⬜ |
| 3.4.4 | Signal repository | Backend | 8h | 3.4.1 | ⬜ |
| 3.4.5 | SignalValue repository | Backend | 8h | 3.4.2 | ⬜ |
| 3.4.6 | Signal service (ML-enhanced) | Backend | 16h | 3.4.4, 3.4.5 | ⬜ |
| 3.4.7 | Signal instantiation from contract | Backend | 8h | 3.4.6 | ⬜ |
| 3.4.8 | Signal value recording (with ML scoring hooks) | Backend | 8h | 3.4.6 | ⬜ |
| 3.4.9 | Signal history query | Backend | 8h | 3.4.5 | ⬜ |
| 3.4.10 | Signal API - List (with ML scores) | Backend | 4h | 3.4.6 | ⬜ |
| 3.4.11 | Signal API - Get (with confidence decomposition) | Backend | 4h | 3.4.6 | ⬜ |
| 3.4.12 | Signal API - History | Backend | 4h | 3.4.9 | ⬜ |
| 3.4.13 | Signal API - Query (ontology filters) | Backend | 8h | 3.4.6 | ⬜ |
| 3.4.14 | Source model (with industry_tags, ontology_ids, reliability_score) | Backend | 4h | None | ⬜ |
| 3.4.15 | Source migration | Backend | 2h | 3.4.14 | ⬜ |
| 3.4.16 | Source repository | Backend | 8h | 3.4.14 | ⬜ |
| 3.4.17 | Source service | Backend | 8h | 3.4.16 | ⬜ |
| 3.4.18 | Source adapter interface | Backend | 8h | None | ⬜ |
| 3.4.19 | Web scraper adapter | Backend | 16h | 3.4.18 | ⬜ |
| 3.4.20 | API adapter | Backend | 16h | 3.4.18 | ⬜ |
| 3.4.21 | RSS adapter | Backend | 8h | 3.4.18 | ⬜ |
| 3.4.22 | Source health tracking | Backend | 8h | 3.4.17 | ⬜ |
| 3.4.23 | Source API - CRUD (with industry filters) | Backend | 8h | 3.4.17 | ⬜ |
| 3.4.24 | Source API - Test connection | Backend | 4h | 3.4.19, 3.4.20 | ⬜ |
| 3.4.25 | Frontend: Signal list (with ML scores, confidence bar) | Frontend | 16h | 3.4.10 | ⬜ |
| 3.4.26 | Frontend: Signal detail (with confidence decomposition) | Frontend | 16h | 3.4.11 | ⬜ |
| 3.4.27 | Frontend: Signal history chart | Frontend | 16h | 3.4.12 | ⬜ |
| 3.4.28 | Frontend: Source management (with industry tags) | Frontend | 16h | 3.4.23 | ⬜ |
| 3.4.29 | E2E signal tests | Backend | 8h | 3.4.13 | ⬜ |
| 3.4.30 | E2E source tests | Backend | 8h | 3.4.24 | ⬜ |

**Acceptance Criteria:**
- [ ] Signals instantiate from contracts with ML scoring hooks
- [ ] Signal API returns confidence decomposition (source_coverage + freshness + agreement + ml_score)
- [ ] Signal values recorded with timestamps and ML scores
- [ ] Sources tagged with industry and ontology
- [ ] Source reliability tracked
- [ ] Frontend shows confidence decomposition bar

#### WP-3.5: Evidence, Acquisition & Refinement Pipelines

**Objective:** Full data pipeline: fetch → normalize → enrich → score

| Task ID | Task | Owner | Est. | Dependencies | Status |
|---------|------|-------|------|--------------|--------|
| 3.5.1 | Evidence model (with embedding column) | Backend | 4h | 3.4.14 | ⬜ |
| 3.5.2 | Evidence migration | Backend | 2h | 3.5.1 | ⬜ |
| 3.5.3 | Evidence repository (with vector search) | Backend | 8h | 3.5.1 | ⬜ |
| 3.5.4 | Evidence service | Backend | 8h | 3.5.3 | ⬜ |
| 3.5.5 | Evidence extraction from fetch | Backend | 16h | 3.5.4 | ⬜ |
| 3.5.6 | Evidence-signal linkage | Backend | 8h | 3.5.4, 3.4.6 | ⬜ |
| 3.5.7 | Evidence embedding generation (OpenAI) | ML Eng | 8h | 3.5.4 | ⬜ |
| 3.5.8 | Acquisition job definition | Backend | 8h | 3.4.18 | ⬜ |
| 3.5.9 | Fetch scheduler | Backend | 16h | 3.5.8 | ⬜ |
| 3.5.10 | Rate limiting per source | Backend | 8h | 3.5.8 | ⬜ |
| 3.5.11 | Retry logic with backoff | Backend | 8h | 3.5.8 | ⬜ |
| 3.5.12 | Source health update | Backend | 4h | 3.5.8, 3.4.22 | ⬜ |
| 3.5.13 | Worker process integration | Backend | 8h | 3.5.9 | ⬜ |
| 3.5.14 | Normalizer interface | Backend | 4h | None | ⬜ |
| 3.5.15 | Generic normalizer (ontology-enhanced) | Backend | 16h | 3.5.14, 3.1.7 | ⬜ |
| 3.5.16 | Entity resolution integration (ML) | ML Eng | 8h | 3.3.5 | ⬜ |
| 3.5.17 | Confidence calculation (decomposed: source + freshness + agreement + ML) | ML Eng | 16h | 3.5.15 | ⬜ |
| 3.5.18 | Change detection | Backend | 16h | 3.4.6 | ⬜ |
| 3.5.19 | Refinement job definition | Backend | 8h | 3.5.15 | ⬜ |
| 3.5.20 | Full pipeline integration (Acquire → Refine → ML Score → Synthesize) | Backend | 16h | 3.5.19 | ⬜ |
| 3.5.21 | Evidence API - Get for signal | Backend | 4h | 3.5.4 | ⬜ |
| 3.5.22 | Frontend: Evidence display | Frontend | 8h | 3.5.21 | ⬜ |
| 3.5.23 | E2E pipeline tests | Backend | 8h | 3.5.20 | ⬜ |

**Acceptance Criteria:**
- [ ] Sources fetched on schedule
- [ ] Raw data normalized with ontology enrichment
- [ ] Entities resolved via ML (>90% accuracy)
- [ ] Confidence decomposed into 4 factors (source_coverage + freshness + agreement + ML)
- [ ] Evidence embeddings generated for vector search
- [ ] Full pipeline runs end-to-end
- [ ] Changes detected and tracked

#### WP-3.6: Lightweight ML Engine & Recommendation Engine

**Objective:** ML-powered anomaly detection, signal scoring, trend forecasting, and actionable recommendations

| Task ID | Task | Owner | Est. | Dependencies | Status |
|---------|------|-------|------|--------------|--------|
| 3.6.1 | ML model registry (model + migrations) | ML Eng | 8h | None | ⬜ |
| 3.6.2 | Model registry service (versioning, loading, caching) | ML Eng | 16h | 3.6.1 | ⬜ |
| 3.6.3 | Anomaly detector (Isolation Forest + statistical) | ML Eng | 24h | 3.6.2 | ⬜ |
| 3.6.4 | Signal scorer (Gradient Boosted Trees) | ML Eng | 24h | 3.6.2 | ⬜ |
| 3.6.5 | Trend forecaster (Prophet-lite / ARIMA) | ML Eng | 16h | 3.6.2 | ⬜ |
| 3.6.6 | Cluster engine (K-Means + DBSCAN) | ML Eng | 16h | 3.6.2 | ⬜ |
| 3.6.7 | ML inference service (unified interface) | ML Eng | 16h | 3.6.3, 3.6.4, 3.6.5, 3.6.6 | ⬜ |
| 3.6.8 | ML integration into signal pipeline | Backend | 8h | 3.6.7, 3.5.20 | ⬜ |
| 3.6.9 | Recommendation model + migration | Backend | 4h | None | ⬜ |
| 3.6.10 | Recommendation service (LLM + ML scoring) | Backend | 24h | 3.6.9, 3.6.7 | ⬜ |
| 3.6.11 | Recommendation generation pipeline | Backend | 16h | 3.6.10 | ⬜ |
| 3.6.12 | Recommendation API - Get for signal | Backend | 4h | 3.6.10 | ⬜ |
| 3.6.13 | Recommendation API - List all active | Backend | 4h | 3.6.10 | ⬜ |
| 3.6.14 | ML retraining job (lightweight, scheduled) | ML Eng | 16h | 3.6.7 | ⬜ |
| 3.6.15 | Simulation mode service (starter tier) | ML Eng | 24h | 3.6.7, 3.1.7 | ⬜ |
| 3.6.16 | Simulation data generator (per industry ontology) | ML Eng | 16h | 3.6.15 | ⬜ |
| 3.6.17 | Frontend: Recommendation cards | Frontend | 16h | 3.6.12 | ⬜ |
| 3.6.18 | Frontend: Actionable insights panel | Frontend | 8h | 3.6.13 | ⬜ |
| 3.6.19 | Frontend: ML insights display | Frontend | 8h | 3.6.7 | ⬜ |
| 3.6.20 | Frontend: Simulation mode indicator + toggle | Frontend | 8h | 3.6.15 | ⬜ |
| 3.6.21 | E2E ML tests | Backend | 8h | 3.6.8 | ⬜ |
| 3.6.22 | E2E recommendation tests | Backend | 8h | 3.6.11 | ⬜ |
| 3.6.23 | E2E simulation tests | Backend | 8h | 3.6.16 | ⬜ |

**Acceptance Criteria:**
- [ ] Anomaly detector runs in <50ms, flags unusual signal changes
- [ ] Signal scorer produces ML confidence component
- [ ] Trend forecaster generates 24h/7d predictions
- [ ] Cluster engine groups related signals
- [ ] Recommendations generated with action items and risk levels
- [ ] Simulation mode generates realistic data per industry ontology
- [ ] Starter tier organizations default to simulation mode
- [ ] ML models retrain on schedule (weekly)
- [ ] All models ≤100MB, inference ≤100ms

#### WP-3.7: Deep Live Search & On-Demand Synthesis

**Objective:** Multi-source parallel search with semantic ranking and LLM synthesis

| Task ID | Task | Owner | Est. | Dependencies | Status |
|---------|------|-------|------|--------------|--------|
| 3.7.1 | Search orchestrator | Backend | 16h | None | ⬜ |
| 3.7.2 | Query expansion (ontology synonyms + related concepts) | ML Eng | 16h | 3.1.8 | ⬜ |
| 3.7.3 | Parallel source fetcher (async, concurrent) | Backend | 16h | 3.4.18 | ⬜ |
| 3.7.4 | Semantic ranker (embedding-based relevance + ontology alignment) | ML Eng | 24h | 3.5.7 | ⬜ |
| 3.7.5 | Result synthesizer (dedup, fusion, scoring) | Backend | 16h | 3.7.4 | ⬜ |
| 3.7.6 | Source discovery (dynamic new source identification) | Backend | 16h | 3.7.1 | ⬜ |
| 3.7.7 | Search API - Execute deep search | Backend | 8h | 3.7.5 | ⬜ |
| 3.7.8 | Search API - Discover sources | Backend | 4h | 3.7.6 | ⬜ |
| 3.7.9 | Search API - History | Backend | 4h | 3.7.1 | ⬜ |
| 3.7.10 | LLM synthesis service (GPT-4 Turbo) | Backend | 16h | None | ⬜ |
| 3.7.11 | Intent parsing (question → search parameters) | ML Eng | 16h | 3.7.10 | ⬜ |
| 3.7.12 | Coverage check (existing signals vs. gap) | Backend | 8h | 3.4.6 | ⬜ |
| 3.7.13 | Live source discovery for synthesis | Backend | 16h | 3.7.6 | ⬜ |
| 3.7.14 | Evidence extraction (live) | Backend | 16h | 3.5.5 | ⬜ |
| 3.7.15 | Signal synthesis logic (with ML scoring + confidence) | Backend | 24h | 3.7.14, 3.6.7 | ⬜ |
| 3.7.16 | Limitations generation | Backend | 4h | 3.7.15 | ⬜ |
| 3.7.17 | Synthesis API endpoint | Backend | 8h | 3.7.15 | ⬜ |
| 3.7.18 | Frontend: Search bar (with query expansion suggestions) | Frontend | 8h | 3.7.7 | ⬜ |
| 3.7.19 | Frontend: Search results (ranked, with source cards) | Frontend | 16h | 3.7.7 | ⬜ |
| 3.7.20 | Frontend: Search filters (industry, domain, depth) | Frontend | 8h | 3.7.7 | ⬜ |
| 3.7.21 | Frontend: Synthesis interface | Frontend | 24h | 3.7.17 | ⬜ |
| 3.7.22 | E2E search tests | Backend | 8h | 3.7.9 | ⬜ |
| 3.7.23 | E2E synthesis tests | Backend | 8h | 3.7.17 | ⬜ |

**Acceptance Criteria:**
- [ ] Deep search orchestrates parallel fetch across 3+ source types
- [ ] Query expansion uses ontology synonyms and related concepts
- [ ] Semantic ranking uses embedding similarity + source reliability + freshness + ontology alignment
- [ ] Search results deduplicated and fused
- [ ] Search P95 < 5 seconds for "deep" mode
- [ ] On-demand synthesis returns signal with confidence ≥ 0.85 and evidence lineage
- [ ] Synthesis includes recommendations and limitations

#### WP-3.8: AI Chat Agent

**Objective:** Conversational AI layer providing natural language signal interaction with tool orchestration

| Task ID | Task | Owner | Est. | Dependencies | Status |
|---------|------|-------|------|--------------|--------|
| 3.8.1 | Chat session model + migration | Backend | 4h | None | ⬜ |
| 3.8.2 | Chat message model + migration | Backend | 4h | 3.8.1 | ⬜ |
| 3.8.3 | Chat repository (sessions + messages) | Backend | 8h | 3.8.2 | ⬜ |
| 3.8.4 | Agent tool definitions (search_signals, deep_search, synthesize, get_analytics, get_recommendations, browse_ontology, create_contract) | ML Eng | 24h | 3.4.6, 3.7.1, 3.6.10, 3.1.7 | ⬜ |
| 3.8.5 | Conversation context manager (short-term memory via Redis) | ML Eng | 16h | 3.8.3 | ⬜ |
| 3.8.6 | Agent core (LLM reasoning loop with tool orchestration) | ML Eng | 24h | 3.8.4, 3.8.5 | ⬜ |
| 3.8.7 | System prompts per industry domain | ML Eng | 8h | 3.8.6, 3.1.7 | ⬜ |
| 3.8.8 | SSE streaming response handler | Backend | 8h | 3.8.6 | ⬜ |
| 3.8.9 | Citation generation (evidence references in responses) | ML Eng | 8h | 3.8.6 | ⬜ |
| 3.8.10 | Chat API - Create session | Backend | 4h | 3.8.3 | ⬜ |
| 3.8.11 | Chat API - List sessions | Backend | 4h | 3.8.3 | ⬜ |
| 3.8.12 | Chat API - Get session (with messages) | Backend | 4h | 3.8.3 | ⬜ |
| 3.8.13 | Chat API - Send message (SSE streaming) | Backend | 16h | 3.8.8 | ⬜ |
| 3.8.14 | Chat API - Feedback | Backend | 4h | 3.8.3 | ⬜ |
| 3.8.15 | Chat rate limiting (30 msg/min) | Backend | 4h | None | ⬜ |
| 3.8.16 | Frontend: Chat interface | Frontend | 24h | 3.8.13 | ⬜ |
| 3.8.17 | Frontend: Chat message bubble (with citations) | Frontend | 8h | 3.8.16 | ⬜ |
| 3.8.18 | Frontend: Chat input (with suggestions) | Frontend | 8h | 3.8.16 | ⬜ |
| 3.8.19 | Frontend: Tool execution display | Frontend | 8h | 3.8.16 | ⬜ |
| 3.8.20 | Frontend: Chat sidebar (session history) | Frontend | 8h | 3.8.11 | ⬜ |
| 3.8.21 | E2E chat tests | Backend | 8h | 3.8.14 | ⬜ |

**Acceptance Criteria:**
- [ ] User can start conversation and get streamed responses
- [ ] Agent uses tools to query signals, search, analytics, ontology
- [ ] Citations reference evidence in responses
- [ ] Industry-specific system prompts provide domain context
- [ ] Chat sessions isolated per org+user
- [ ] First token in <1.5s (P95)
- [ ] Rate limited to 30 msg/min

#### WP-3.9: Analytics, Trends & Notifications

**Objective:** ML-enhanced analytics, trend detection, anomaly alerts, and notification delivery

| Task ID | Task | Owner | Est. | Dependencies | Status |
|---------|------|-------|------|--------------|--------|
| 3.9.1 | Trend calculation logic (ML-enhanced) | ML Eng | 16h | 3.4.9, 3.6.5 | ⬜ |
| 3.9.2 | Anomaly detection integration (from ML engine) | ML Eng | 8h | 3.6.3 | ⬜ |
| 3.9.3 | Comparison logic | Backend | 8h | 3.4.9 | ⬜ |
| 3.9.4 | Coverage report | Backend | 8h | 3.4.4, 3.4.16 | ⬜ |
| 3.9.5 | Industry-specific analytics (benchmark comparison) | ML Eng | 16h | 3.1.7 | ⬜ |
| 3.9.6 | ML forecast endpoint | ML Eng | 8h | 3.6.5 | ⬜ |
| 3.9.7 | Analytics API - Trends | Backend | 8h | 3.9.1 | ⬜ |
| 3.9.8 | Analytics API - Anomalies | Backend | 8h | 3.9.2 | ⬜ |
| 3.9.9 | Analytics API - Compare | Backend | 4h | 3.9.3 | ⬜ |
| 3.9.10 | Analytics API - Coverage | Backend | 4h | 3.9.4 | ⬜ |
| 3.9.11 | Analytics API - Recommendations | Backend | 4h | 3.6.13 | ⬜ |
| 3.9.12 | Analytics API - Forecast | Backend | 4h | 3.9.6 | ⬜ |
| 3.9.13 | Analytics API - Industry | Backend | 4h | 3.9.5 | ⬜ |
| 3.9.14 | Webhook configuration model | Backend | 4h | None | ⬜ |
| 3.9.15 | Webhook repository | Backend | 4h | 3.9.14 | ⬜ |
| 3.9.16 | Webhook service | Backend | 8h | 3.9.15 | ⬜ |
| 3.9.17 | Webhook delivery with retry | Backend | 8h | 3.9.16 | ⬜ |
| 3.9.18 | Webhook signature (HMAC) | Backend | 4h | 3.9.16 | ⬜ |
| 3.9.19 | Alert rule model | Backend | 4h | 3.4.1 | ⬜ |
| 3.9.20 | Alert evaluation logic (incl. ML anomaly triggers) | Backend | 8h | 3.9.19, 3.9.2 | ⬜ |
| 3.9.21 | Alert trigger + webhook | Backend | 8h | 3.9.20, 3.9.16 | ⬜ |
| 3.9.22 | Push notification delivery (PWA) | Frontend | 8h | 3.9.21 | ⬜ |
| 3.9.23 | Webhook API - CRUD | Backend | 8h | 3.9.16 | ⬜ |
| 3.9.24 | Frontend: Trends dashboard (ML-enhanced) | Frontend | 24h | 3.9.7 | ⬜ |
| 3.9.25 | Frontend: Anomaly alerts (ML-flagged) | Frontend | 16h | 3.9.8 | ⬜ |
| 3.9.26 | Frontend: Recommendations dashboard | Frontend | 16h | 3.9.11 | ⬜ |
| 3.9.27 | Frontend: Forecast visualization | Frontend | 8h | 3.9.12 | ⬜ |
| 3.9.28 | Frontend: Webhook management | Frontend | 8h | 3.9.23 | ⬜ |
| 3.9.29 | E2E analytics tests | Backend | 8h | 3.9.13 | ⬜ |
| 3.9.30 | E2E notification tests | Backend | 8h | 3.9.21 | ⬜ |

**Acceptance Criteria:**
- [ ] Trends ML-enhanced with forecasts
- [ ] Anomalies detected by ML engine and flagged in UI
- [ ] Industry-specific benchmarks in analytics
- [ ] Recommendations dashboard shows actionable insights
- [ ] Webhooks delivered reliably with HMAC signatures
- [ ] PWA push notifications for critical alerts
- [ ] Alerts trigger on ML anomaly + signal conditions

### 6.4 Phase 3 Deliverables

| Deliverable | Description |
|-------------|-------------|
| Industry Ontology System | 10+ industries, domain taxonomies, 100+ catalog templates |
| Signal Contract System | Enterprise-grade, ontology-validated, catalog-based |
| Signal Management | Instantiation, values, history, ML scores, confidence decomposition |
| Source Management | Industry-tagged, reliability-scored |
| Acquisition & Refinement Pipelines | Scheduled fetching, ontology-enhanced normalization |
| Lightweight ML Engine | Anomaly detector, signal scorer, trend forecaster, cluster engine |
| Recommendation Engine | Actionable insights with confidence and action items |
| Simulation Mode | Realistic simulated data for starter tier |
| Deep Live Search | Multi-source parallel search with semantic ranking |
| On-Demand Synthesis | LLM-powered signal synthesis with ML scoring |
| AI Chat Agent | Conversational intelligence with tool orchestration |
| Analytics Dashboard | ML-enhanced trends, anomalies, forecasts, industry benchmarks |
| Notification System | Webhooks, alerts, PWA push notifications |

### 6.5 Phase 3 Exit Criteria (MVP Definition)

| Criterion | Validation |
|-----------|------------|
| User can define contract (from catalog or custom) | E2E test |
| Contracts validated against industry ontology | E2E test |
| Signals populate automatically with ML scoring | Acquisition runs |
| Confidence ≥ 0.85 on delivered signals | Metric check |
| User can ask questions via chat agent | Chat E2E test |
| Deep search returns ranked results | Search E2E test |
| Recommendations generated with action items | E2E test |
| Simulation mode works for starter tier | E2E test |
| Trends visible with ML forecasts | Dashboard shows data |
| Alerts work (webhook + push) | Notification received |
| 10 beta users onboarded | User acceptance |

### 6.6 Stop Condition (CRITICAL)

**STOP WHEN:**
1. ✅ Core user jobs (track signals + ask questions + get recommendations) work end-to-end
2. ✅ User can repeat the action (create contracts, query signals, chat, search)
3. ✅ Data persists correctly (signals, evidence, chat history stored)
4. ✅ Intelligence quality ≥ 0.85 confidence threshold maintained
5. ✅ Errors are understandable (clear messages)
6. ✅ One analytics signal fires (track usage)

> **"Phase 3 core product loop delivered. Do not expand scope."**

---

## 7. Phase 4: Scale & Hardening (Post-PMF)

**Status:** DEFERRED
**Trigger:** After Product-Market Fit confirmed

### 7.1 Deferred Work Packages (DO NOT IMPLEMENT NOW)

| WP | Name | Trigger |
|----|------|---------|
| 4.1 | Autonomous Signal Discovery | 1000 signals created |
| 4.2 | Real-Time Streaming (Kafka) | Low-latency requirements |
| 4.3 | Multi-Region Deployment | International customers |
| 4.4 | GPU-Based ML Training | Custom model requests |
| 4.5 | SOC 2 Compliance | Enterprise deals require |
| 4.6 | Advanced RBAC (Attribute-Based) | Complex org structures |
| 4.7 | Workflow Automation | Integration requests |
| 4.8 | Voice Interface | User demand validated |
| 4.9 | Custom ML Model Upload | Power user requests |

> Note: ML models, chat agent, deep search, PWA, ontology, and recommendations are now IN SCOPE for Phase 3.

### 7.2 Scaling Triggers

| Metric | Current | Trigger | Action |
|--------|---------|---------|--------|
| Users | <100 | 1,000 | Scale compute |
| Signals | <10,000 | 100,000 | Partition tables |
| QPS | <50 | 500 | Add replicas |
| Latency P95 | <500ms | >2s | Optimize queries |
| ML models | 5 | 20+ | GPU inference |
| Chat sessions | <1000/day | 10,000/day | Scale LLM |

---

## 8. Work Breakdown Structure (WBS)

### 8.1 WBS Summary

```
1.0 ESIP Implementation
├── 1.1 Phase 0: Strategy & Discovery (2 weeks)
│   ├── 1.1.1 Requirements Finalization
│   ├── 1.1.2 Technical Planning (incl. ontology design)
│   └── 1.1.3 Environment Setup
│
├── 1.2 Phase 1: Foundation (4 weeks)
│   ├── 1.2.1 Authentication System (extended RBAC)
│   ├── 1.2.2 Organization & User Management (industry linkage)
│   ├── 1.2.3 Database Setup (pgvector-enabled)
│   ├── 1.2.4 Redis Setup
│   └── 1.2.5 API Framework (SSE streaming)
│
├── 1.3 Phase 2: Infrastructure Validation (4 weeks)
│   ├── 1.3.1 CI/CD Pipeline
│   ├── 1.3.2 Azure Infrastructure (Blob for ML models)
│   ├── 1.3.3 Observability Stack (ML/chat/search panels)
│   ├── 1.3.4 Security Hardening (chat/search rate limits)
│   └── 1.3.5 Frontend Infrastructure (PWA)
│
├── 1.4 Phase 3: Product Construction (16 weeks)
│   ├── 1.4.1 Industry Ontology & Enterprise Signal Catalog
│   ├── 1.4.2 Signal Contract System (Ontology-Aware)
│   ├── 1.4.3 Entity Management (ML-Enhanced)
│   ├── 1.4.4 Signal Core + Source Management
│   ├── 1.4.5 Evidence, Acquisition & Refinement Pipelines
│   ├── 1.4.6 Lightweight ML Engine & Recommendation Engine
│   ├── 1.4.7 Deep Live Search & On-Demand Synthesis
│   ├── 1.4.8 AI Chat Agent
│   └── 1.4.9 Analytics, Trends & Notifications
│
└── 1.5 Phase 4: Scale & Hardening (DEFERRED)
    └── (Post-PMF)
```

### 8.2 WBS Dictionary

| WBS ID | Name | Description | Duration | Dependencies |
|--------|------|-------------|----------|--------------|
| 1.1 | Phase 0 | Strategy & discovery (incl. ontology design) | 2 weeks | None |
| 1.2 | Phase 1 | Foundation (pgvector, SSE, extended RBAC) | 4 weeks | 1.1 |
| 1.3 | Phase 2 | Infrastructure validation (PWA, ML metrics) | 4 weeks | 1.2 |
| 1.4 | Phase 3 | Product construction (full intelligence stack) | 16 weeks | 1.3 |
| 1.5 | Phase 4 | Scale & hardening | TBD | PMF achieved |

### 8.3 Effort Estimates Summary

| Phase | Backend | Frontend | ML Engineer | DevOps | Total |
|-------|---------|----------|-------------|--------|-------|
| Phase 0 | 40h | 0h | 24h | 16h | 80h |
| Phase 1 | 168h | 48h | 16h | 40h | 272h |
| Phase 2 | 96h | 88h | 0h | 80h | 264h |
| Phase 3 | 640h | 368h | 480h | 40h | 1,528h |
| **Total** | **944h** | **504h** | **520h** | **176h** | **2,144h** |

> Total effort increased from 1,096h → 2,144h (+96%) due to AI Chat Agent, Deep Live Search, Lightweight ML Engine, Industry Ontology System, PWA, Recommendation Engine, and Simulation Mode added to MVP scope.

---

## 9. Resource Allocation

### 9.1 Team Capacity

| Role | FTE | Weekly Hours | Total Capacity (26 weeks) |
|------|-----|--------------|---------------------------|
| Tech Lead | 1.0 | 40h | 1,040h |
| Backend Engineer 1 | 1.0 | 40h | 1,040h |
| Backend Engineer 2 | 1.0 | 40h | 1,040h |
| ML / Intelligence Eng | 1.0 | 40h | 1,040h |
| Frontend Engineer | 1.0 | 40h | 1,040h |
| DevOps Engineer | 0.5 | 20h | 520h |
| **Total** | **5.5** | **220h** | **5,720h** |

### 9.2 Allocation by Phase

| Phase | Duration | Team Allocation |
|-------|----------|-----------------|
| Phase 0 | 2 weeks | Tech Lead (80%), PM (100%), ML Eng (60%) |
| Phase 1 | 4 weeks | Tech Lead (50%), BE1 (100%), BE2 (100%), ML Eng (20%), FE (50%), DevOps (50%) |
| Phase 2 | 4 weeks | Tech Lead (30%), BE1 (50%), BE2 (50%), FE (80%), DevOps (100%) |
| Phase 3 | 16 weeks | Tech Lead (30%), BE1 (100%), BE2 (100%), ML Eng (100%), FE (100%), DevOps (20%) |

### 9.3 Sprint Assignments (Phase 3)

| Sprint | Backend 1 | Backend 2 | ML Engineer | Frontend |
|--------|-----------|-----------|-------------|----------|
| 3.1 | Ontology API | Catalog service | Ontology seed data + matcher | Ontology browser |
| 3.2 | Contract CRUD | Contract validation | Contract ontology validation | Contract UI + catalog wizard |
| 3.3 | Entity CRUD | Entity merge | ML entity resolution | Entity list |
| 3.4 | Signal CRUD | Source adapters | Signal scorer integration | Signal UI + confidence bar |
| 3.5 | Acquisition pipeline | Refinement pipeline | Confidence decomposition | Evidence display |
| 3.6 | Recommendation svc | ML integration | ML models + simulation | Recommendation UI + ML display |
| 3.7 | Search orchestrator | Synthesis logic | Semantic ranker + query expansion | Search UI + synthesis UI |
| 3.8 | Chat API + SSE | Analytics API + webhooks | Chat agent core + tools | Chat UI + analytics dashboard |

---

## 10. Risk Management

### 10.1 Risk Register

| ID | Risk | Probability | Impact | Mitigation | Owner |
|----|------|-------------|--------|------------|-------|
| R1 | Auth0 integration complexity | Medium | High | Spike first, fallback plan | Tech Lead |
| R2 | LLM rate limits/costs (increased with chat agent) | High | High | Cache responses, budget alerts, model fallback | Backend |
| R3 | Source reliability | High | Medium | Health scoring, fallbacks | Backend |
| R4 | Team velocity lower than estimated | Medium | High | Buffer 20%, scope flexibility | PM |
| R5 | Database performance (pgvector at scale) | Medium | High | Query monitoring, indexes, HNSW tuning | Backend |
| R6 | Third-party API changes | Medium | Medium | Adapter abstraction | Backend |
| R7 | Security vulnerability discovered | Low | Critical | Security audit, quick patch | Tech Lead |
| R8 | ML model accuracy below threshold | Medium | High | Fallback to statistical methods, retrain frequently | ML Eng |
| R9 | Chat agent hallucination | High | Medium | Citation requirement, confidence gates, tool-only answers | ML Eng |
| R10 | Ontology data quality | Medium | High | Expert review, iterative refinement | ML Eng |
| R11 | Phase 3 scope creep (16 weeks is ambitious) | High | High | Strict sprint goals, cut non-critical features | Tech Lead |

### 10.2 Risk Responses

| Risk ID | Response Type | Action |
|---------|---------------|--------|
| R1 | Mitigate | Complete auth spike in Week 1 |
| R2 | Transfer | Set hard budget limits $500/mo, use GPT-4 Turbo mini for simple queries |
| R3 | Accept | Build for eventual consistency |
| R4 | Mitigate | Cut scope, not quality |
| R5 | Mitigate | Performance testing in Phase 2, index tuning |
| R6 | Mitigate | Adapter pattern isolates changes |
| R7 | Mitigate | Immediate patch, post-mortem |
| R8 | Mitigate | Statistical fallbacks, model A/B testing |
| R9 | Mitigate | Mandatory citations, tool-grounded responses only |
| R10 | Mitigate | Expert review per industry, community feedback |
| R11 | Mitigate | Weekly scope review, protect critical path |

### 10.3 Contingency Plans

| Trigger | Response |
|---------|----------|
| Phase 1 > 6 weeks | Reduce Phase 3 scope to core signals + search |
| Phase 2 > 6 weeks | Deploy to simpler infrastructure |
| LLM costs > $500/mo | Disable chat for free tier, use cheaper models |
| ML accuracy < 0.70 | Revert to statistical confidence only |
| Chat agent hallucinating | Restrict to tool-only responses (no free generation) |
| Team member leaves | Prioritize documentation, pair programming |
| Phase 3 > 18 weeks | Defer simulation mode and advanced analytics to Phase 4 |

---

## 11. Quality Gates

### 11.1 Code Quality Gates

| Gate | Criteria | Enforcement |
|------|----------|-------------|
| Commit | Tests pass locally | Pre-commit hooks |
| Pull Request | CI passes, 1 review | GitHub protection |
| Merge | All checks green | Branch protection |
| Deploy Staging | Smoke tests pass | Automated |
| Deploy Production | Manual approval | Required |

### 11.2 Intelligence Quality Gates

| Gate | Criteria | Enforcement |
|------|----------|-------------|
| Signal Confidence | ≥ 0.85 for delivery | Pipeline gate |
| ML Model Accuracy | ≥ 0.80 on test set | Model registry gate |
| Chat Citation Rate | ≥ 95% of factual claims cited | Prompt engineering + audit |
| Recommendation Actionability | Each rec has ≥ 1 action item | Schema validation |
| Ontology Coverage | ≥ 80% entity types per industry | Seed data validation |

### 11.3 Definition of Done (DoD)

A task is DONE when:

- [ ] Code written and compiles
- [ ] Unit tests written and pass (>80% coverage)
- [ ] Integration test written (if applicable)
- [ ] Documentation updated
- [ ] Code reviewed and approved
- [ ] Deployed to staging
- [ ] Smoke tested in staging
- [ ] Intelligence quality gates pass (if ML/chat/search feature)
- [ ] Product acceptance (if user-facing)

### 11.4 Sprint Quality Metrics

| Metric | Target |
|--------|--------|
| Test coverage | >80% |
| Build success rate | >95% |
| Bug escape rate | <5% |
| Code review turnaround | <24h |
| Deployment frequency | Daily |
| Signal confidence average | ≥0.85 |
| Chat response quality | ≥4/5 user rating |

---

## 12. Dependencies & Critical Path

### 12.1 Dependency Graph

```
Phase 0 ──────────┐
                  │
                  ▼
            ┌─────────┐
            │ Phase 1 │
            │ Foundation
            └────┬────┘
                 │
        ┌────────┼────────┐
        │        │        │
        ▼        ▼        ▼
    ┌──────┐ ┌──────┐ ┌──────┐
    │ Auth │ │ DB+  │ │ API+ │
    │      │ │pgvec │ │ SSE  │
    └──┬───┘ └──┬───┘ └──┬───┘
       │        │        │
       └────────┼────────┘
                │
                ▼
            ┌─────────┐
            │ Phase 2 │
            │ Infra+  │
            │ PWA     │
            └────┬────┘
                 │
        ┌────────┼────────┐
        │        │        │
        ▼        ▼        ▼
    ┌──────┐ ┌──────┐ ┌──────┐
    │ CI/CD│ │ Obs  │ │ PWA  │
    └──┬───┘ └──┬───┘ └──┬───┘
       │        │        │
       └────────┼────────┘
                │
                ▼
            ┌─────────┐
            │ Phase 3 │
            │ Product │
            └────┬────┘
                 │
         ┌───────┼───────────────┐
         │       │               │
         ▼       ▼               ▼
    ┌──────┐ ┌──────────┐  ┌──────────┐
    │Ontol.│ │Contracts │  │ Sources  │
    │System│ │+ Signals │  │+ Fetch   │
    └──┬───┘ └─────┬────┘  └────┬─────┘
       │           │             │
       └───────────┼─────────────┘
                   │
         ┌─────────┼───────────┐
         │         │           │
         ▼         ▼           ▼
    ┌──────┐  ┌──────────┐ ┌──────────┐
    │  ML  │  │  Deep    │ │  Chat    │
    │Engine│  │  Search  │ │  Agent   │
    └──┬───┘  └─────┬────┘ └────┬─────┘
       │            │            │
       └────────────┼────────────┘
                    │
                    ▼
            ┌─────────────┐
            │ Analytics + │
            │ Recommend.  │
            │ + Notify    │
            └─────────────┘
```

### 12.2 Critical Path

The critical path determines the minimum project duration:

```
Phase 0 → Phase 1 (DB+pgvector) → Phase 2 (CI/CD+PWA) → Phase 3:
  → Ontology → Contracts → Signals → Pipeline → ML Engine → Search/Synthesis → Chat Agent → Analytics

Total: 2 + 4 + 4 + 16 = 26 weeks
```

### 12.3 External Dependencies

| Dependency | Type | Risk | Mitigation |
|------------|------|------|------------|
| Auth0 | Service | Medium | Fallback auth plan |
| Neon PostgreSQL (pgvector) | Service | Low | Multi-region available |
| Upstash Redis | Service | Low | Self-hosted fallback |
| OpenAI API (GPT-4 Turbo) | Service | Medium | Azure OpenAI backup, GPT-4 mini fallback |
| Azure | Platform | Low | Established platform |
| scikit-learn / ONNX | Library | Very Low | Stable, well-maintained |

---

## 13. Communication Plan

### 13.1 Regular Meetings

| Meeting | Frequency | Duration | Attendees | Purpose |
|---------|-----------|----------|-----------|---------|
| Daily Standup | Daily | 15 min | Dev team | Progress, blockers |
| Sprint Planning | Bi-weekly | 2 hours | All | Sprint scope |
| Sprint Review | Bi-weekly | 1 hour | All + stakeholders | Demo |
| Sprint Retro | Bi-weekly | 1 hour | Dev team | Improve process |
| Tech Sync | Weekly | 30 min | Engineers | Technical decisions |
| ML/Intelligence Review | Weekly | 30 min | ML Eng + Tech Lead | Model quality, ontology quality |

### 13.2 Communication Channels

| Channel | Purpose | Participants |
|---------|---------|--------------|
| Slack #dev | Daily dev communication | Dev team |
| Slack #ml-quality | ML model quality + ontology updates | ML Eng, Tech Lead |
| Slack #alerts | System alerts | All |
| GitHub Issues | Task tracking | Dev team |
| Notion/Confluence | Documentation | All |
| Email | Stakeholder updates | PM, stakeholders |

### 13.3 Stakeholder Updates

| Stakeholder | Frequency | Format | Content |
|-------------|-----------|--------|---------|
| Leadership | Weekly | Email | Progress summary |
| Investors | Monthly | Deck | Milestones, metrics |
| Beta users | Bi-weekly | Email | New features, feedback request |

### 13.4 Escalation Path

```
Developer → Tech Lead → CTO → Stakeholders
    ↓
  (If blocked > 4 hours, escalate)
```

---

## 14. Success Metrics

### 14.1 Phase Success Metrics

| Phase | Metric | Target |
|-------|--------|--------|
| Phase 0 | Documents complete (incl. ontology v1) | 100% |
| Phase 1 | Auth + pgvector E2E working | Yes |
| Phase 2 | CI/CD green, PWA installable | Yes |
| Phase 3 | Beta users onboarded | 10 |
| Phase 3 | User can complete all 3 core jobs | Yes |
| Phase 3 | Average signal confidence | ≥ 0.85 |

### 14.2 Product Success Metrics (MVP)

| Metric | Definition | Target |
|--------|------------|--------|
| Activation | User creates first contract (or uses catalog) | 50% of signups |
| Engagement | User queries signals or uses chat weekly | 30% WAU |
| Chat adoption | User starts chat session | 40% of active users |
| Search usage | User performs deep search | 50% of active users |
| Retention | User returns after 30 days | 40% |
| NPS | Net Promoter Score | > 30 |
| Recommendation action rate | User acts on recommendation | 20% |

### 14.3 Technical Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Availability | 99.5% | Uptime monitoring |
| API Latency P95 | <500ms | APM |
| Chat first token P95 | <1.5s | APM |
| Search P95 | <5s | APM |
| ML inference P95 | <50ms | APM |
| Error rate | <1% | Sentry |
| Test coverage | >80% | CI reports |
| Signal confidence avg | ≥0.85 | Signal metrics |
| Deploy frequency | Daily | CI/CD |

### 14.4 Cost Success Metrics

| Resource | Monthly Budget | Alert Threshold |
|----------|----------------|-----------------|
| Azure Compute | $250 | $200 |
| Neon Database | $70 | $55 |
| Upstash Redis | $40 | $30 |
| OpenAI API (synthesis + chat + embeddings) | $500 | $400 |
| Azure Blob Storage (ML models + evidence) | $30 | $25 |
| Auth0 | $0 (free tier) | N/A |
| **Total** | **$890** | **$710** |

> Budget increased from $580 → $890 due to higher OpenAI usage (chat agent + deeper synthesis + more embeddings) and blob storage for ML model artifacts.

---

## 15. Appendices

### 15.1 Appendix A: Technology Stack

| Layer | Technology | Version | Purpose |
|-------|------------|---------|---------|
| Backend | Python | 3.11+ | Core language |
| Framework | FastAPI | 0.109+ | Async API framework |
| ORM | SQLAlchemy | 2.0+ | Database access |
| Database | PostgreSQL + pgvector | 16+ | Primary store + vector search |
| Cache | Redis | 7+ | Cache, queue, rate limits |
| Frontend | Next.js (PWA) | 14+ | Installable web application |
| UI | Tailwind + Shadcn | Latest | Component library |
| Auth | Auth0 | Latest | Identity + SSO |
| AI/LLM | OpenAI GPT-4 Turbo | Latest | Synthesis, chat, intent parsing |
| ML | scikit-learn + ONNX | Latest | Lightweight models |
| Embeddings | OpenAI text-embedding-3-small | Latest | Semantic search |
| Cloud | Azure Container Apps | Latest | Serverless hosting |
| Storage | Azure Blob | Latest | ML models, evidence files |
| CDN | Azure Front Door | Latest | PWA static assets |

### 15.2 Appendix B: Environment Setup Guide

```bash
# Clone repository
git clone https://github.com/org/esip.git
cd esip

# Backend setup
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\Activate.ps1 on Windows
pip install -r requirements.txt

# Environment variables
cp .env.example .env
# Edit .env with your values (Auth0, OpenAI, Neon, Upstash)

# Database setup (pgvector-enabled)
docker-compose up -d db redis
alembic upgrade head

# Seed industry ontology data
python -m backend.ontology.loader --seed

# Run backend
uvicorn backend.main:app --reload

# Frontend setup (new terminal)
cd frontend
npm install
npm run dev

# ML model initialization (optional, for development)
python -m backend.ml.model_registry --init
```

### 15.3 Appendix C: API Quick Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/contracts` | GET/POST | List/Create contracts |
| `/api/v1/contracts/from-catalog` | POST | Create from catalog template |
| `/api/v1/signals` | GET | List signals (with ML scores) |
| `/api/v1/signals/query` | POST | Query signals (ontology filters) |
| `/api/v1/signals/synthesize` | POST | On-demand synthesis |
| `/api/v1/signals/{id}/recommendations` | GET | Signal recommendations |
| `/api/v1/chat/sessions` | POST | Create chat session |
| `/api/v1/chat/sessions/{id}/messages` | POST | Send message (SSE streaming) |
| `/api/v1/search` | POST | Deep live search |
| `/api/v1/search/discover` | POST | Discover new sources |
| `/api/v1/ontology/industries` | GET | List industries |
| `/api/v1/ontology/industries/{code}/catalog` | GET | Signal catalog |
| `/api/v1/analytics/trends` | GET | ML-enhanced trends |
| `/api/v1/analytics/anomalies` | GET | ML-detected anomalies |
| `/api/v1/analytics/forecast` | GET | ML trend forecasts |
| `/api/v1/analytics/recommendations` | GET | Active recommendations |
| `/health` | GET | Health check |

### 15.4 Appendix D: Glossary

| Term | Definition |
|------|------------|
| Signal | A verified change or observation with confidence, lineage, and ML scoring |
| Contract | Enterprise-grade declarative specification validated against industry ontology |
| Entity | Business object with ML-resolved identity |
| Evidence | Raw data with provenance, stored with embeddings |
| Synthesis | Creating signals from live data using LLM + ML |
| Acquisition | Fetching data from sources on schedule |
| Refinement | Normalizing raw data with ontology enrichment |
| Industry Ontology | Structured domain knowledge per industry vertical |
| Domain Taxonomy | Hierarchical classification within an industry |
| Signal Catalog | Pre-built, industry-validated signal contract templates |
| AI Chat Agent | Conversational interface with tool orchestration |
| Deep Live Search | Multi-source parallel search with semantic ranking |
| Recommendation | Actionable insight with confidence and action items |
| ML Engine | Lightweight CPU-based ML for anomaly detection, scoring, forecasting |
| Simulation Mode | Simulated data generation for starter tier exploration |
| Confidence Decomposition | source_coverage + freshness + agreement + ml_score |
| PWA | Progressive Web Application — installable, offline-capable |

### 15.5 Appendix E: Decision Log

| Date | Decision | Rationale | Status |
|------|----------|-----------|--------|
| 2026-02-09 | Use FastAPI | Async, typed, auto-docs | Approved |
| 2026-02-09 | Use Neon PostgreSQL + pgvector | Serverless, cost-efficient, vector search | Approved |
| 2026-02-09 | Use Auth0 | Enterprise SSO, RBAC | Approved |
| 2026-02-09 | Use Azure | Existing relationship | Approved |
| 2026-02-09 | Use scikit-learn + ONNX for ML | Lightweight, CPU-only, fast inference | Approved |
| 2026-02-09 | PWA instead of native mobile | Lower cost, single codebase, installable | Approved |
| 2026-02-09 | AI Chat Agent in MVP | Core differentiator, natural language intelligence | Approved |
| 2026-02-09 | Deep Live Search in MVP | Enterprise-grade discovery, not basic text search | Approved |
| 2026-02-09 | Industry Ontology System in MVP | Domain accuracy is non-negotiable | Approved |
| 2026-02-09 | Confidence threshold 0.85 | High trust requirement for enterprise decisions | Approved |
| 2026-02-09 | Simulation mode for starter tier | Lower onboarding friction | Approved |
| 2026-02-09 | Defer Kafka | Complexity not needed yet | Deferred |
| 2026-02-09 | Defer multi-region | Scale not needed yet | Deferred |
| 2026-02-09 | Defer GPU ML training | Lightweight models sufficient for MVP | Deferred |
| 2026-02-09 | Phase 3 expanded to 16 weeks | Accommodate new in-scope features | Approved |

---

## Document Approval

| Role | Name | Date | Signature |
|------|------|------|-----------|
| CTO | | | |
| Engineering Lead | | | |
| ML Lead | | | |
| Product Manager | | | |

---

**End of Implementation Planning Document v2.0**
