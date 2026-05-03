# AWS Full Platform Migration Blueprint

Date: 2026-05-01

## Decision

We are switching the full Cogent platform target to AWS. This is not a reduced MVP path. The goal is to keep the same product intent and system capability:

- authenticated Next.js frontend
- FastAPI backend API
- background workers for acquisition, signal generation, briefs, alerts, and intelligence jobs
- PostgreSQL with pgvector
- Redis-compatible queue/cache/state layer
- object storage for uploaded documents, generated artifacts, models, and pipeline outputs
- Auth0 authentication and authorization as currently designed
- live data acquisition, scraping, market data, signal dossiers, library briefs, investigate, alerts, domains, settings, and admin pipeline visibility

The recommended AWS runtime target is Amazon ECS on AWS Fargate, not App Runner, because this platform needs multiple coordinated containers and worker processes, not only a simple web service.

## Why ECS Fargate

ECS Fargate lets us run the existing Dockerized services without managing EC2 servers. It also gives us the control we need for private networking, separate worker services, task IAM roles, scheduled jobs, service discovery, health checks, and load balancing.

This maps cleanly to the existing application shape:

- frontend container: Next.js web app
- backend container: FastAPI API
- worker container: RQ worker
- scheduled job container/task: acquisition and pipeline maintenance triggers

App Runner is simpler for a single web app, but it becomes awkward once we need persistent worker services, Redis queues, private database access, and scheduled ingestion. Lambda would require too much rewrite for the current worker and scraping model. EKS is more operational overhead than we need right now.

## Service Mapping

| Current responsibility | AWS target | Notes |
| --- | --- | --- |
| Container image registry | Amazon ECR | Single image registry for frontend, backend, worker, and base images. |
| Frontend runtime | ECS Fargate service behind ALB | Runs `frontend/Dockerfile`. |
| Backend runtime | ECS Fargate service behind ALB | Runs `Dockerfile`. |
| Worker runtime | ECS Fargate service without public ingress | Runs `Dockerfile.worker`. |
| Scheduled acquisition | EventBridge Scheduler to ECS task or backend scheduler endpoint | Prefer EventBridge to avoid duplicate in-process schedulers. |
| PostgreSQL | Amazon RDS for PostgreSQL | Enable pgvector extension in database migrations/bootstrap. |
| Redis/RQ | Amazon ElastiCache for Redis/Valkey | Preserve existing RQ architecture first. |
| Object storage | Amazon S3 | Canonical object storage for documents, model artifacts, and generated files. |
| Secrets | AWS Secrets Manager | Inject secrets into ECS task definitions. |
| Public routing | Application Load Balancer + ACM | TLS for frontend and API hostnames. |
| DNS | Route 53 or existing DNS provider | Point frontend/API domains to ALB records. |
| Logs/metrics | CloudWatch Logs and CloudWatch metrics | Keep Sentry/PostHog/Logtail as product telemetry if still desired. |
| CI/CD | GitHub Actions OIDC to AWS | Build Docker images, push ECR, run migrations, update ECS services. |
| Auth | Existing Auth0 tenant | Keep Auth0. Update callback/logout/origin URLs for AWS domains. |

## AWS Target Architecture

The staging/production environment should use:

- one VPC with public and private subnets across at least two Availability Zones
- public Application Load Balancer in public subnets
- ECS Fargate tasks in private subnets
- RDS PostgreSQL in private subnets
- ElastiCache Redis/Valkey in private subnets
- S3 bucket for application storage
- Secrets Manager for runtime secrets
- ECR repositories for frontend, backend, and worker images
- CloudWatch log groups per service
- EventBridge schedules for recurring acquisition/pipeline jobs

Traffic shape:

- user browser -> ALB -> frontend ECS service
- frontend server/client API calls -> backend API hostname -> ALB -> backend ECS service
- backend -> RDS, Redis, S3, external providers
- worker -> Redis queue, RDS, S3, external providers
- EventBridge -> scheduled ECS task or backend-controlled scheduler endpoint

## Codebase Changes Required

The previous non-AWS migration work must be replaced, not layered on top forever.

Remove or retire:

- non-AWS infrastructure folders
- non-AWS deploy workflows
- non-AWS setup docs once AWS docs replace them
- non-AWS object storage dependencies
- non-AWS object storage URI assumptions

Add or change:

- `infrastructure-aws/` Terraform
- `.github/workflows/deploy-aws.yml`
- S3 storage helper using `boto3`
- AWS runtime environment variable names where needed
- ECS-compatible health checks and deployment commands
- AWS validation runbook

The storage layer should stay abstract at the application boundary. Product code should use the application storage helper instead of provider-specific object URLs directly. The helper should expose the same application operations:

- read object by URI
- write object
- delete object
- create signed download URL if needed
- normalize provider-specific URLs into an internal storage reference

## Runtime Plan

Create three ECR repositories:

- `cogent-frontend`
- `cogent-backend`
- `cogent-worker`

Create three ECS task definitions:

- frontend task: exposes Next.js port
- backend task: exposes API port and uses backend secrets
- worker task: no public port, runs RQ worker command

Create ECS services:

- frontend service with ALB target group
- backend service with ALB target group
- worker service with desired count at least 1 in staging when validating ingestion

Use separate task roles:

- frontend task role: minimal, usually no S3/write permissions
- backend task role: read/write S3 where the backend needs it, read secrets only if not injected
- worker task role: read/write S3, provider access through injected secrets, queue/database access through network

## Database Plan

Use Amazon RDS for PostgreSQL.

Required setup:

- choose a PostgreSQL version that supports the needed pgvector extension
- create the app database and app user
- enable `CREATE EXTENSION IF NOT EXISTS vector;`
- run Alembic migrations from a one-off ECS migration task
- keep RDS private, reachable only from ECS/security-group-approved clients
- enable automated backups
- use Multi-AZ for production when budget allows

For staging, start with the smallest viable instance class that can run migrations and realistic test traffic. Do not under-size production readiness tests so badly that worker timeouts look like app bugs.

## Redis And Queue Plan

Preserve Redis/RQ first. This avoids a large rewrite while moving cloud providers.

Use Amazon ElastiCache for Redis/Valkey:

- private subnet only
- TLS enabled where supported by selected mode
- security group allows backend and worker tasks only
- `REDIS_URL` points to the ElastiCache endpoint

Later, we can consider moving some queue workloads to SQS or Step Functions, but not during the first AWS migration. The first migration should prove the existing intelligence pipeline works unchanged.

## Object Storage Plan

Use Amazon S3 for:

- uploaded source documents
- generated briefs/exports if stored server-side
- model artifacts
- acquisition artifacts and normalized payloads if currently persisted

Application changes:

- use `boto3` for S3 object operations
- support `s3://bucket/key` as the canonical internal URI
- optionally support HTTPS S3 URLs during migration
- keep all object operations behind `backend/storage.py` or the existing storage boundary

IAM changes:

- backend and worker task roles get scoped access to the specific bucket/prefixes
- frontend should not get broad bucket credentials

## Secrets And Configuration Plan

Use AWS Secrets Manager for sensitive values:

- database URL or database password
- Redis URL/auth token if needed
- Auth0 domain/client/audience/client secret values
- OpenAI key
- NewsAPI key
- SerpAPI key
- NGX market data credentials
- Resend key/from address
- Paystack keys
- Sentry/PostHog/Logtail tokens if still used
- application `SECRET_KEY`

Use plain ECS environment variables for non-secret config:

- `ENVIRONMENT`
- `APP_BASE_URL`
- `FRONTEND_URL`
- `BACKEND_URL`
- feature flags
- public Auth0 values that are safe for frontend use

## Auth0 Plan

Keep Auth0. Do not rebuild auth for this migration.

Required Auth0 updates for AWS domains:

- Allowed Callback URLs:
  - `https://<aws-frontend-domain>/api/auth/callback`
- Allowed Logout URLs:
  - `https://<aws-frontend-domain>`
- Allowed Web Origins:
  - `https://<aws-frontend-domain>`
- Allowed CORS Origins:
  - `https://<aws-frontend-domain>`
- API audience remains whatever the backend currently validates, unless the code intentionally changes.

The frontend and backend must agree on:

- issuer
- audience
- callback domain
- logout domain
- cookie/session secret
- API base URL

## Scheduler And Acquisition Plan

Current acquisition depends on workers being online and jobs being queued. AWS should make that operationally obvious.

First AWS implementation:

- keep the RQ worker process
- run it as an ECS Fargate service
- expose queue depth and worker heartbeat through the existing pipeline/status endpoint
- add CloudWatch alarms for worker count, task crashes, and queue backlog

Scheduling options:

- preferred: EventBridge Scheduler invokes ECS tasks or a protected backend scheduling endpoint
- temporary: keep in-app APScheduler only if exactly one scheduler instance is guaranteed

The production-safe direction is EventBridge because scaling backend tasks should not accidentally create duplicate schedulers.

## CI/CD Plan

Use GitHub Actions with OIDC to AWS. Avoid long-lived AWS keys in GitHub secrets.

Pipeline stages:

1. Checkout code.
2. Configure AWS credentials via OIDC role.
3. Build frontend/backend/worker Docker images.
4. Push images to ECR with commit SHA tags.
5. Run backend tests and frontend build checks.
6. Run database migrations as one-off ECS task.
7. Update ECS services to the new task definition revisions.
8. Wait for service stability.
9. Run smoke validation:
   - frontend health
   - backend health
   - auth redirect sanity
   - worker online
   - pipeline status
   - optional contract fetch

## Terraform Plan

Create `infrastructure-aws/` with:

- provider configuration
- remote state backend recommendation
- VPC module
- ECR repositories
- S3 bucket
- RDS PostgreSQL
- ElastiCache Redis/Valkey
- Secrets Manager secret definitions
- ECS cluster
- ECS task definitions and services
- ALB, listeners, target groups, security groups
- CloudWatch log groups
- EventBridge schedules
- IAM roles and policies
- outputs for frontend URL, backend URL, ECR repositories, database endpoint, Redis endpoint

Do not copy previous cloud infrastructure patterns directly. AWS networking, IAM, and load balancing should be designed natively.

## Migration Phases

### Phase 1 - AWS foundation

- create AWS account/project structure
- choose AWS region
- create Terraform AWS infrastructure folder
- define variables for staging
- create VPC, ECR, S3, Secrets Manager placeholders, CloudWatch logs

### Phase 2 - Data layer

- provision RDS PostgreSQL
- enable pgvector
- provision ElastiCache Redis/Valkey
- run migrations
- verify backend can connect from ECS private networking

### Phase 3 - Runtime

- build and push Docker images to ECR
- deploy backend ECS service
- deploy worker ECS service
- deploy frontend ECS service
- attach ALB routes and health checks

### Phase 4 - Storage migration

- use the S3 storage implementation
- update storage env vars
- test document upload/read/delete paths
- test brief/export artifact storage if applicable

### Phase 5 - Auth and external integrations

- update Auth0 application URLs for AWS frontend
- set backend API URL and CORS origins
- load provider secrets into Secrets Manager
- verify OpenAI, NewsAPI, SerpAPI, NGX, Resend, Paystack, Sentry/PostHog integrations as configured

### Phase 6 - Acquisition and intelligence validation

- verify worker service is running
- verify queue depth endpoint
- trigger a real contract fetch
- confirm signals land in database
- confirm signals show in frontend
- confirm briefs/library update
- confirm domains, market data, alerts, and investigate surfaces can read live data

### Phase 7 - Cutover cleanup

- remove or archive non-AWS infrastructure files
- remove non-AWS cloud dependencies
- update runbooks and deployment docs
- disable old staging resources to avoid surprise billing

## Acceptance Criteria

AWS staging is ready when all of these are true:

- frontend deploys from ECR to ECS and loads over HTTPS
- backend deploys from ECR to ECS and passes health checks
- worker deploys from ECR to ECS and is visible as online
- RDS PostgreSQL migrations succeed
- pgvector extension is available
- Redis/RQ queues are reachable from backend and worker
- S3 storage read/write/delete paths work
- Auth0 login/signup/callback/logout work on AWS domain
- pipeline status reports workers, queues, and provider readiness
- a real contract fetch queues work and lands signals
- signals appear in the UI
- intelligence briefs/library update from live data
- settings/privacy actions still call backend endpoints correctly
- market data, domains, alerts, investigate, and signal dossier pages do not show false empty states when backend data exists

## Main Risks

- Worker scheduling duplication if APScheduler runs in multiple backend tasks.
- Redis TLS/auth URL differences can break RQ if not tested carefully.
- RDS security groups can make the backend look broken when it is only blocked from the database.
- Auth0 callback/origin mismatch can break login even when the app deployment is healthy.
- S3 URL format changes can break document/model artifact paths if provider-specific URLs leak into product code.
- External provider credentials can make acquisition look broken even when AWS infrastructure is correct.
- Cost can creep through NAT gateways, ALB hours, RDS, ElastiCache, and logs if staging is left oversized.

## Recommended First Implementation Order

1. Create AWS Terraform foundation in `infrastructure-aws/`.
2. Add ECR repositories and GitHub Actions AWS OIDC deploy workflow.
3. Add S3 storage implementation and the AWS SDK dependency.
4. Provision RDS and Redis.
5. Deploy backend and worker first, because they prove database, queue, secrets, storage, and acquisition.
6. Deploy frontend after backend API URL and Auth0 URLs are final.
7. Run the intelligence validation checklist against AWS staging.
8. Remove non-AWS cloud-specific code and docs after AWS staging is proven.

## Research Sources

- AWS Fargate for ECS: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.html
- Amazon ECR: https://docs.aws.amazon.com/AmazonECR/latest/userguide/what-is-ecr.html
- Amazon RDS for PostgreSQL: https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_PostgreSQL.html
- RDS PostgreSQL extension versions, including pgvector: https://docs.aws.amazon.com/AmazonRDS/latest/PostgreSQLReleaseNotes/postgresql-extensions.html
- Amazon ElastiCache: https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/WhatIs.html
- Amazon S3: https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html
- AWS Secrets Manager: https://docs.aws.amazon.com/secretsmanager/latest/userguide/intro.html
- EventBridge Scheduler: https://docs.aws.amazon.com/scheduler/latest/UserGuide/what-is-scheduler.html
- ECS task IAM roles: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-iam-roles.html
- GitHub Actions OIDC for AWS: https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws
