# Cogent Real-World Readiness Audit

Date: 2026-04-19
Author: Codex
Scope: Repo-wide product, integration, setup, and readiness audit

## 1. Executive Summary

Cogent has a meaningful amount of real backend capability:

- authenticated multi-tenant API surface
- signal acquisition pipeline
- AI chat and synthesis
- discovery and living-contract machinery
- pricing, credits, feature gates, and background jobs

The current product problem is not "there is no platform." The problem is that the user-facing experience does not yet align with the platform's intended value.

The platform currently behaves like this:

- the backend is mostly source-centric and operator-centric
- the frontend often hides failures behind polished empty states
- new environments depend on seeded data that is not automatically bootstrapped
- feature gates and role checks make key workflows inaccessible to fresh signups
- some pages present local heuristics or scaffolding as if they were real product intelligence

For real-world use, Cogent needs to shift from:

- "define a source config"

to:

- "tell Cogent what you want to monitor, and Cogent chooses, combines, and manages sources for you"

That product principle is not consistently implemented today.

## 2. Audit Method

This audit covered:

- full repo file inventory
- frontend dashboard pages
- frontend hooks and API clients
- backend API router inventory
- backend models, services, repositories, and jobs relevant to user workflows
- infrastructure and environment configuration
- seed scripts, smoke tests, and release-readiness checks

Deep review was focused on:

- files with business logic
- integration-bearing files
- auth/session/token flow
- config/setup files
- worker/AI/data pipeline files
- pages and buttons a real customer would touch

Purely visual components were inventoried and sampled, but not all were read line-by-line where they contained no data access, state transitions, or side effects.

## 3. Product Intent vs Current Design

### Intended product outcome

A user should be able to:

1. describe what they want to track in plain language
2. let Cogent infer the right monitoring strategy
3. get signals, briefs, investigations, and recommendations without technical setup

### Current implementation bias

The current contract system is still fundamentally source-oriented.

Evidence:

- `backend/models/signal_contract.py` models contracts as `source_url`, `source_type`, `refresh_cron`, and `extraction_config`
- `backend/schemas/signals.py` requires `source_url` and `source_type` for contract creation
- `backend/api/v1/contracts.py` exposes CRUD around source contracts, not intent contracts
- `frontend/components/contracts/DefinitionPane.tsx` requires users to choose:
  - source type
  - provider preset
  - source URL
- `frontend/lib/contracts/providerPresets.ts` is built around provider/source presets, not user intent templates

### Conclusion

The current system solves:

- "how should an operator configure a feed?"

more than it solves:

- "what does the user want intelligence about?"

This is the most important product-design mismatch in the repo.

## 4. What The Platform Actually Is Today

### Backend platform shape

The backend in `backend/` is a real application platform with:

- FastAPI app and middleware in `backend/main.py`
- auth and tenant scoping in `backend/auth/`
- API groups in `backend/api/v1/`
- repositories in `backend/repositories/`
- services in `backend/services/`
- signal acquisition in `backend/signals/`
- AI chat, embeddings, and synthesis in `backend/ai/` and `backend/agent/`
- ONNX/ML functionality in `backend/ml/`
- background jobs in `backend/jobs/`

### User-facing feature intention by area

Home:
- overview and next-best-action dashboard

Studio:
- create monitoring definitions for future signal acquisition

Marketplace:
- browse and subscribe to predefined signal templates

Signals:
- review ingested and scored intelligence items

Investigate:
- use AI chat to analyze signals, ask questions, and retrieve evidence

Library:
- read generated briefs and reports

Discovery:
- review new sources and entities discovered by the system

Domains:
- regional/geographic aggregation view over signals

Market Data:
- structured time-series extracted from signals

Alerts:
- anomaly and change-detection notifications

Settings:
- account, usage, sessions, API keys, and preferences

Pipeline:
- operator/admin control over ingestion and scheduler

## 5. Confirmed Platform-Level Blockers

### 5.1 Fresh environments are under-seeded

