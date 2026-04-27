# GCP + Upstash Setup Runbook

Date: 2026-04-26

This guide sets up Cogent on GCP + Upstash while keeping the existing Auth0 authentication and current full platform scope.

Follow it in order. Do not skip ahead unless a step says it is optional.

## What You Need Before Starting

Accounts:

- Google account with access to Google Cloud Console
- Upstash account
- Auth0 tenant admin access
- Paystack dashboard access
- GitHub repo admin or maintainer access

Local tools:

- PowerShell
- Docker Desktop
- Terraform
- Google Cloud CLI
- Git

Already done on this machine:

- Terraform is installed and validates the repo's `infrastructure-gcp/` config.

Still needed:

- Google Cloud CLI installation and login.

Official links:

- Google Cloud Console: https://console.cloud.google.com/
- Google Cloud CLI install: https://docs.cloud.google.com/sdk/docs/install
- Google Cloud billing: https://docs.cloud.google.com/billing/docs/how-to/modify-project
- Upstash Redis quickstart: https://upstash.com/docs/redis/overall/getstarted
- Auth0 dashboard: https://manage.auth0.com/

## Step 1: Install Google Cloud CLI

Try the Windows package manager first:

```powershell
winget install --id Google.CloudSDK --source winget --accept-package-agreements --accept-source-agreements
```

If the install times out or fails, use the official installer:

1. Open https://docs.cloud.google.com/sdk/docs/install
2. Find the Windows installer section.
3. Download the Google Cloud CLI installer.
4. Run the installer.
5. Keep the bundled Python option enabled unless you know you need a different Python.
6. Finish the install.
7. Close PowerShell.
8. Open a new PowerShell window.

Verify:

```powershell
gcloud version
```

Expected:

- It prints Google Cloud CLI component versions.

## Step 2: Create Or Select A GCP Project

In the browser:

1. Open https://console.cloud.google.com/
2. Click the project selector near the top-left.
3. Click `New Project`.
4. Project name: `Cogent Staging`
5. Project ID: choose something globally unique, for example `cogent-staging-<shortname>`
6. Click `Create`.

Write down:

```text
GCP_PROJECT_ID=<your-project-id>
```

In PowerShell:

```powershell
gcloud auth login
gcloud config set project <your-project-id>
gcloud config get-value project
```

Expected:

- The last command prints your project ID.

## Step 3: Enable Billing

GCP services like Cloud Run and Cloud SQL require billing.

In the browser:

1. Open https://console.cloud.google.com/billing
2. If you do not have a billing account, create one.
3. Open your `Cogent Staging` project.
4. Link the project to the billing account.

Official doc:

- https://docs.cloud.google.com/billing/docs/how-to/modify-project

Important:

- Set a budget alert before deploying.
- A budget alert does not automatically stop services, but it warns you early.

Budget click path:

1. Go to https://console.cloud.google.com/billing
2. Open your billing account.
3. Click `Budgets & alerts`.
4. Click `Create budget`.
5. Scope: your Cogent project.
6. Amount: choose your warning limit.
7. Alerts: set thresholds like 50%, 90%, 100%.
8. Save.

## Step 4: Enable Required GCP APIs

Run:

```powershell
gcloud services enable run.googleapis.com sqladmin.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com storage.googleapis.com iamcredentials.googleapis.com cloudbuild.googleapis.com
```

Verify:

```powershell
gcloud services list --enabled --filter="name:(run.googleapis.com OR sqladmin.googleapis.com OR artifactregistry.googleapis.com OR secretmanager.googleapis.com OR storage.googleapis.com)"
```

Expected:

- You see Cloud Run, Cloud SQL Admin, Artifact Registry, Secret Manager, and Cloud Storage APIs enabled.

## Step 5: Create Upstash Redis

In the browser:

1. Open https://console.upstash.com/
2. Sign in.
3. Click `Create Database`.
4. Choose `Redis`.
5. Name: `cogent-staging-redis`
6. Region: choose the closest region to your GCP Cloud Run region.
7. Type: choose the normal serverless/global option that Upstash recommends.
8. Click `Create`.

After creation:

1. Open the database.
2. Find `Connect`.
3. Find the Redis URL.
4. Copy the TLS URL that starts with `rediss://`.

Write down:

```text
REDIS_URL=rediss://default:<password>@<host>:<port>
```

Official doc:

- https://upstash.com/docs/redis/overall/getstarted

## Step 6: Choose Region Names

Recommended first staging region:

```text
GCP_REGION=europe-west2
```

Why:

- It is London.
- It is close to the previous UK South deployment.
- It is a good default for the current staging geography.

If your Upstash selected region is different, keep GCP and Upstash geographically close where possible.

## Step 7: Prepare Terraform Variables

From repo root:

```powershell
Copy-Item infrastructure-gcp\terraform.tfvars.example infrastructure-gcp\terraform.tfvars
notepad infrastructure-gcp\terraform.tfvars
```

Fill:

```hcl
project_id  = "<your-gcp-project-id>"
region      = "europe-west2"
environment = "staging"
```

For image URLs, use this shape:

```hcl
backend_image  = "europe-west2-docker.pkg.dev/<your-gcp-project-id>/cogent/cogent-backend:latest"
worker_image   = "europe-west2-docker.pkg.dev/<your-gcp-project-id>/cogent/cogent-worker:latest"
frontend_image = "europe-west2-docker.pkg.dev/<your-gcp-project-id>/cogent/cogent-frontend:latest"
```

For URLs before custom domains exist, use temporary values:

```hcl
frontend_base_url = "https://staging.cogent.ai"
public_api_url    = "https://api-staging.cogent.ai"
cors_origins      = "https://staging.cogent.ai"
```

We will later replace these with Cloud Run URLs or custom domains after first deploy.

In `secret_values`, set at least:

```hcl
"redis-url"                  = "rediss://..."
"secret-key"                 = "<long-random-secret>"
"auth0-domain"               = "<your-auth0-domain>"
"auth0-audience"             = "https://api.cogent.ai"
"auth0-m2m-client-id"        = "<from-auth0>"
"auth0-m2m-client-secret"    = "<from-auth0>"
"auth0-webhook-secret"       = "<current-webhook-secret>"
"auth0-frontend-secret"      = "<long-random-secret>"
"auth0-client-id"            = "<from-auth0-frontend-app>"
"auth0-client-secret"        = "<from-auth0-frontend-app>"
"openai-api-key"             = "<openai-key>"
"newsapi-api-key"            = "<newsapi-key>"
"ngx-market-data-api-key"    = "<ngx-key>"
"ngx-market-data-base-url"   = "https://ngxpulse.ng/api/ngxdata/market"
"x-bearer-token"             = "<x-token>"
"serpapi-api-key"            = "<serpapi-key>"
"resend-api-key"             = "<resend-key>"
"paystack-public-key"        = "<paystack-public-key>"
"paystack-secret-key"        = "<paystack-secret-key>"
```

Generate long secrets:

```powershell
[Convert]::ToHexString((1..32 | ForEach-Object { Get-Random -Minimum 0 -Maximum 256 }))
```

## Step 8: Create Artifact Registry Before First Image Push

Terraform can create Artifact Registry, but Cloud Run also needs image URLs. The easiest order is:

1. Let Terraform create Artifact Registry using a temporary image later, or
2. Create Artifact Registry manually now, push real images, then apply Terraform with real image URLs.

Use option 2 for clarity.

Run:

```powershell
gcloud artifacts repositories create cogent --repository-format=docker --location=europe-west2 --description="Cogent container images"
```

Configure Docker auth:

```powershell
gcloud auth configure-docker europe-west2-docker.pkg.dev
```

## Step 9: Build And Push First Images

From repo root:

```powershell
$PROJECT_ID = "<your-gcp-project-id>"
$REGION = "europe-west2"
$REPO = "$REGION-docker.pkg.dev/$PROJECT_ID/cogent"
```

Build shared Python base:

```powershell
docker build -t cogent-python-analytics:latest -f Dockerfile.base-analytics .
```

Build backend:

```powershell
docker build --build-arg BASE_IMAGE=cogent-python-analytics:latest -t "$REPO/cogent-backend:latest" -f Dockerfile .
```

Build worker:

```powershell
docker build --build-arg BASE_IMAGE=cogent-python-analytics:latest -t "$REPO/cogent-worker:latest" -f Dockerfile.worker .
```

Build frontend:

```powershell
docker build -t "$REPO/cogent-frontend:latest" -f frontend/Dockerfile --build-arg NEXT_PUBLIC_API_URL=https://api-staging.cogent.ai --build-arg BACKEND_URL=https://api-staging.cogent.ai ./frontend
```

Push:

```powershell
docker push "$REPO/cogent-backend:latest"
docker push "$REPO/cogent-worker:latest"
docker push "$REPO/cogent-frontend:latest"
```

## Step 10: Run Terraform Plan And Apply

From repo root:

```powershell
terraform -chdir=infrastructure-gcp fmt -recursive
terraform -chdir=infrastructure-gcp init
terraform -chdir=infrastructure-gcp validate
terraform -chdir=infrastructure-gcp plan
```

Read the plan. It should create:

- Artifact Registry
- Cloud SQL
- Secret Manager secrets
- Cloud Run services
- Cloud Run migration job
- Cloud Storage buckets
- Service accounts and IAM

Apply:

```powershell
terraform -chdir=infrastructure-gcp apply
```

When asked:

```text
Do you want to perform these actions?
```

Type:

```text
yes
```

## Step 11: Get Cloud Run URLs

Run:

```powershell
gcloud run services list --region europe-west2
```

Write down:

```text
FRONTEND_URL=<cogent-staging-frontend url>
BACKEND_URL=<cogent-staging-backend url>
```

## Step 12: Update Auth0

Open:

- https://manage.auth0.com/

Go to:

1. `Applications`
2. `Applications`
3. Open your Cogent frontend Regular Web Application

Set:

```text
Allowed Callback URLs:
<FRONTEND_URL>/api/auth/callback

Allowed Logout URLs:
<FRONTEND_URL>

Allowed Web Origins:
<FRONTEND_URL>
```

Also check:

1. `Applications`
2. `APIs`
3. Open API identifier `https://api.cogent.ai`
4. Ensure the frontend app is allowed to request this API audience.

## Step 13: Update Terraform URLs And Reapply

Now replace temporary URLs in `infrastructure-gcp/terraform.tfvars`:

```hcl
frontend_base_url = "<FRONTEND_URL>"
public_api_url    = "<BACKEND_URL>"
cors_origins      = "<FRONTEND_URL>"
```

Then:

```powershell
terraform -chdir=infrastructure-gcp apply
```

## Step 14: Run Migrations

Terraform creates the migration job. Run:

```powershell
gcloud run jobs execute cogent-staging-migrate --region europe-west2 --wait
```

## Step 15: Check Health

Backend:

```powershell
curl.exe "<BACKEND_URL>/health"
```

Frontend:

Open:

```text
<FRONTEND_URL>
```

Worker:

```powershell
gcloud run services describe cogent-staging-worker --region europe-west2
```

Logs:

```powershell
gcloud run services logs read cogent-staging-backend --region europe-west2 --limit 100
gcloud run services logs read cogent-staging-worker --region europe-west2 --limit 100
gcloud run services logs read cogent-staging-frontend --region europe-west2 --limit 100
```

## Step 16: Update Paystack Webhooks

Open Paystack dashboard:

- https://dashboard.paystack.com/

Go to:

1. `Settings`
2. `API Keys & Webhooks`
3. Webhook URL

Set webhook URL:

```text
<FRONTEND_URL>/api/webhooks/paystack
```

If you use backend direct webhooks instead:

```text
<BACKEND_URL>/webhooks/paystack/events
```

Use the frontend proxy path first because the current Next.js app already proxies Paystack webhooks.

## Step 17: Validate Product Flow

Run the staging validator after login/admin token is available:

```powershell
$env:COGENT_BASE_URL = "<BACKEND_URL>"
$env:COGENT_BEARER_TOKEN = "<admin-token>"
python scripts/validate_intelligence_pipeline.py --trigger-fetch
```

Manual UI checks:

- Signup/login
- Home
- Studio
- Marketplace
- Signals
- Library
- Investigate
- Domains
- Market Data
- Alerts
- Pipeline
- Settings

Acceptance target:

- auth works
- backend health works
- worker is online
- marketplace templates load
- industries load
- contract/source activation queues jobs
- worker consumes jobs
- signals appear
- brief refresh works
- settings and billing do not throw network/auth errors

## Common Failure Points

### `gcloud` command not found

Close PowerShell and open a new one. If still missing, reinstall from:

https://docs.cloud.google.com/sdk/docs/install

### Terraform says APIs are disabled

Run Step 4 again.

### Cloud Run fails because secret version is missing

Make sure every secret in `terraform.tfvars` exists as a key in `secret_values`, even if temporarily blank.

### Backend cannot connect to database

Check:

```powershell
gcloud sql instances describe cogent-staging-postgres
gcloud run services logs read cogent-staging-backend --region europe-west2 --limit 100
```

### Auth0 callback mismatch

Add exact frontend URL plus `/api/auth/callback` to Auth0 allowed callback URLs.

### Browser API calls fail

Check:

- `public_api_url`
- `BACKEND_URL`
- `NEXT_PUBLIC_API_URL`
- backend `CORS_ORIGINS`
- Auth0 audience grant

