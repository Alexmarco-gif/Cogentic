# Cogent Full-Platform Migration Blueprint: Azure to GCP + Upstash

Date: 2026-04-25

## 1. Decision Record

We are migrating the existing Cogent platform from Azure infrastructure to GCP while preserving the current product scope and the existing Auth0-based authentication and authorization model.

This is not a reduced MVP plan. The target is the same platform shape Cogent is already building:

- Next.js frontend
- FastAPI backend
- RQ-style background worker path or a compatible replacement
- PostgreSQL with pgvector
- Redis-backed cache, rate limiting, job state, chat context, and operational metadata
- Auth0 login, Auth0 access tokens, Auth0 M2M tokens, and existing org/role authorization
- signal acquisition, refinement, briefs, intelligence surfaces, payments, notifications, observability, and admin pipeline visibility

Auth and authorization are not being rebuilt in this plan. The current Auth0 design remains the identity layer.

## 2. Current Platform Inventory

The current Azure deployment is defined mainly in:

- `infrastructure/main.bicep`
- `infrastructure/modules/container-app.bicep`
- `infrastructure/modules/postgres.bicep`
- `infrastructure/modules/redis.bicep`
- `infrastructure/modules/keyvault.bicep`
- `infrastructure/modules/container-registry.bicep`
- `.github/workflows/deploy.yml`

Runtime containers:

- Backend API: `Dockerfile`
- Worker: `Dockerfile.worker`
- Frontend: `frontend/Dockerfile`
- Local staging topology: `docker-compose.staging.yml`

Core backend runtime dependencies:

- FastAPI app: `backend/main.py`
- Settings: `backend/config.py`
- Database: `backend/database.py`
- Redis clients: `backend/redis_client.py`
- Job queue: `backend/job_queue.py`
- Worker entrypoint: `worker.py`
- Scheduler: `backend/signals/scheduler.py`
- Job handlers: `backend/job_handlers.py`
- Acquisition jobs: `backend/jobs/acquisition_job.py`

Auth and authorization dependencies:

- Auth0 frontend SDK wrapper: `frontend/lib/auth0.ts`
- Frontend Auth0 provider: `frontend/components/ui/Auth0Provider.tsx`
- Access token route: `frontend/app/api/auth/access-token/route.ts`
- Backend JWT middleware: `backend/auth/middleware.py`
- Auth dependencies and context: `backend/auth/dependencies.py`
- Auth schemas: `backend/auth/schemas.py`
- Auth0 JWKS: `backend/auth/jwks.py`
- Auth guards and roles: `backend/auth/guards.py`
- Auth0 backend webhook: `backend/webhooks/auth0.py`
- Auth0 frontend webhook proxy: `frontend/app/api/webhooks/auth0/route.ts`

Data and intelligence dependencies:

- PostgreSQL models: `backend/models/*`
- pgvector usage: `backend/models/signal.py`, `backend/models/entity.py`, `backend/models/regulatory_knowledge.py`
- signal fetchers: `backend/signals/fetchers/*`
- signal processors: `backend/signals/processors/*`
- AI services: `backend/ai/*`
- brief generation: `backend/briefs/*`
- chat and investigation: `backend/agent/*`, `backend/services/chat_agent_service.py`
- ML artifacts: `backend/ml/models/*`
- document processing and storage cleanup: `backend/job_handlers.py`

External services currently kept:

- Auth0
- OpenAI
- Paystack
- Resend
- SerpApi
- NewsAPI
- NGX Pulse
- X API
- Sentry
- PostHog
- Better Stack / Logtail
- Neo4j, if enabled

## 3. Target Architecture

### Azure to GCP Mapping

| Current Azure resource | GCP / Upstash target | Notes |
| --- | --- | --- |
| Azure Container Apps backend | Cloud Run service: `cogent-backend` | Keep FastAPI container and health checks. |
| Azure Container Apps frontend | Cloud Run service: `cogent-frontend` | Keep Next.js standalone container. |
| Azure Container Apps worker | Cloud Run worker service or Cloud Run Job | See worker strategy below. |
| Azure Container Apps migration job | Cloud Run Job: `cogent-migrate` | Runs `alembic upgrade head`. |
| Azure PostgreSQL Flexible Server | Cloud SQL for PostgreSQL | Must enable pgvector support. |
| Azure Cache for Redis | Upstash Redis | Use `rediss://` Redis-compatible endpoint. |
| Azure Key Vault | Secret Manager | Secrets injected into Cloud Run env. |
| Azure Container Registry | Artifact Registry | Store backend, worker, frontend images. |
| Azure Log Analytics | Cloud Logging / Cloud Monitoring | Keep Sentry/PostHog/Logtail if wanted. |
| Azure managed identity | GCP service accounts + IAM | One service account per runtime is preferred. |
| Azure Blob model/document storage | Cloud Storage | Replace Azure Blob-specific cleanup code. |
| Azure Bicep | Terraform or Pulumi | Terraform recommended for portable GCP infra. |

