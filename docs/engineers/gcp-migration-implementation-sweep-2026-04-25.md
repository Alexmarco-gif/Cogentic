# GCP Migration Implementation Sweep

Date: 2026-04-25

## Scope

This sweep covers the current full-platform migration from the previous cloud deployment path to GCP + Upstash while preserving Auth0 authentication, existing authorization, and the full Cogent product surface.

This is not an MVP reduction. The implementation keeps backend, frontend, worker, signals, acquisition, briefs, settings, billing, webhooks, and admin pipeline flows in scope.

## Implemented

- Added Terraform infrastructure under `infrastructure-gcp/`.
- Added Cloud Run services for backend, worker, and frontend.
- Added Cloud Run migration job for Alembic.
- Added Cloud SQL for PostgreSQL.
- Added Artifact Registry.
- Added Secret Manager secrets and Cloud Run secret injection.
- Added Cloud Storage buckets for ML models and documents.
- Added service accounts and IAM bindings.
- Preserved Auth0 variables and token validation model.
- Replaced the previous deploy workflow with `.github/workflows/deploy-gcp.yml`.
- Added Secret Manager seeding scripts:
  - `scripts/seed-secret-manager.sh`
  - `scripts/seed-secret-manager.ps1`
- Added Cloud Storage backend helper:
  - `backend/storage.py`
- Updated document ingestion/cleanup to support `gs://`, `https://storage.googleapis.com/...`, and virtual-hosted GCS URLs.
- Removed the object-storage SDK dependency from the previous cloud provider and added `google-cloud-storage`.
- Updated root and frontend env examples for GCP, Cloud SQL, Upstash, and Cloud Storage.
- Removed previous cloud IaC files and old secret-seeding scripts.
- Updated monitoring config to reference Cloud Monitoring instead of the previous cloud-specific availability test.

## Validated

- Terraform installed locally: `Terraform v1.14.9`.
- Terraform initialized with local backend disabled.
- Terraform formatted successfully.
- Terraform validated successfully.
- Backend Python compile passed.
- Frontend TypeScript check passed.
- New Cloud Storage parser tests passed.
- New GCP deploy workflow YAML parses.
- Uptime monitoring YAML parses.
- Active runtime/deployment scan is clean for previous cloud-specific terms across:
  - `backend`
  - `frontend`
  - `scripts`
  - `infrastructure`
  - `.github`
  - env examples
  - Dockerfiles
  - requirements
  - tests

The remaining previous-cloud references are intentionally historical in `docs/engineers/gcp-upstash-full-platform-migration-blueprint.md`.

## Important Findings

### 1. Google Cloud CLI is still needed

Terraform is installed, but `gcloud` is not installed yet. Deployment and manual GCP setup need Google Cloud CLI for:

- project auth
- Artifact Registry Docker auth
- Cloud Run inspection
- Cloud SQL connection checks
- Secret Manager verification

### 2. Cloud Run worker is configured as an always-on service

The worker still uses RQ and long-lived Redis worker behavior. For the first GCP staging pass this is intentional.

The worker service has CPU idle disabled in Terraform so it can keep processing jobs without waiting for HTTP requests.

### 3. Scheduler duplication still needs operational control

The current backend has an in-process APScheduler. Cloud Run can scale horizontally, so the first GCP staging deployment should keep backend max instances conservative until scheduler dispatch is moved to Cloud Scheduler.

### 4. Upstash Redis needs real RQ validation

The Redis client can point at Upstash via `rediss://`, but RQ behavior must be validated under real queue/worker load before production cutover.

### 5. Secret Manager versions are created for all runtime secrets

Terraform now creates a version for every runtime secret reference, defaulting to an empty value if not supplied. This prevents Cloud Run from failing because a referenced secret has no `latest` version.

The app can still fail startup if required provider credentials are blank in staging/production, which is correct.

## Still Required Before First GCP Staging Apply

- Create or select the GCP project.
- Enable required APIs:
  - Cloud Run
  - Cloud SQL Admin
  - Artifact Registry
  - Secret Manager
  - Cloud Storage
  - IAM Credentials
  - Cloud Build, if builds will run in GCP
- Create the Upstash Redis database and get the `rediss://` URL.
- Decide the first staging region.
- Fill `infrastructure-gcp/terraform.tfvars`.
- Configure GitHub Actions variables and secrets for GCP Workload Identity Federation.
- Push initial backend, worker, and frontend images to Artifact Registry, or use temporary bootstrap images for the first Terraform apply.
- Update Auth0 callback/logout/web-origin URLs for the GCP frontend domain.
- Update Paystack webhook URLs for the GCP frontend/backend proxy path.

## Recommended Next Implementation Step

Create the GCP project setup runbook and bootstrap commands next:

- `gcloud auth login`
- `gcloud config set project ...`
- API enablement commands
- Artifact Registry creation or Terraform apply order
- Docker auth to Artifact Registry
- first image build/push commands
- Terraform `tfvars` checklist
- first `terraform plan/apply`
- post-apply validation with `scripts/validate_intelligence_pipeline.py`