The app assumes data exists for:

- industries
- signal templates
- contracts
- signals
- briefs
- market data
- discovery entities/sources

But the deployed environment does not clearly run a bootstrap/init phase for this dataset.

Evidence:

- industries are read from DB in `backend/api/v1/industries.py`
- marketplace templates are read from DB in `backend/api/v1/marketplace.py`
- signals are read from DB in `backend/api/v1/signals.py`
- briefs are read from DB in `backend/api/v1/briefs.py`
- seed scripts exist only as manual scripts:
  - `backend/scripts/seed_nigeria_contracts.py`
  - `backend/scripts/seed_nigeria_briefs.py`

Impact:

- empty home
- empty marketplace
- empty signals
- empty domains
- investigate with little or no evidence
- library appearing empty or demo-dependent

### 5.2 The contract model is misaligned with end-user intent

Current contract UX requires the user to think like a data engineer:

- source type
- provider preset
- source URL
- extraction strategy

That is the wrong abstraction for most customers.

Impact:

- onboarding friction
- "hardcoded/generic" feeling
- users are asked to solve source discovery themselves
- product fails the "what job is it doing for the user?" test

### 5.3 Frontend truthfulness is weak

Several pages silently transform system failures into polished emptiness.

Evidence:

- `frontend/lib/hooks/useContractStudio.ts`
- `frontend/app/dashboard/home/page.tsx`
- `frontend/app/dashboard/marketplace/page.tsx`
- `frontend/lib/hooks/useDiscovery.ts`
- `frontend/lib/contexts/PricingContext.tsx`

Impact:

- users cannot tell the difference between:
  - no data yet
  - no access
  - no seed data
  - broken backend call
  - auth/token failure

### 5.4 New-user capability model is not coherent

Fresh signups land in a product that looks broad, but many meaningful actions are gated.

Evidence:

- `backend/api/v1/contracts.py` requires `custom_contracts` and credits
- `backend/api/v1/marketplace.py` requires `marketplace_subscribe`
- `backend/api/v1/briefs.py` requires `intelligence_briefs`
- `backend/api/v1/market_data.py` requires `market_data`
- `frontend/app/dashboard/home/page.tsx` has premium/starter branching

Impact:

- new signups feel broken, not intentionally tiered
- onboarding does not align with entitlement reality

### 5.5 Settings is only partially real

`frontend/lib/hooks/useSettings.ts` mixes:

- real APIs for:
  - profile
  - auth/me
  - sessions
  - API keys
  - credit balance/transactions

with local-only state for:

- payment card
- notifications
- integration toggles
- 2FA toggle

Impact:

- users can interact with controls that do not actually configure the platform

### 5.6 Setup documentation is stale relative to code

Evidence:

- `README.md` still references `frontend/app/api/auth/[auth0]/`
- auth route implementation has moved to explicit routes in `frontend/lib/auth0.ts`
- Resolved in the GCP migration pass: `.env.example` now documents Cloud SQL, Upstash Redis, and Cloud Storage variables instead of legacy object-storage names.

Impact:

- engineers can configure the system incorrectly by following the docs

## 6. Fake, Scaffolded, or Misleading Behaviors

### 6.1 Studio scaffolding

`frontend/lib/hooks/useContractStudio.ts` contains local generation logic for:

- feasibility data
- synthetic preview
- validation errors
- configured source docs
- simulation

This is not just UI polish. It changes the truth model of the page.

The frontend can appear to validate and simulate contracts even when backend-backed intelligence is absent.

### 6.2 Home fallback industries

`frontend/app/dashboard/home/page.tsx` contains `FALLBACK_INDUSTRIES` and starter-home logic that can mask missing taxonomy or failed requests.

### 6.3 Library demo residue

`frontend/lib/hooks/useLibrary.ts` still contains `SEED_BRIEFS`.

Even though live fetching is preferred, the presence of embedded demo content means the page architecture still assumes fallback content as a presentation strategy.

### 6.4 Discovery silent recommendation failure