### Runtime Services

Recommended Cloud Run services:

- `cogent-frontend`
- `cogent-backend`
- `cogent-worker`

Recommended Cloud Run jobs:

- `cogent-migrate`
- `cogent-backfill`
- `cogent-model-training`
- `cogent-scheduled-dispatch`, if scheduler is moved out of backend process

Recommended managed resources:

- Cloud SQL for PostgreSQL with pgvector
- Artifact Registry Docker repository
- Secret Manager
- Cloud Storage bucket for ML artifacts and uploaded documents
- Upstash Redis database
- Cloud Scheduler jobs for periodic dispatch
- Cloud Monitoring uptime checks and alerts

## 4. Auth0 Stays In Place

We are not replacing Auth0.

The GCP version must preserve:

- `AUTH0_DOMAIN`
- `AUTH0_AUDIENCE`
- `AUTH0_CLIENT_ID`
- `AUTH0_CLIENT_SECRET`
- `AUTH0_SECRET`
- `AUTH0_M2M_CLIENT_ID`
- `AUTH0_M2M_CLIENT_SECRET`
- `AUTH0_WEBHOOK_SECRET`
- Auth0 custom claims for `org_id`, `roles`, `plan`, and super-admin state
- backend JWT verification via Auth0 JWKS
- frontend access token route
- Auth0 log stream webhook sync, unless we later retire it deliberately

Required Auth0 dashboard changes during cutover:

- Add the GCP frontend URL to allowed callback URLs.
- Add the GCP frontend URL to allowed logout URLs.
- Add the GCP frontend URL to allowed web origins.
- Ensure the frontend Auth0 app is authorized to request the existing API audience.
- Add the GCP webhook URL for Auth0 log streams if webhooks remain active.

No backend authorization rewrite is planned. Existing role and permission behavior stays in:

- `backend/auth/dependencies.py`
- `backend/auth/guards.py`
- `backend/auth/permissions.py`
- `backend/auth/enums.py`
- `backend/models/org_user.py`

## 5. Database Plan

Primary store:

- Cloud SQL for PostgreSQL
- PostgreSQL version should support pgvector; Cloud SQL documents pgvector support for PostgreSQL versions 11 and later, with newer pgvector versions available on PostgreSQL 13 and later.
- pgvector extension must be enabled during provisioning or migration.

Data to migrate:

- organizations
- users
- org_users
- user_sessions
- signal contracts
- marketplace templates
- signals
- signal scores
- entities and relationships
- intelligence briefs
- chat sessions and messages
- documents
- credits and billing state
- audit logs
- feature gates and pricing config
- ML run metadata

Migration strategy:

1. Freeze Azure writes during the final cutover window.
2. Dump Azure PostgreSQL with custom format.
3. Restore into Cloud SQL.
4. Run Alembic migrations against Cloud SQL.
5. Validate pgvector extension and vector columns.
6. Run bootstrap catalog idempotently.
7. Run pipeline validator against the GCP backend.

Important code references:

- `alembic.ini`
- `alembic/`
- `backend/database.py`
- `backend/bootstrap/catalog.py`
- `scripts/validate_intelligence_pipeline.py`

## 6. Redis and Upstash Plan

Use Upstash Redis for the current Redis responsibilities:

- rate limiting: `backend/auth/rate_limit.py`
- async and sync Redis clients: `backend/redis_client.py`
- RQ queues, if initially preserved: `backend/job_queue.py`, `worker.py`
- AI and embedding cache: `backend/ai/embedding_cache.py`, `backend/ai/embeddings.py`, `backend/ai/synthesis.py`
- chat context: `backend/agent/context.py`
- web search cache: `backend/services/web_search/cache.py`
- source health and pipeline state
- webhook idempotency

Upstash supports Redis-compatible commands and TLS endpoints, so the lowest-risk first migration is:

```text
REDIS_URL=rediss://default:<token>@<host>:<port>
```

Important risk:

- RQ relies on Redis behavior such as blocking operations, worker heartbeats, registries, and long-lived worker connections.
- Upstash supports a broad Redis command surface, but we must test RQ specifically under staging load before calling the worker path production-ready.

Recommended worker strategy:

1. Phase 1 keeps RQ and the existing worker container to minimize code churn.
2. Phase 2 evaluates replacing RQ with Cloud Tasks for durable HTTP job dispatch.
3. Phase 3 moves scheduler-owned periodic jobs to Cloud Scheduler and Cloud Run Jobs where appropriate.

This preserves the platform while reducing migration risk.

## 7. Worker and Scheduler Plan

Current behavior:

- Backend starts app lifespan logic in `backend/main.py`.
- `backend/signals/scheduler.py` uses APScheduler.
- Scheduler dispatches RQ jobs via `backend/job_queue.py`.
- `worker.py` consumes high/default/low queues.

GCP target, phase 1:

- Run `cogent-backend` as a Cloud Run service.
- Run `cogent-worker` as a Cloud Run service with minimum instances set to at least 1 for staging/production ingestion.
- Keep `worker.py` unchanged initially.
- Set `REDIS_URL` to Upstash.
- Keep the scheduler behavior initially, but ensure only one scheduler instance is active.

GCP target, phase 2:

- Move periodic dispatch from in-process APScheduler to Cloud Scheduler.
- Create HTTP dispatch endpoints or Cloud Run Jobs for:
  - tier fetch dispatch
  - contract health checks
  - refinement catch-up
  - brief refresh
  - recommendation generation
  - source auto-activation
  - weekly model training

Why phase 2 matters:

- Cloud Run can scale horizontally.
- In-process schedulers can duplicate work if more than one backend instance runs.
- Cloud Scheduler gives a single external clock.

## 8. Storage Plan

Current storage references include Azure Blob settings:

- `AZURE_BLOB_CONNECTION_STRING`
- `AZURE_BLOB_MODEL_CONTAINER`
- document cleanup logic in `backend/job_handlers.py`
- ML artifact comments in `backend/ml/inference.py` and `backend/ml/models/__init__.py`

Target:

- Cloud Storage bucket for ML model artifacts
- Cloud Storage bucket or prefix for user-uploaded documents
- signed URLs or service-account mediated access for private files

Code changes required:

- Add `gcs_bucket_models` and `gcs_bucket_documents` settings.
- Replace Azure Blob parsing/deletion in `backend/job_handlers.py`.
- Replace Azure Blob model loading path in ML inference code if production model loading uses object storage.
- Keep local filesystem behavior for development.

Do not remove document storage behavior. Replace the backing provider.

## 9. Secrets and Config Plan

Move secrets from Key Vault references to Secret Manager.

Required secrets:

- `DATABASE_URL`
- `DATABASE_READ_URL`, if used
- `REDIS_URL`
- `SECRET_KEY`
- `AUTH0_DOMAIN`
- `AUTH0_AUDIENCE`
- `AUTH0_M2M_CLIENT_ID`
- `AUTH0_M2M_CLIENT_SECRET`
- `AUTH0_WEBHOOK_SECRET`
- `AUTH0_SECRET`
- `AUTH0_CLIENT_ID`
- `AUTH0_CLIENT_SECRET`
- `OPENAI_API_KEY`
- `NEWSAPI_API_KEY`
- `NGX_MARKET_DATA_API_KEY`
- `NGX_MARKET_DATA_BASE_URL`
- `X_BEARER_TOKEN`
- `SERPAPI_API_KEY`
- `RESEND_API_KEY`
- `PAYSTACK_PUBLIC_KEY`
- `PAYSTACK_SECRET_KEY`
- `SENTRY_DSN`
- `LOGTAIL_TOKEN`
- `POSTHOG_API_KEY`
- `NEO4J_URI`
- `NEO4J_USER`
- `NEO4J_PASSWORD`

GCP-specific additions:

- `GCS_MODEL_BUCKET`
- `GCS_DOCUMENT_BUCKET`
- `GOOGLE_CLOUD_PROJECT`
- optional `CLOUD_TASKS_QUEUE`
- optional `CLOUD_TASKS_LOCATION`

Config files that must be updated:

- `.env.example`
- `frontend/.env.example`
- `backend/config.py`
- deployment workflow files
- new Terraform variables

## 10. CI/CD Plan

Current deploy pipeline:

- `.github/workflows/deploy.yml`
- Azure OIDC login
- ACR build/push
- Azure Container Apps deploy
- Container Apps migration job

