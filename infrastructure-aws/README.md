# Cogent AWS Infrastructure

This Terraform stack deploys the full Cogent platform on AWS:

- ECS Fargate frontend, backend, and worker services
- ECR repositories for Docker images
- RDS PostgreSQL for application data and pgvector
- ElastiCache Redis for RQ queues/cache
- S3 for documents, ML artifacts, and generated files
- Secrets Manager for runtime secrets
- Application Load Balancer for public traffic
- CloudWatch Logs for service logs

## Bootstrap

```powershell
cd infrastructure-aws
Copy-Item terraform.tfvars.example terraform.tfvars
terraform init
terraform plan
terraform apply
```

The stack creates secret containers in AWS Secrets Manager. Before setting ECS desired counts above zero in a fresh environment, populate the required secrets:

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

Provider secrets such as OpenAI, NewsAPI, NGX, SerpAPI, Resend, Paystack, Sentry, PostHog, and Logtail should be populated the same way for the integrations you enable.

For first bootstrap, keep `frontend_desired_count`, `backend_desired_count`, and `worker_desired_count` at `0`. After images and secrets are ready, set them to `1` or higher and run `terraform apply` again.

## Images

Terraform creates these ECR repositories:

- `cogent-staging-frontend`
- `cogent-staging-backend`
- `cogent-staging-worker`
- `cogent-staging-python-analytics`

Build and push images through the AWS GitHub Actions workflow or manually with Docker/ECR.

## Database

After RDS is available, run migrations from a one-off backend task or from a secure machine that can reach the private database:

```powershell
alembic upgrade head
```

The database must have pgvector enabled:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

## Auth0

Update Auth0 after the AWS frontend URL is known:

- Allowed Callback URLs: `https://<frontend-domain>/api/auth/callback`
- Allowed Logout URLs: `https://<frontend-domain>`
- Allowed Web Origins: `https://<frontend-domain>`
- Allowed CORS Origins: `https://<frontend-domain>`

## Notes

- Private ECS tasks need NAT or VPC endpoints to reach Auth0, OpenAI, NewsAPI, SerpAPI, Resend, Paystack, and other external APIs.
- The included stack defaults to one NAT gateway for a safer production-like topology.
- For production, enable a real domain, ACM certificate, stronger RDS sizing, longer backups, and deletion protection.
