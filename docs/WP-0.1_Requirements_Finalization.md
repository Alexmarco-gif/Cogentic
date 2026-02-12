# WP-0.1 — Requirements Finalization Deliverable

**Document Version:** 1.0
**Date:** 2026-02-09
**Status:** ✅ APPROVED
**Phase:** 0 — Strategy & Discovery
**Work Package:** WP-0.1 — Requirements Finalization

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [MVP Personas](#2-mvp-personas)
3. [Day-1 User Journeys](#3-day-1-user-journeys)
4. [MVP Scope Definition](#4-mvp-scope-definition)
5. [Target Industries](#5-target-industries)
6. [Seeded Signal Strategy](#6-seeded-signal-strategy)
7. [Intelligence Briefs — Day-1 Catalog](#7-intelligence-briefs--day-1-catalog)
8. [Key Design Decisions](#8-key-design-decisions)
9. [Exit Criteria Checklist](#9-exit-criteria-checklist)

---

## 1. Executive Summary

ESIP (Enterprise Signal Intelligence Platform) MVP requirements have been finalized through a structured Q&A process. The product is a **It’s closer to Bloomberg’s information density, Similarweb’s clarity,\and Notion’s composability, but applied to a signal-first intelligence system instead of data or documents.** intelligence platform that aggregates real-time signals from public and semi-public sources, API's, Web, Socials, synthesizes them through AI, and delivers actionable intelligence briefs to enterprise users.

**Day-1 Philosophy:** *"Belief, not power"* — deliver one credible insight fast, with the reasoning to trust it.

**Approach:** Build everything lightweight but strong enough to be scalable, resilent, standard. Wide surface, thin depth. No scope cuts — only 3 explicit exclusions.

---

## 2. MVP Personas

### 2.1 Analyst (Primary)
- **Title:** Intelligence Analyst, Market Research Analyst, Strategy Analyst
- **Core Need:** Ask a question → get a synthesized answer with evidence
- **Skill Level:** Intermediate-to-advanced research capability
- **Usage Pattern:** Daily, deep dives, multiple queries per session
- **Success Metric:** Time-to-insight < 30 seconds for first credible result

### 2.2 Decision-Maker (Primary)
- **Title:** VP Strategy, Head of Product, C-Suite, Department Lead
- **Core Need:** Read one intelligence brief → make a decision
- **Skill Level:** Low patience for raw data, needs structured conclusions
- **Usage Pattern:** Weekly, consumes briefs, uses Decision Lens
- **Success Metric:** Can trust a brief enough to act on it within 2 minutes

### 2.3 Operator (Primary)
- **Title:** Platform Engineer, Data Engineer, Integration Specialist
- **Core Need:** Inspect API → get sample payloads → integrate into internal systems
- **Skill Level:** Technical, evaluates data quality and contract reliability
- **Usage Pattern:** During setup/integration phases, then periodic monitoring
- **Success Metric:** Working API integration within 15 minutes of onboarding

---

## 3. Day-1 User Journeys

### 3.1 Analyst Journey — "First Credible Insight"

```
Login → SimilarWeb-style Home
  → Search Bar: "What do you want to know?"
  → AI Synthesis Engine processes query
  → Result Page:
      • Synthesis paragraph (BLUF — Bottom Line Up Front)
      • Evidence panel (3-5 source signals with confidence scores)
      • Related signals sidebar
      • "Ask follow-up" input
  → Analyst reads, clicks a source, verifies
  → BELIEF ACHIEVED: "This platform found something I didn't know"
```

**Key Moment:** The synthesis must include at least ONE signal the analyst didn't already know. That's the hook.

### 3.2 Decision-Maker Journey — "One Brief, One Decision"

```
Login → SimilarWeb-style Home
  → Intelligence Briefs section (pre-built, industry-specific)
  → Clicks: "Competitive Pricing & Promotion Intelligence — Retail"
  → Brief Structure:
      • Title + BLUF (2 sentences max)
      • Argument + Evidence (structured, sourced)
      • Outlook & Implications
      • Decision Lens: "What this means for you" panel
  → Decision-Maker reads in 2 minutes
  → BELIEF ACHIEVED: "This brief saved me 3 hours of research"
```

**Key Moment:** The brief must feel *written for them*, not generic. Industry-specific language, relevant competitors named.

### 3.3 Operator Journey — "API in 15 Minutes"

```
Login → SimilarWeb-style Home
  → Search / "what you want to know"
  → Clicks / Analytics and Comparison on signals and update
  → API Documentation page:
      • Endpoint catalog
      • Sample payloads (copy-paste ready)
      • SDKs / curl examples
  → Operator runs first API call
  → Gets structured JSON response with signals
  → BELIEF ACHIEVED: "This data is clean and I can integrate it"
```

**Key Moment:** Sample payloads must return REAL data, not mocked responses.

---

## 4. MVP Scope Definition

### 4.1 Scope Philosophy
> **Build everything lightweight. Wide surface, thin depth.**
> No role-based home pages. Single SimilarWeb-style interface for all personas.

### 4.2 IN Scope — MVP Features (Lightweight Implementations)

| Feature | MVP Implementation | Depth |
|---|---|---|
| **Signal Contracts** | 70 signals per industry × 5 industries = 350 seeded | Lightweight |
| **Signal Acquisition Pipeline** | Scheduled fetchers (API + scraper) | Lightweight |
| **Signal Refinement Pipeline** | NLP extraction, dedup, confidence scoring | Lightweight |
| **Industry Ontology** | 4 industry taxonomies with entity mapping | Lightweight |
| **Signal Catalog** | Browse/filter/search signals by industry, entity, type | Lightweight |
| **AI Synthesis Engine** | GPT-4o Turbo query → multi-signal synthesis | Lightweight |
| **AI Chat Agent** | Follow-up questions, conversational refinement | Lightweight |
| **Deep Live Search** | Real-time source querying on user demand | Lightweight |
| **Intelligence Briefs** | 20 pre-built briefs (5 per industry), auto-refreshing | Lightweight |
| **Decision Lens** | "What this means for you" panel on each brief | Lightweight |
| **Recommendation Engine** | "Related signals" and "You might also need" | Lightweight |
| **ML Pipeline** | Anomaly detection, confidence scoring, trending | Lightweight |
| **Lightweight ML Models** | scikit-learn + ONNX, simple models | Lightweight |
| **PWA (Progressive Web App)** | Installable, offline shell, push notifications | Lightweight |
| **Situation Room** | Live dashboard per industry, real-time signal feed | Lightweight |
| **API & Developer Portal** | Full REST API, docs, sample payloads, API keys | Lightweight |
| **Enterprise RBAC** | Roles, permissions, org-level isolation (already built) | Complete |
| **Multi-tenancy** | Org-scoped data, tenant isolation (already built) | Complete |

### 4.3 OUT of Scope — MVP Exclusions (Only 3)

| Exclusion | Rationale |
|---|---|
| **Autonomous Discovery** | Requires mature signal graph + heavy compute. Phase 4+. |
| **Forecasting & Predictions** | Needs 6+ months of signal history for reliable models. Phase 4+. |
| **Workflow Automation** | Alerting/triggers/actions layer. Phase 4+, after core trust is established. |

### 4.4 Simulation Mode — KILLED for Day-1
Replaced with **Guided Live + Seeded Signals** strategy:
- 280 real signals pre-seeded before launch
- Live data from real sources from Day-1
- No fake/simulated data — everything is real, just curated

---

## 5. Target Industries

### 5.1 Launch Industries (5)

| # | Industry Cluster | Sub-verticals |
|---|---|---|
| 1 | **E-Commerce / FMCG / Retail** | Online retail, pricing, competitor pricing, customer behavior segment, trends and customer movement, consumer packaged goods, grocery, fashion, drive conversion, optimization, marketplace |
| 2 | **Financial Services & Fintech** | Banking, insurance, payment processors, credit, lending, risk, neobanks, crypto, lending |
| 3 | **Media / Marketing / Consumer & Brand** | Advertising, social media, content platforms, consumer analytics, campaign performance, PR, brand management |
| 4 | **Telecom / Digital Services / Infrastructure** | Mobile carriers, ISPs, analytics on network data, churn prediction, pricing competition, data usage, tower companies, cloud infra, digital services |
| 5 | **Agriculture & Agritech (AgriBusiness)** | Crop farming, livestock, agritech innovation, supply chain & logistics, agricultural inputs, yield forecasting, weather patterns, soil health, market pricing, commodity trading |

### 5.2 Data Sources

| Source Type | Examples |
|---|---|
| **Real-time APIs** | News APIs, financial data feeds, social media APIs |
| **Public Web** | Company websites, press releases, job postings, patent filings, public websites, blog, regional based website |
| **Semi-public** | App store rankings, ad libraries, regulatory filings, SEC/FCC |
| **Social & Community** | Twitter/X, Reddit, LinkedIn, review platforms, forums, regional based, state based,country based |
| **Government & Regulatory** | Government gazettes, policy announcements, spectrum auctions |

### 5.3 Signal Distribution
- **70 signals per industry** (350 total seeded for Day-1)
- Signals mapped to industry ontology entities
- Each signal has: source, confidence score, freshness, entity links, type classification

---

## 6. Seeded Signal Strategy

### 6.1 Signal Seeding Approach
- Pre-launch: Build 350 signal contracts across 5 industries
- Each contract defines: source URL/API, extraction rules, refresh frequency, entity mapping
- Signals are LIVE from Day-1 — fetched from real sources on schedule
- No mocked/simulated data in production

### 6.2 Signal-to-Brief Ratio
- **~14 signals per intelligence brief** (70 signals ÷ 5 briefs per industry)
- Each brief aggregates multiple signals into a coherent narrative
- Briefs auto-refresh as underlying signals update

### 6.3 Confidence & Quality
- Every signal carries a **confidence score** (0.0–1.0)
- Target: ≥ 0.85 average confidence for brief-eligible signals
- Signals below 0.6 confidence are flagged but not included in briefs
- Source diversity: each brief pulls from ≥ 3 distinct source types

---

## 7. Intelligence Briefs — Day-1 Catalog

### Brief Structure (Locked)
```
1. Checklist (internal — completeness validation)
2. Title + BLUF (2 sentences max — the answer first)
3. Argument + Evidence (structured, sourced, confidence-scored)
4. Finishing Touches:
   • Outlook (what's likely next)
   • Implications (what this means for the reader)
   • Decision Lens (actionable takeaway)
```

### 7.1 E-Commerce / FMCG / Retail (5 Briefs)

| # | Brief Title | Problem Solved | Confidence |
|---|---|---|---|
| 1 | **Competitive Pricing & Promotion Intelligence** | Am I priced right? What are competitors promoting? | 🟢 Very High |
| 1 | **Forcasting Pricing Optimization** | How can I optimize pricing based on forecasted demand and competitor actions? | 🟢 Very High |
| 1 | **Trends and Customers Behavior** | What are the latest trends and how are customers behaving? | 🟢 Very High |
| 1 | **Retailers live or die by data** | How can retailers leverage data to drive sales and customer loyalty? | 🟢 Very High |
| 2 | **Consumer Sentiment & Brand Health Monitor** | How do customers feel about us vs. competitors right now? | 🟢 Very High |
| 3 | **Market Entry & Expansion Signals** | Who is entering my market? New launches, hiring surges, patents? | 🟢 High |
| 4 | **Supply Chain & Disruption Risk Assessment** | What's threatening my supply chain this week? | 🟡 High |
| 5 | **Category Demand & Trend Shift Analysis** | What product categories are rising/falling? What should I stock? | 🟢 High |

### 7.2 Financial Services & Fintech (5 Briefs)

| # | Brief Title | Problem Solved | Confidence |
|---|---|---|---|
| 1 | **Regulatory & Compliance Change Tracker** | What regulations are changing that affect my business? | 🟢 Very High |
| 1 | **Revenue Driver** | What are the key revenue drivers and how can I optimize them? | 🟢 Very High |
| 1 | **Credit Risk Pattern and Fraud detection** | How can I identify and mitigate credit risk and detect fraudulent activities? | 🟢 Very High |
| 1 | **trend insights and regulatory changes impacts** | What are the latest trends and how are regulatory changes impacting the market? | 🟢 Very High |
| 2 | **Fintech Competitive Landscape & Funding Signals** | Who raised money? Who launched what? Who's gaining ground? | 🟢 High |
| 3 | **Credit & Market Risk Signal Monitor** | What risk am I exposed to right now across sectors? | 🟢 High |
| 4 | **Digital Banking & Payment Adoption Trends** | Where is digital finance adoption heading? Who's winning? | 🟢 High |
| 5 | **Fraud & Cybersecurity Threat Intelligence** | What emerging threats should I prepare for this quarter? | 🟡 High |

### 7.3 Media / Marketing / Consumer & Brand (5 Briefs)

| # | Brief Title | Problem Solved | Confidence |
|---|---|---|---|
| 1 | **Audience Behavior & Content Consumption Shifts** | Where is my audience migrating? What formats are winning? | 🟢 Very High |
| 1 | **Brand Sentimental trends** | What are the current sentiment trends around my brand? | 🟢 Very High |
| 1 | **Decline Content performance** | What content is declining in performance and why? | 🟢 Very High |
| 1 | **Uptake Signals,Growing Fields Campaign Performance** | What campaigns are gaining traction and which fields are expanding? | 🟢 Very High |
| 2 | **Brand Perception & Reputation Risk Monitor** | Is my brand under threat? Are sentiment patterns shifting? | 🟢 Very High |
| 3 | **Competitive Campaign & Ad Spend Intelligence** | What are competitors spending on, where, and how much? | 🟢 High |
| 4 | **Influencer & Creator Economy Landscape** | Who should I partner with? What's the ROI signal? | 🟡 High |
| 5 | **Emerging Platform & Channel Opportunity Detection** | Where should I invest marketing dollars next? | 🟢 High |

### 7.4 Telecom / Digital Services / Infrastructure (5 Briefs)

| # | Brief Title | Problem Solved | Confidence |
|---|---|---|---|
| 1 | **5G & Network Technology Deployment Tracker** | Where is network technology heading? Who's deploying what? | 🟢 Very High |
| 1 | **Analytics to Retain Customers** | How can I retain customers using data-driven insights? | 🟢 Very High |
| 1 | **Churn Predictions** | How can I predict and reduce customer churn? | 🟢 Very High |
| 1 | **data usage trends and network quality insights** | What are the current data usage trends and how is network quality evolving? | 🟢 Very High |
| 2 | **Competitive Pricing & Bundle Strategy Intelligence** | How are competitors positioning plans and bundles against us? | 🟢 Very High |
| 1 | **Optimize services** | How can I optimize service delivery and performance? | 🟢 Very High |
| 3 | **Regulatory & Spectrum Policy Monitor** | What policy/spectrum changes affect my business this quarter? | 🟢 Very High |
| 4 | **Digital Infrastructure & Cloud Partnership Signals** | Who's building data centers? Who's partnering with whom? | 🟢 High |
| 5 | **Customer Churn & Satisfaction Risk Signals** | Where am I losing customers and why? | 🟢 High |

### 7.5 Agriculture & Agritech (AgriBusiness) (5 Briefs)

| # | Brief Title | Problem Solved | Confidence |
|---|---|---|---|
| 1 | **Yield Optimization & Weather Risk Monitor** | What's threatening my harvest this season? When should I plant/harvest? | 🟢 Very High |
| 2 | **Commodity Price Intelligence & Market Timing** | Should I sell now or wait? What's driving price volatility? | 🟢 Very High |
| 3 | **Supply Chain Efficiency & Bottleneck Detection** | Where is my produce stuck? What's causing post-harvest losses? | 🟢 High |
| 4 | **Agricultural Policy & Subsidy Opportunity Tracker** | What programs can I access? What policy changes affect my operations? | 🟢 Very High |
| 5 | **Agritech Innovation & Adoption Signals** | What new technologies should I consider? Who's succeeding with precision agriculture? | 🟡 High |

---

## 8. Key Design Decisions

### 8.1 Architecture Decisions

|| Decision        | Choice                                                                    | Rationale                                                                                                                                                                             |
| --------------- | ------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Home Page       | **Single, unified Similarweb-style home for all personas**                | One canonical experience reinforces shared truth. Personas diverge through interaction, not routing. Reduces cognitive load, speeds onboarding, and avoids fragmented UX maintenance. |
| Simulation Mode | **Removed entirely**                                                      | Simulated or synthetic modes undermine trust. The platform operates on real signals from Day-1, with explicit confidence labeling instead of artificial environments.                 |
| MVP Scope       | **Wide surface, shallow depth (with strict exclusions)**                  | The MVP demonstrates end-to-end signal capability across the platform while avoiding premature automation. Breadth validates the signal thesis without over-engineering.              |
| Day-1 Data      | **~350 seeded, live signal contracts (70 per industry × 5 industries)**   | Predefined signal contracts provide immediate value, real coverage, and observable freshness. Users see real intelligence immediately, not an empty shell.                            |
| Brief Format    | **Structured intelligence brief (Checklist → BLUF → Evidence → Outlook)** | A standardized brief format enforces clarity, consistency, and executive readability. Every brief is scannable, defensible, and decision-oriented within minutes.                     |


### 8.2 UX Decisions
| Decision            | Choice                                                              | Rationale                                                                                                                                                         |
| ------------------- | ------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Primary Interaction | **Single home with dual entry: Search-first + Intelligence briefs** | Analysts begin with intent-driven search; decision-makers engage via curated briefs. Both coexist naturally on one home without persona switching.                |
| Trust Mechanism     | **Confidence scores, lineage, and evidence visible everywhere**     | Trust is earned through transparency. Every signal exposes confidence, provenance, and limitations, allowing users to validate conclusions themselves.            |
| Day-1 Hook          | **Deliver one credible insight the user did not already know**      | The goal is belief, not feature impressiveness. A single defensible insight builds trust faster than broad capability claims.                                     |
| Mobile Strategy     | **Progressive Web App (PWA)**                                       | PWA provides installability, offline shell, and notifications with a single codebase. It supports executive consumption without the cost and risk of native apps. |


### 8.3 Technical Decisions (Confirmed from Existing Stack)

| Component | Technology | Status |
|---|---|---|
| Backend API | FastAPI (Python 3.11+) | ✅ Built |
| Database | PostgreSQL 15 (Neon Serverless) + pgvector | ✅ Provisioned |
| Cache/Queue | Redis 7 (Upstash) + RQ | ✅ Built |
| Auth | Auth0 + JWT + RBAC | ✅ Built |
| Frontend | Next.js 14 + Tailwind | ⬜ Scaffolded only |
| AI Engine | OpenAI GPT-4o Turbo | ⬜ Not built |
| ML Pipeline | scikit-learn + ONNX | ⬜ Not built |
| Infrastructure | Azure Container Apps | ✅ Deployed (pre-prod) |

---

## 9. Exit Criteria Checklist

| # | Criterion | Status |
|---|---|---|
| 1 | MVP personas defined and approved | ✅ |
| 2 | Day-1 user journeys mapped per persona | ✅ |
| 3 | MVP feature scope locked (in/out documented) | ✅ |
| 4 | Target industries selected with rationale | ✅ (5 industries) |
| 5 | Signal seeding strategy defined (350 signals) | ✅ |
| 6 | Intelligence brief catalog defined (25 briefs) | ✅ |
| 7 | Brief structure format locked | ✅ |
| 8 | Data source types identified | ✅ |
| 9 | Key design decisions documented | ✅ |
| 10 | Existing codebase audited | ✅ |
| 11 | Critical bugs identified (auth namespace mismatch) | ✅ |

**WP-0.1 STATUS: ✅ COMPLETE — All exit criteria met.**

---

*Document generated as part of Phase 0: Strategy & Discovery*
*Next: WP-0.2 — Technical Planning*