`frontend/lib/hooks/useDiscovery.ts` uses silent or empty-list fallbacks in some code paths, especially around recommended sources and pending entities.

### 6.5 Pricing fallback can collapse product access state

`frontend/lib/contexts/PricingContext.tsx` loads pricing/features/credits via a single `Promise.all(...)`.

If one request fails, the page can degrade into a misleading fallback access picture.

## 7. Page-by-Page Audit

### 7.1 Home

Files:

- `frontend/app/dashboard/home/page.tsx`
- `frontend/lib/hooks/useCredits.ts`
- `frontend/lib/hooks/useFeatureGate.ts`

What it should do:

- orient new users
- show recent intelligence
- guide the next action

What it currently does:

- works as a polished empty-state shell
- depends on signals, industries, credits, and feature gates
- may look intentionally empty when the real problem is missing data or missing entitlements

Readiness:

- not production-ready as the first-run experience

### 7.2 Studio

Files:

- `frontend/app/dashboard/studio/page.tsx`
- `frontend/components/contracts/ContractStudio.tsx`
- `frontend/components/contracts/DefinitionPane.tsx`
- `frontend/lib/hooks/useContractStudio.ts`
- `backend/api/v1/contracts.py`

What it should do:

- accept user intent
- transform it into monitoring strategy
- make source selection invisible or mostly automated

What it currently does:

- asks for source type, preset, and URL
- simulates feasibility locally
- validates partly with local heuristics
- activates a source-centric contract

Readiness:

- not aligned with intended product use

### 7.3 Marketplace

Files:

- `frontend/app/dashboard/marketplace/page.tsx`
- `frontend/lib/api/marketplace.ts`
- `backend/api/v1/marketplace.py`
- `backend/models/signal_template.py`

What it should do:

- show a usable source/template catalog
- explain why each source matters
- allow entitlement-aware subscription

What it currently does:

- depends entirely on seeded `signal_templates`
- becomes empty if the catalog is absent
- subscription flow is real, but only if plan access and data exist

Readiness:

- not usable in a fresh environment without template bootstrap

### 7.4 Signals

Files:

- `frontend/app/dashboard/signals/page.tsx`
- `frontend/lib/hooks/useSignals.ts`
- `backend/api/v1/signals.py`

What it should do:

- show high-confidence, actionable intelligence
- support filtering, save/dismiss feedback, and detail drill-down

What it currently does:

- uses real APIs
- depends on ingestion and scoring having already happened
- empty state is real, not fake

Readiness:

- backend-integrated, but data-starved unless ingestion is already alive

### 7.5 Investigate

Files:

- `frontend/app/dashboard/investigate/page.tsx`
- `frontend/lib/hooks/useInvestigate.ts`
- `frontend/lib/api/chat.ts`
- `backend/api/v1/chat.py`
- `backend/services/chat_agent_service.py`
- `backend/agent/agent.py`

What it should do:

- let users ask questions about signals, entities, markets, and developments
- return evidence, citations, recommendations, and structured analysis

What it currently does:

- has a real session/message/SSE architecture
- relies on live agent/tooling/backend context
- has UI fallbacks when structured evidence is missing

Readiness:

- real feature foundation exists
- quality depends on signals, search, industries, Redis, OpenAI, and tool accuracy

### 7.6 Library

Files:

- `frontend/app/dashboard/library/page.tsx`
- `frontend/lib/hooks/useLibrary.ts`
- `backend/api/v1/briefs.py`
- `backend/briefs/generator.py`

What it should do:

- store generated and refreshed briefs
- present credible, current intelligence artifacts

What it currently does:

- has real list/detail/generation endpoints
- still carries demo residue in the frontend
- brief generation is real but gated and credit-consuming

Readiness:

- backend viable, UX still mixed with demo-era architecture

### 7.7 Discovery

Files:

- `frontend/app/dashboard/discovery/page.tsx`
- `frontend/lib/hooks/useDiscovery.ts`
- `backend/api/v1/discovered_sources.py`
- `backend/api/v1/entities.py`
- `backend/services/source_discovery.py`