Target deploy pipeline:

- GitHub Actions OIDC to GCP Workload Identity Federation
- Docker buildx builds backend, worker, and frontend
- Push images to Artifact Registry
- Run Cloud Run migration job
- Deploy backend Cloud Run service
- Deploy worker Cloud Run service
- Deploy frontend Cloud Run service
- Run health checks and smoke tests

New workflow files:

- `.github/workflows/deploy-gcp.yml`
- optional `.github/workflows/migrate-gcp.yml`

The repository now uses the GCP deployment workflow as the active deploy path. Historical cloud rollback should be handled from source control history rather than by keeping a second active workflow in the tree.

## 11. Network and Domain Plan

Required public endpoints:

- frontend HTTPS domain
- backend HTTPS domain
- Auth0 callback URL
- Auth0 logout URL
- Auth0 web origin
- Auth0 webhook receiver URL
- Paystack webhook receiver URL

Cloud Run ingress:

- Frontend: public
- Backend: public but protected by JWT middleware, with CORS restricted to frontend domains
- Worker: not public if implemented as always-on service without HTTP entrypoints, except health checks if needed
- Migration jobs: not public

Recommended domains:

- `staging.cogent.ai` -> frontend Cloud Run
- `api-staging.cogent.ai` -> backend Cloud Run
- `app.cogent.ai` -> production frontend
- `api.cogent.ai` -> production backend

## 12. Observability Plan

GCP native:

- Cloud Logging
- Cloud Monitoring
- Error Reporting
- uptime checks
- service metrics for Cloud Run and Cloud SQL

Existing third-party observability can remain:

- Sentry
- PostHog
- Better Stack / Logtail
- Prometheus `/metrics` endpoint

Code references:

- `backend/observability.py`
- `backend/main.py`
- `infrastructure/dashboards/grafana-cogent.json`
- `infrastructure/alerting/*`
- `infrastructure/monitoring/uptime-config.yml`

Migration work:

- Replace Azure Log Analytics assumptions in docs and runbooks.
- Add Cloud Run log and error triage instructions.
- Preserve `/metrics` and current Prometheus labels.

## 13. Full Product Surfaces To Preserve

The migration must preserve all active pages and endpoints:

- Home
- Studio
- Marketplace
- Signals
- Signal drawer and dossier exports
- Library and intelligence briefs
- Investigate
- Domains
- Market Data
- Alerts
- Discovery
- Pipeline admin
- Settings
- Billing and Paystack
- Privacy/export/delete flows
- API keys
- Feature gates and credits
- ML and refinement jobs
- document processing
- Auth0 and Paystack webhooks

Important endpoint router index:

- `backend/api/v1/__init__.py`

Important frontend API client index:

- `frontend/lib/api/index.ts`
- `frontend/lib/api/client.ts`

## 14. Implementation Phases

### Phase 0: Freeze The Target

- Keep Auth0.
- Keep current roles and permissions.
- Keep all product surfaces.
- Keep RQ for the first GCP staging pass.
- Use Upstash Redis first, then evaluate queue replacement after staging proof.

### Phase 1: Add GCP Infrastructure

Create Terraform for:

- Artifact Registry
- Cloud SQL PostgreSQL
- Secret Manager secrets
- Cloud Storage buckets
- Cloud Run backend service
- Cloud Run worker service
- Cloud Run frontend service
- Cloud Run migration job
- Cloud Scheduler jobs, initially disabled if the in-process scheduler remains active
- service accounts and IAM

### Phase 2: Build And Deploy Containers To GCP

- Build backend image from `Dockerfile`.
- Build worker image from `Dockerfile.worker`.
- Build frontend image from `frontend/Dockerfile`.
- Push to Artifact Registry.
- Deploy all three Cloud Run services.

### Phase 3: Data Migration

- Export Azure PostgreSQL.
- Restore into Cloud SQL.
- Enable pgvector.
- Run Alembic.
- Run catalog bootstrap.
- Verify core tables and counts.

### Phase 4: Runtime Validation

Run:

- `/health`
- `/api/v1/pipeline/status`
- `scripts/validate_intelligence_pipeline.py`
- frontend login/signup
- Studio contract creation
- marketplace activation
- manual fetch
- worker processing
- signal creation
- brief refresh
- dossier export

### Phase 5: Storage Replacement

