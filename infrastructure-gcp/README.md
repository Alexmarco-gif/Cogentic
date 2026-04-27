# Cogent GCP Infrastructure

This directory provisions the full Cogent platform on GCP while preserving the current product scope and Auth0 authentication model.

It creates:

- Artifact Registry for backend, worker, and frontend images
- Cloud SQL for PostgreSQL
- Secret Manager secrets
- Cloud Storage buckets for ML models and documents
- Cloud Run services for backend, worker, and frontend
- Cloud Run job for Alembic migrations
- Service accounts and IAM bindings

Upstash Redis is external to this Terraform module. Create the Upstash database first, then provide its `rediss://` URL as the `redis-url` secret.

## First Apply

Create a `terraform.tfvars` file from the example:

```bash
cp terraform.tfvars.example terraform.tfvars
```

Required high-signal values:

```hcl
project_id = "your-gcp-project"
region     = "europe-west2"

secret_values = {
  "redis-url"                = "rediss://default:..."
  "secret-key"               = "..."
  "auth0-domain"             = "..."
  "auth0-audience"           = "https://api.cogent.ai"
  "auth0-m2m-client-id"      = "..."
  "auth0-m2m-client-secret"  = "..."
  "auth0-webhook-secret"     = "..."
  "auth0-frontend-secret"    = "..."
  "auth0-client-id"          = "..."
  "auth0-client-secret"      = "..."
  "openai-api-key"           = "..."
}
```

Then run:

```bash
terraform init
terraform plan
terraform apply
```

The first `terraform apply` needs image URIs that exist in Artifact Registry. For a brand-new project, either push initial backend, worker, and frontend images first, or point the image variables at a temporary known-good image and let `.github/workflows/deploy-gcp.yml` replace them with the real Cogent images.

After the first apply, build and push images through `.github/workflows/deploy-gcp.yml` or with Docker and `gcloud run deploy`.

Required GitHub Actions variables:

- `GCP_STAGING_REGION`
- `GCP_STAGING_ARTIFACT_REGISTRY`
- `GCP_PRODUCTION_REGION`
- `GCP_PRODUCTION_ARTIFACT_REGISTRY`
- `BACKEND_URL`
- `FRONTEND_URL`
- `NEXT_PUBLIC_API_URL`

Required GitHub Actions secrets:

- `GCP_WORKLOAD_IDENTITY_PROVIDER`
- `GCP_DEPLOY_SERVICE_ACCOUNT`
- `SMOKE_TEST_TOKEN`

## Auth0 Updates

Add the Cloud Run frontend URL or custom domain to:

- Allowed Callback URLs: `https://<frontend-domain>/api/auth/callback`
- Allowed Logout URLs: `https://<frontend-domain>`
- Allowed Web Origins: `https://<frontend-domain>`

Keep the existing API audience and client grants.