What it should do:

- show sources the platform discovered from real ingestion
- let admins review/activate them
- let entity review happen in one place

What it currently does:

- is real and promising
- depends on refinement/source extraction/entity discovery already producing records
- can show "Loading industries..." indefinitely when the taxonomy is empty

Readiness:

- real subsystem, but not self-bootstrapping

### 7.8 Domains

Files:

- `frontend/app/dashboard/domains/page.tsx`
- `frontend/lib/hooks/useDomainMap.ts`
- `backend/api/v1/signals.py`

What it should do:

- provide geographic/regional intelligence aggregation

What it currently does:

- depends on `/signals/regions`
- becomes inert if there are no region aggregates

Readiness:

- real integration, but downstream of signal availability

### 7.9 Market Data

Files:

- `frontend/app/dashboard/market-data/page.tsx`
- `frontend/lib/hooks/useMarketData.ts`
- `backend/api/v1/market_data.py`

What it should do:

- expose structured market metrics extracted from signals

What it currently does:

- uses real endpoints
- is gated behind `market_data`
- requires extracted `market_data_points`

Readiness:

- legitimate advanced feature, not a fresh-user core path

### 7.10 Alerts

Files:

- `frontend/app/dashboard/alerts/page.tsx`
- `frontend/lib/hooks/useAlerts.ts`
- `backend/api/v1/alerts.py`

What it should do:

- notify users of meaningful changes and anomalies

What it currently does:

- uses real APIs
- empty if no alerts exist

Readiness:

- real, but only useful after upstream analytics are generating alerts

### 7.11 Settings

Files:

- `frontend/app/dashboard/settings/page.tsx`
- `frontend/lib/hooks/useSettings.ts`

What it should do:

- let users actually manage account/security/preferences/billing

What it currently does:

- mixes real and local-only sections

Readiness:

- partially production-ready

### 7.12 Pipeline

Files:

- `frontend/app/dashboard/pipeline/page.tsx`
- `backend/api/v1/pipeline.py`

What it should do:

- admin/operator operations only

What it currently does:

- uses real scheduler and health APIs
- suppresses some permission failures with vague UI behavior

Readiness:

- not for end users; acceptable as an internal tool once auth messaging is improved

## 8. Buttons and Actions Audit

### Real buttons today

- Signals save/dismiss feedback
- Investigate send message
- Discovery activate/dismiss
- Contracts activate/deactivate/delete/fetch
- Alerts acknowledge
- API key create/rotate/revoke
- session revoke

### Problematic buttons today

- Studio `Run Validation`
  - partly local
- Studio `Run Simulation`
  - local
- Settings notification/integration/payment controls
  - mostly local-only
- Home and onboarding actions
  - may route correctly but often land on under-seeded or gated experiences

## 9. Endpoint Integration Audit

### Strongly integrated endpoint groups

- `auth`
- `users`
- `signals`
- `chat`
- `alerts`
- `contracts`
- `discovered_sources`
- `market_data`
- `briefs`

### Real but environment/data/gate dependent

- `marketplace`
- `pricing`
- `credits`
- `situation_room`
- `search`
- `recommendations`
- `entities`
- `causal`
- `influence`
- `regulatory`
- `ml`

### Important integration truth

The biggest integration weakness is not missing routes. The routes mostly exist.

The biggest weakness is:

- user-facing flows are not aligned to the data/seed/gating prerequisites of those routes

## 10. AI and Intelligence Layer Audit

### What is real

- OpenAI-powered agent chat
- synthesis service
- embeddings and search
- ONNX scoring infrastructure
- source discovery
- refinement pipeline
- recommendation and intelligence services

### What is not yet productized correctly

- AI outputs are not consistently surfaced as truthful, dependable user workflows
- empty-state and fallback UX makes the intelligence layer feel fake even when the backend is real
- the contract system exposes infrastructure concepts instead of intent capture

### Product implication

