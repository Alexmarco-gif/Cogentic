# Frontend Improvements to Reach Senior-Level Design

This plan is grounded in the current implementation (not docs) and focuses on architecture, DX, product quality, and scalability.

## Current State (Implementation Signals)

- The frontend shell is minimal and mostly auth-test oriented (`app/page.tsx`, `app/auth-test/page.tsx`).
- Core monetization UX components exist (`FeatureGate`, `CreditDisplay`, `UpgradePrompt`) but rely on hooks/contexts under `@/lib/...` that are not present in this checkout.
- Auth middleware currently protects only `/api/protected/*` and `/dashboard/*`.
- The backend already supports rich multi-tenant features (signals, chat SSE, pricing/gating), so frontend should be elevated to match that capability.

## 1) Establish a Production Frontend Architecture

### 1.1 Route groups + app shell strategy

Adopt route groups to separate concerns and avoid global coupling:

- `(marketing)` public pages
- `(auth)` login/callback/error handling
- `(app)` authenticated product experience
- `(admin)` role-restricted operations

Add shared shell primitives:

- `AppShell` (nav, breadcrumb, responsive layout)
- `ErrorBoundary` per route segment
- `Loading` skeletons per segment

### 1.2 Typed service layer with strict boundaries

Create a single API client layer under `src/lib/api` with:

- runtime validation (`zod`) for responses
- typed `Result<T, E>` style error handling
- auth token/session propagation logic centralized
- request cancellation and timeout defaults

Avoid ad-hoc `fetch` calls inside components; all network calls should flow through service modules.

### 1.3 Server-first data fetching + targeted client interactivity

Use App Router as intended:

- server components for initial data fetch and SEO
- client components only for interaction-heavy islands (filters, charts, chat stream)
- colocated `actions.ts` for form mutations where applicable

## 2) Close Gaps in Existing Implementation

### 2.1 Rebuild missing `lib` foundations

Current components import:

- `@/lib/hooks/useFeatureGate`
- `@/lib/hooks/useCredits`
- `@/lib/contexts/PricingContext`
- `@/lib/auth0` and `@/lib/dev-gate`

Senior-level baseline is to implement these with:

- strict types shared from API schemas
- stable loading/error states
- retry/backoff for transient failures
- no silent nulls in critical monetization UX

### 2.2 Make gating cohesive across backend + frontend

Backend already returns structured feature/tier denial payloads. Frontend should:

- parse these errors into a unified `AccessDeniedModel`
- render a consistent upgrade UX everywhere
- log denied-intent analytics (which feature was attempted)

### 2.3 Introduce a design system layer

Extract and standardize primitives:

- `Button`, `Badge`, `Card`, `Alert`, `EmptyState`, `Skeleton`, `Modal`
- design tokens via CSS variables (`color`, `radius`, `spacing`, `elevation`)
- variant props with strict typing

This prevents one-off Tailwind strings and ensures visual consistency.

## 3) Data UX and Information Architecture

### 3.1 Build role-aware app navigation

Given multi-tenant + role model in backend, nav should be dynamic by:

- role (admin/manager/member)
- tier feature availability
- organization context

### 3.2 Improve signals/discovery workflows

For signals pages:

- faceted filters (type, confidence, entity, date)
- saved views/search presets
- URL-synced state for shareable views
- optimistic pagination interactions

### 3.3 Chat product quality (SSE)

The backend streams typed SSE events; frontend should model these as a state machine:

- `idle -> thinking -> tool_calling -> streaming -> done/error`
- stream chunk rendering with reconnect support
- citation panel + source hover previews
- transcript virtualization for long sessions

## 4) Quality, Testing, and Observability (Senior Standards)

### 4.1 Testing pyramid

- Unit: utility functions, hooks, formatting, guards
- Component: key states (loading/error/access denied)
- E2E: auth flow, gating flow, chat stream, upgrade conversion path

Suggested stack:

- Vitest + Testing Library
- Playwright for E2E

### 4.2 Frontend observability

Add:

- web vitals collection
- client error boundary reporting (Sentry)
- user journey analytics for funnel steps (login, trial, upgrade)

### 4.3 Error handling contract

Centralize error mapping:

- auth errors
- network/timeout errors
- backend validation errors
- gating/permission errors

Each error class should map to deterministic UX copy and recovery actions.

## 5) Performance and Accessibility

### 5.1 Performance

- streaming-friendly suspense boundaries
- dynamic import heavy client widgets (charts, editors)
- image optimization and icon strategy
- cache strategy per route: `force-cache`/`no-store` intentionality

### 5.2 Accessibility

- keyboard-first interactions for nav/modals/chat
- proper aria labels and live regions for SSE updates
- color contrast and focus indicators verified in CI

## 6) Security and Enterprise Readiness

- strict CSP and security headers in Next config/middleware
- robust session expiry UX + token refresh edge cases
- org-switching safeguards to avoid cross-tenant confusion
- audit trail surfacing for sensitive admin actions

## 7) Recommended 90-Day Execution Plan

### Phase 1 (Weeks 1-3): Foundation

- Recreate missing `lib` modules (hooks/contexts/auth wrappers)
- Introduce typed API client + shared schemas
- Build design-system primitives and app shell

### Phase 2 (Weeks 4-7): Product Surface

- Implement real dashboard and signals browsing experience
- Implement cohesive feature gating + upgrade journeys
- Implement robust chat SSE UI with citations

### Phase 3 (Weeks 8-12): Hardening

- Add full test suite and CI quality gates
- Add observability + analytics instrumentation
- Accessibility and performance budget enforcement

## 8) Definition of Done for “Senior-Level Frontend”

A frontend can be considered senior-level in this repo when it demonstrates:

1. **Architectural clarity** (server/client boundaries, typed API contracts)
2. **Consistency** (design system + error model + loading patterns)
3. **Reliability** (tests, observability, graceful degradation)
4. **Product alignment** (fully expressing backend capabilities: signals, chat, gating, pricing)
5. **Operational maturity** (performance, accessibility, security defaults)

