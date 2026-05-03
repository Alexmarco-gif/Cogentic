# AWS Setup Runbook

Date: 2026-05-01

This runbook is the active AWS setup path for the full Cogent platform runtime.

## 1. Install tools

Install:

- AWS CLI v2
- Terraform
- Docker Desktop

Verify:

```powershell
aws --version
terraform version
docker version
```

## 2. Sign in to AWS

```powershell
aws configure sso
aws sts get-caller-identity
```

Use the AWS account and region that will host staging. The default region in Terraform is `eu-west-2`.

## 3. Prepare Terraform

```powershell
cd infrastructure-aws
Copy-Item terraform.tfvars.example terraform.tfvars
terraform init
terraform plan
```

Review the plan carefully. The stack includes paid AWS resources: ALB, NAT gateway, RDS, ElastiCache, ECS Fargate, CloudWatch logs, and S3.

For the first apply, keep these values at `0` in `terraform.tfvars` so ECS does not try to start containers before images and secrets exist:

```hcl
frontend_desired_count = 0
backend_desired_count  = 0
worker_desired_count   = 0
```

Apply:

```powershell
terraform apply
```

## 4. Populate Secrets Manager

Terraform creates secret names, but real values must be added before ECS services can run correctly.

Required minimum:

```powershell
aws secretsmanager put-secret-value --secret-id cogent-staging/SECRET_KEY --secret-string "<generated-secret>"
aws secretsmanager put-secret-value --secret-id cogent-staging/AUTH0_DOMAIN --secret-string "<tenant>.auth0.com"
aws secretsmanager put-secret-value --secret-id cogent-staging/AUTH0_AUDIENCE --secret-string "https://api.cogent.ai"
aws secretsmanager put-secret-value --secret-id cogent-staging/AUTH0_SECRET --secret-string "<frontend-session-secret>"
aws secretsmanager put-secret-value --secret-id cogent-staging/AUTH0_ISSUER_BASE_URL --secret-string "https://<tenant>.auth0.com"
aws secretsmanager put-secret-value --secret-id cogent-staging/AUTH0_CLIENT_ID --secret-string "<auth0-frontend-client-id>"
aws secretsmanager put-secret-value --secret-id cogent-staging/AUTH0_CLIENT_SECRET --secret-string "<auth0-frontend-client-secret>"
aws secretsmanager put-secret-value --secret-id cogent-staging/AUTH0_M2M_CLIENT_ID --secret-string "<auth0-m2m-client-id>"
aws secretsmanager put-secret-value --secret-id cogent-staging/AUTH0_M2M_CLIENT_SECRET --secret-string "<auth0-m2m-client-secret>"
```

Add provider secrets for enabled integrations:

- `OPENAI_API_KEY`
- `NEWSAPI_API_KEY`
- `NGX_MARKET_DATA_API_KEY`
- `NGX_MARKET_DATA_BASE_URL`
- `X_BEARER_TOKEN`
- `SERPAPI_API_KEY`
- `RESEND_API_KEY`
- `RESEND_FROM_EMAIL`
- `PAYSTACK_SECRET_KEY`
- `PAYSTACK_PUBLIC_KEY`
- `SENTRY_DSN`
- `POSTHOG_API_KEY`
- `POSTHOG_HOST`
- `LOGTAIL_TOKEN`

## 5. Build and push images manually

Use this only before GitHub Actions is fully configured.

```powershell
$AWS_REGION="eu-west-2"
$ACCOUNT_ID=(aws sts get-caller-identity --query Account --output text)
$REGISTRY="$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
$PREFIX="cogent-staging"
$TAG="latest"

aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $REGISTRY

docker build -t "$REGISTRY/$PREFIX-python-analytics:$TAG" -f Dockerfile.base-analytics .
docker push "$REGISTRY/$PREFIX-python-analytics:$TAG"

docker build -t "$REGISTRY/$PREFIX-backend:$TAG" -f Dockerfile --build-arg BASE_IMAGE="$REGISTRY/$PREFIX-python-analytics:$TAG" .
docker push "$REGISTRY/$PREFIX-backend:$TAG"

docker build -t "$REGISTRY/$PREFIX-worker:$TAG" -f Dockerfile.worker --build-arg BASE_IMAGE="$REGISTRY/$PREFIX-python-analytics:$TAG" .
docker push "$REGISTRY/$PREFIX-worker:$TAG"

docker build -t "$REGISTRY/$PREFIX-frontend:$TAG" -f frontend/Dockerfile --build-arg NEXT_PUBLIC_API_URL="https://api-staging.cogent.ai" --build-arg BACKEND_URL="https://api-staging.cogent.ai" frontend
docker push "$REGISTRY/$PREFIX-frontend:$TAG"
```

## 6. Redeploy ECS services

After secrets and images exist, update `infrastructure-aws/terraform.tfvars`:

```hcl
frontend_desired_count = 1
backend_desired_count  = 1
worker_desired_count   = 1
```

Then apply the service count change:

```powershell
cd infrastructure-aws
terraform apply
```

```powershell
aws ecs update-service --cluster cogent-staging-cluster --service cogent-staging-backend --force-new-deployment
aws ecs update-service --cluster cogent-staging-cluster --service cogent-staging-worker --force-new-deployment
aws ecs update-service --cluster cogent-staging-cluster --service cogent-staging-frontend --force-new-deployment
aws ecs wait services-stable --cluster cogent-staging-cluster --services cogent-staging-backend cogent-staging-worker cogent-staging-frontend
```

## 7. Update Auth0

After the AWS frontend URL is known, update the frontend Auth0 application:

- Allowed Callback URLs: `https://<frontend-domain>/api/auth/callback`
- Allowed Logout URLs: `https://<frontend-domain>`
- Allowed Web Origins: `https://<frontend-domain>`
- Allowed CORS Origins: `https://<frontend-domain>`

## 8. Validate platform readiness

Check:

```powershell
curl https://<backend-domain>/health
aws ecs describe-services --cluster cogent-staging-cluster --services cogent-staging-backend cogent-staging-worker cogent-staging-frontend
```

Then verify:

- signup/login works
- worker is online
- `/api/v1/pipeline/status` reports queue and worker health
- a contract fetch queues and lands signals
- signals appear in the UI
- briefs/library update from live data
- market data, domains, alerts, investigate, and settings call backend endpoints successfully