The AI layer should be downstream of user intent and platform-managed acquisition.

Instead, the current product often asks the user to manually define acquisition mechanics before AI can help them.

## 11. Config, Setup, and Deployment Audit

### Confirmed setup inconsistencies

- `README.md` references outdated auth route structure
- Resolved in the GCP migration pass: `.env.example` now uses `GOOGLE_CLOUD_PROJECT`, `GCS_MODEL_BUCKET`, and `GCS_DOCUMENT_BUCKET`.
- the repo assumes a high number of secrets and provider credentials with little first-run validation guidance beyond environment presence
- deployment stands up infrastructure, but not a trustworthy product bootstrap

### Good things already in place

- health endpoints
- startup dependency checks
- infrastructure-as-code
- smoke-test script
- release-readiness tests
- environment-based frontend/backend URL wiring

### Missing production setup layer

There is no obvious single "initialize environment for usable product" step that:

- runs migrations
- seeds industries
- seeds marketplace templates
- seeds optional staging demo data
- validates provider credentials
- validates required feature/pricing defaults

## 12. Architectural Diagnosis

Cogent currently has three different product models mixed together:

1. an operator-configured source ingestion platform
2. a user-facing intelligence SaaS
3. a staging/demo shell designed to stay visually stable when data is missing

Those three models are pulling against each other.

For real-world readiness, Cogent needs one dominant model:

- an intent-first intelligence SaaS where the system manages source complexity on behalf of the user

## 13. Required Product Reframe

### Contract creation should become intent-first

Instead of:

- source type
- provider preset
- source URL
- extraction config

The user should provide:

- what to monitor
- geography
- sector/domain
- time sensitivity
- desired output format
- optional constraints

The platform should then:

- map intent to one or more provider templates
- create underlying source contracts automatically
- let advanced users inspect or override them later

### Marketplace should become "coverage packs"

Not just templates, but:

- what intelligence coverage is unlocked
- which sources are behind it
- why it matters
- what outputs it enables

### Home should distinguish states explicitly

It must clearly say whether the workspace is:

- new and unconfigured
- seeded but waiting for ingestion
- gated by plan
- missing required integrations
- experiencing backend issues

## 14. Engineering Roadmap

### Phase 1: Truthfulness and bootstrap

- remove silent empty-state masking
- add explicit status messaging
- create environment bootstrap/init job
- seed industries and marketplace templates automatically
- add optional staging demo dataset
- fix stale docs and env examples

### Phase 2: Intent-first contract system

- add `monitoring_intent` model/schema layer
- let users describe monitoring goals without source plumbing
- automatically derive one or more underlying source contracts
- hide advanced source config behind expert mode

### Phase 3: Fresh-user journey

- define what Explorer users can actually do immediately
- align onboarding, pages, and buttons to that reality
- avoid routing users into dead/gated views without explanation

### Phase 4: Real settings and trust polish

- persist notifications/integrations/preferences or remove them
- make billing controls truthful
- fix sidebar interaction and page-level broken-feeling behavior

### Phase 5: Advanced intelligence hardening

- validate briefs, market data, causal, influence, regulatory, and ML pages after core onboarding works
- add stronger smoke tests across these flows

## 15. Immediate Engineering Tasks

1. Add a post-deploy bootstrap command or job.
2. Replace Studio source-config UX with intent capture.
3. Split "empty because new" from "empty because broken" everywhere.
4. Remove or label scaffolded/local-only behavior.
5. Make new-user entitlements intentional and visible.
6. Bring docs and env examples back in sync with code.

## 16. Bottom Line

Cogent has a real backend platform.

What it does not yet have is a trustworthy, intent-first, first-run user product.

The engineering goal should not be:

- "make the fancy UI feel less empty"

It should be:

- "make the platform honest, bootstrapped, and centered on user monitoring intent rather than source configuration"

That is the path from staging demo behavior to real customer-ready usage.
# Implementation Progress — 2026-04-20

The following readiness fixes have now been implemented:

- Added automatic catalog bootstrap on backend startup for core industries and curated marketplace templates via [backend/bootstrap/catalog.py](/c:/Users/Alex%20Marco/Documents/Cogent/backend/bootstrap/catalog.py).
- Updated contract creation and marketplace subscription flows to support managed-source defaults and to enqueue an initial fetch immediately after activation.
- Relaxed contract schema requirements so managed-source contracts do not force users to provide a source URL unless they are using a webhook or a generic override.
- Shifted Studio toward intent-first behavior:
  - managed source plan is now the default framing in the definition pane
  - source overrides are moved behind an advanced section
  - validation no longer blocks on source URL for managed-source contracts
  - evidence/source tray now reflects `planned`, `matched`, and `selected` states instead of synthetic ingestion states
- Improved pricing context resilience so partial failures do not collapse the entire entitlement model.
- Made Home and Marketplace report missing bootstrap/catalog data explicitly instead of silently falling back to empty-but-polished states.
- Added explicit discovery error reporting for recommended sources instead of silent failure.
- Hardened the navigation rail expansion behavior with focus/pointer expansion support.

These changes improve truthfulness and first-run behavior, but they do not complete the full product-readiness roadmap. Remaining work still includes deeper fixes across settings persistence, richer onboarding, more honest admin gating, live data population for all empty states, and additional route-by-route product integration.

## 17. Additional Implementation Progress — 2026-04-20

The following follow-up fixes have also been implemented after the initial readiness pass:

- Removed the remaining runtime demo-state branch from the Library hook so the page no longer claims it is showing fallback demo content when the live briefs service fails.
- Improved Library brief detail handling so failed full-detail refreshes keep the current brief open while showing an honest warning instead of silently masking the issue.
- Rebuilt Preferences as a truthful device-level settings surface:
  - removed the fake "System" theme option
  - removed the non-functional density control
  - persisted language and timezone locally for the current browser
  - clarified in copy that these are device-level preferences, not workspace-wide localization
- Removed dead settings runtime state that was not actually wired to the product:
  - fake integrations state
  - fake local notification-preference state
  - fake billing-card/invoice state from the hook used by the current settings page
  - unused 2FA toggle wiring in the security section
- Improved Discovery activation UX so missing industry bootstrap is surfaced explicitly instead of looking like an endless "Loading industries..." state.
- Improved Signals empty-state truthfulness so new workspaces are told there are no signals yet and are pointed toward creating contracts or activating sources, rather than being told their filters are the problem.

These changes reduce the gap between what the product says is happening and what the backend is actually capable of doing in the current deployment.

## 18. Additional Implementation Progress â€” 2026-04-20 (Studio Trust Pass)

The Studio workflow has been tightened further so it reads like a real operator workflow instead of a speculative simulation surface:

- Removed the synthetic feasibility chart from the active Studio experience. The review step now focuses on:
  - validation results
  - managed-source evidence
  - planned output rows
  - estimated monthly credits
- Renamed the user-facing Studio lifecycle language from "Simulate" to "Review" while preserving the internal step wiring.
- Updated Studio copy to stay intent-first:
  - "Schema Fields" is now framed as "Return fields"
  - "Delivery Parameters" is now framed as "Monitoring settings"
  - the natural-language prompt now asks what the user wants monitored instead of asking for data wiring
- Removed the misleading post-activation preview state that was still showing planning rows as though they were live data. Once a contract is active, Studio now explains what happens next and directs the user toward real fetch and Signals workflows.
- Hardened contract list messaging so managed-source contracts no longer fall back to raw source URLs or blank descriptions when live data has not yet landed.
- Added a clear note in Library code that the remaining large fixture block is legacy migration residue, not an active runtime data source.

These changes make Studio more truthful for real users: review aids remain available, but the product now draws a clearer line between planning artifacts and live intelligence.

## 19. Additional Implementation Progress — 2026-04-21 (Settings And Signal Feedback Pass)