- Add Cloud Storage settings.
- Replace Azure Blob document/model storage code.
- Update document import and cleanup tests.
- Verify ML model loading from GCS if production uses remote artifacts.

### Phase 6: Scheduler Hardening

- Move periodic scheduling from backend APScheduler to Cloud Scheduler and Cloud Run Jobs.
- Ensure only one scheduler path is active per environment.
- Update pipeline status to show Cloud Scheduler/Cloud Run job health.

### Phase 7: Cutover

- Update Auth0 callbacks/web origins.
- Update Paystack webhooks.
- Update DNS.
- Run final smoke and intelligence validation.
- Keep Azure in rollback mode until GCP production is stable.

## 15. Required Code Changes

Minimum code changes for first GCP staging:

- Replace legacy cloud-specific env comments in `backend/config.py`.
- Add GCS settings in `backend/config.py`.
- Add GCP deployment env examples in `.env.example`.
- Add GCP build args for frontend `BACKEND_URL` and `NEXT_PUBLIC_API_URL`.
- Add Terraform or Pulumi infra under a new directory, recommended `infrastructure-gcp/`.
- Add `.github/workflows/deploy-gcp.yml`.
- Update `scripts/validate_intelligence_pipeline.py` docs for GCP endpoints.

Code changes after first staging proof:

- Keep Cloud Storage document cleanup and model artifact handling aligned with `backend/storage.py`.
- Move scheduler dispatch from APScheduler to Cloud Scheduler/Cloud Run jobs.
- Optionally replace RQ with Cloud Tasks after validating the worker path.

## 16. Key Risks

1. RQ on Upstash must be validated under real worker load.
   The Redis API is broadly compatible, but RQ behavior depends on queues, registries, blocking operations, and worker heartbeats.

2. In-process scheduling can duplicate work on Cloud Run.
   Keep backend max instances constrained during first staging or move scheduler to Cloud Scheduler early.

3. Cloud SQL pgvector must be verified before data restore is considered complete.

4. Auth0 callbacks and API audience grants must be updated for GCP domains.

5. Legacy object-storage assumptions must not remain in production document/model paths after GCP cutover.

6. Cloud Run services need correct timeout, CPU, memory, concurrency, and min instance settings for long AI and acquisition paths.

7. Worker health and pipeline status must be revalidated after Redis moves to Upstash.

## 17. Acceptance Criteria

GCP staging is ready when:

- Frontend, backend, and worker deploy from Artifact Registry.
- Backend `/health` passes.
- Frontend Auth0 login works on the GCP domain.
- Backend validates Auth0 API access tokens.
- Auth0 and Paystack webhooks reach the backend.
- Cloud SQL contains migrated data and pgvector works.
- Upstash Redis supports rate limits, cache, job queue state, and worker heartbeats.
- Worker is online and visible in `/api/v1/pipeline/status`.
- A contract creation or marketplace activation queues acquisition work.
- Worker consumes the job and lands signals.
- Signals appear in the UI.
- Brief refresh works.
- Dossier export works.
- Settings, privacy, billing, and API key flows work.
- Cloud Logging/Sentry/PostHog show enough production diagnostics.

## 18. Research Sources

- Cloud Run overview: https://docs.cloud.google.com/run/docs/overview/what-is-cloud-run
- Cloud Run jobs: https://docs.cloud.google.com/run/docs/execute/jobs
- Cloud Run and Cloud Tasks: https://docs.cloud.google.com/run/docs/triggering/using-tasks
- Cloud Run container deployment: https://docs.cloud.google.com/run/docs/deploying
- Cloud SQL for PostgreSQL: https://docs.cloud.google.com/sql/docs/postgres
- Cloud SQL from Cloud Run: https://docs.cloud.google.com/sql/docs/postgres/connect-run
- Cloud SQL PostgreSQL extensions and pgvector support: https://docs.cloud.google.com/sql/docs/postgres/extensions
- Secret Manager overview: https://docs.cloud.google.com/secret-manager/docs/overview
- Artifact Registry: https://docs.cloud.google.com/artifact-registry/docs
- Cloud Scheduler: https://docs.cloud.google.com/scheduler/docs
- Cloud Storage overview: https://docs.cloud.google.com/storage/docs/introduction
- Upstash Redis docs: https://upstash.com/docs/redis
- Upstash Redis API compatibility: https://upstash.com/docs/redis/overall/rediscompatibility
- Upstash Redis durability: https://upstash.com/docs/redis/features/durability
- Upstash QStash: https://upstash.com/docs/qstash/overall/getstarted