Another follow-up pass was completed to remove remaining overpromises in settings/legal surfaces and to make signal dossier actions visibly trustworthy:

- Tightened the Data & Privacy section so it now reflects the actual backend compliance flows:
  - clear history now describes the real scope of deletion: investigation sessions and their associated chat messages
  - user-data export now lists the actual exported payload categories returned by the backend
  - account deletion now describes the real deletion/anonymisation scope instead of implying unrelated workspace objects are removed
  - success messages from privacy actions are now surfaced directly in the UI instead of disappearing into the network layer
- Removed legal/support copy that implied unsupported operational guarantees:
  - the support card no longer promises a fixed four-hour response SLA
  - the legal footer no longer hardcodes a static version/build banner that can drift from reality after deployment
- Improved Signal Drawer trust and usability:
  - copying a signal link now shows a success or failure message instead of silently swallowing clipboard errors
  - social share actions now report when a browser popup is blocked
  - markdown export now confirms that the brief has been downloaded
  - PDF, Word, and PowerPoint export failures now surface a user-visible error instead of only logging to the console

These changes do not add new product capabilities by themselves, but they materially improve production-readiness by ensuring that sensitive settings actions and live intelligence export workflows behave transparently for real users.

## 20. Additional Implementation Progress — 2026-04-21 (Live Intelligence Surfaces Pass)

Another targeted integration pass was completed across alerts, domains, investigate, and market-data consistency:

- Improved alert handling truthfulness and recoverability:
  - alert list and summary hooks now use the shared friendly error formatter instead of leaking raw transport messages
  - alert acknowledgements now surface user-visible action failures
  - acknowledgement buttons now show in-progress state so the UI no longer feels unresponsive during writes
  - the Alerts empty state now distinguishes between "no active anomalies yet" and "alert coverage has not started producing events yet"
- Improved signal and dossier error handling:
  - signal list, signal drawer open, save, dismiss, and pagination errors now use clearer user-facing messaging
- Made the Domains page more honest for first-run workspaces:
  - the region sidebar can now explain the difference between "there are no signals yet" and "there are signals, but they have no geographic metadata"
  - the domain-map hook now explicitly treats endpoint failures as service errors instead of implying a harmless empty result
- Tightened Investigate fallback messaging:
  - when industry filters fail to load, the page now explicitly tells the user they can still investigate across all monitored industries
- Fixed backend feature-gating consistency:
  - the `/api/v1/market-data/metrics` endpoint now follows the same `market_data` feature gate as the rest of the market-data surface

These changes continue the same theme as the previous waves: reducing silent failure, removing misleading emptiness, and ensuring that live intelligence surfaces behave in ways real users can understand and trust.

## 21. Additional Implementation Progress — 2026-04-21 (First-Run Library And Home Finalization Pass)

Another cleanup wave was completed to tighten first-run guidance and align the remaining frontend brief contracts with the backend:

- Fixed stale frontend brief refresh types so they now match the backend schemas for both single-brief refresh and batch refresh responses.
- Improved the Library first-run experience:
  - added an explicit "Refresh library" action in the page header
  - replaced the passive "No briefs yet" message with intent-first guidance that explains briefs appear after live signals are synthesized
  - added direct next-step actions for creating a contract, browsing managed sources, and opening the Signals workspace
- Improved Home feed truthfulness:
  - the live feed now accepts explicit empty-state messaging from the page
  - Home now distinguishes between "no signals yet" and "no recent live events"
  - starter empty-state copy no longer uses rhetorical filler and instead explains the real next step that unlocks value
  - starter Home now passes the effective last-updated timestamp to the live feed, not just the premium dashboard timestamp

These changes close another important gap in the new-user journey: users are now guided toward the real work needed to generate intelligence instead of being left in polished but passive empty states.

## 22. Additional Implementation Progress — 2026-04-21 (Signals, Investigate, And Market Data Guidance Pass)

One more end-to-end usability pass was completed across the core live-work surfaces:

- Improved the Signals workspace first-run state:
  - added a dedicated guidance card when no signals have been ingested yet
  - linked the empty state directly to Studio and Marketplace so users can create monitoring coverage instead of staring at an empty table
- Improved Investigate onboarding clarity:
  - when no active thread exists yet, the page now explains that Investigate is strongest once the workspace has real monitored signals
  - added direct navigation to Signals, Studio, and Marketplace so the investigation flow stays tied to real data rather than abstract prompting
- Improved Market Data first-run guidance:
  - the empty metrics state now explains that tracked indicators only appear after the relevant sources are activated and ingested
  - added direct calls to action back into Marketplace and Signals

This pass finishes another important part of the product-readiness effort: the core intelligence workspaces now tell users how to generate real value instead of leaving them in passive empty containers.

## 23. Additional Implementation Progress — 2026-04-21 (Acquisition Readiness And Pipeline Visibility Pass)

The acquisition stack received another hardening pass focused on proving that data collection is truly operational:

- Hardened the signal acquisition service for managed-source contracts:
  - provider presets are now resolved at fetch time before the worker calls the underlying fetcher
  - contracts that cannot resolve to a real source endpoint now fail with an explicit operational error instead of drifting into unclear fetch failures
- Improved pipeline observability:
  - `/api/v1/pipeline/status` now includes queue depth, worker heartbeat information, and provider-readiness flags
  - pipeline status now reports whether the core provider credentials required for managed acquisition are actually configured
- Improved the admin pipeline page:
  - shows whether any RQ workers are online
  - shows per-queue backlog/failure/scheduled counts
  - shows worker heartbeat and queue assignment details
  - makes missing workers or missing provider credentials explicit instead of forcing operators to infer them from empty downstream surfaces

These changes do not replace a full live ingestion test against every provider, but they materially improve real-world operability by making acquisition readiness visible and by reducing failure cases where contracts looked valid while still lacking a resolvable fetch target.

## 24. Additional Implementation Progress — 2026-04-21 (Acquisition Smoke-Test Verification)

After the readiness changes above, the generic acquisition fetchers were smoke-tested against public live endpoints from the project virtualenv:

- RSS fetcher: successfully parsed a live BBC World RSS feed
- Scraper fetcher: successfully extracted live items from Hacker News using CSS selectors
- API fetcher: successfully parsed a public JSON API payload into normalized fetch results

This does **not** prove that every paid/provider-specific source is ready in every environment by itself. NewsAPI, NGX market data, X, OpenAI, and any premium upstream integrations still depend on valid production credentials and network reachability. However, it does confirm that:

- the generic fetcher stack is operational
- scraping is functioning with live public HTML
- feed parsing is functioning with live public RSS
- API normalization is functioning with live public JSON

Combined with the new pipeline readiness visibility, these checks materially improve confidence that data acquisition is genuinely wired rather than only represented in the UI.

## 25. Additional Implementation Progress — 2026-04-21 (Operational Validation Toolkit Pass)

To move the readiness work from code hardening into repeatable operational proof, a dedicated validation layer was added for engineers and operators:

- Added a runnable staging validation script:
  - `scripts/validate_intelligence_pipeline.py` checks backend health, scheduler status, worker availability, queue backlog, provider readiness, contract visibility, signal feed visibility, and brief availability
  - the script can optionally trigger a real manual fetch for an active contract and poll the contract signal endpoint to detect live growth
  - failures are separated from warnings so fresh-workspace emptiness does not get confused with true operational outages
- Added an engineer runbook:
  - `docs/engineers/staging-intelligence-validation-checklist.md` documents the intended end-to-end validation flow from contract/source activation through workers, signals, briefs, and frontend verification
  - the checklist also provides a triage order for the most common staging failure modes: workers offline, missing provider secrets, growing queues, or signals landing without appearing in product surfaces

This pass does not add new user-facing features directly, but it closes an important production-readiness gap: engineers now have a concrete, repeatable way to prove that live acquisition and downstream intelligence generation are functioning end to end in staging rather than relying on UI inference alone.
