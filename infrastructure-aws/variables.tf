variable "aws_region" {
  description = "AWS region to deploy into."
  type        = string
  default     = "eu-west-2"
}

variable "environment" {
  description = "Deployment environment name."
  type        = string
  default     = "staging"
}

variable "project_name" {
  description = "Short project name used in AWS resource names."
  type        = string
  default     = "cogent"
}

variable "vpc_cidr" {
  description = "CIDR block for the application VPC."
  type        = string
  default     = "10.40.0.0/16"
}

variable "enable_nat_gateway" {
  description = "Create a NAT gateway so private ECS tasks can reach external APIs."
  type        = bool
  default     = true
}

variable "certificate_arn" {
  description = "Optional ACM certificate ARN for HTTPS. Leave empty for HTTP-only bootstrap."
  type        = string
  default     = ""
}

variable "frontend_domain_name" {
  description = "Frontend hostname used in app config and Auth0 callbacks."
  type        = string
  default     = ""
}

variable "backend_domain_name" {
  description = "Backend API hostname used in app config and CORS."
  type        = string
  default     = ""
}

variable "db_name" {
  description = "PostgreSQL database name."
  type        = string
  default     = "cogent"
}

variable "db_username" {
  description = "PostgreSQL application username."
  type        = string
  default     = "cogent"
}

variable "db_password" {
  description = "PostgreSQL application password. Store only in local terraform.tfvars or a secure Terraform variable store."
  type        = string
  sensitive   = true
}

variable "db_instance_class" {
  description = "RDS instance class."
  type        = string
  default     = "db.t4g.micro"
}

variable "db_engine_version" {
  description = "PostgreSQL engine version. Choose a version that supports pgvector in your region."
  type        = string
  default     = "16.13"
}

variable "redis_node_type" {
  description = "ElastiCache Redis node type."
  type        = string
  default     = "cache.t4g.micro"
}

variable "redis_auth_token" {
  description = "ElastiCache Redis auth token. Store only in local terraform.tfvars or a secure Terraform variable store."
  type        = string
  sensitive   = true
}

variable "frontend_desired_count" {
  description = "Desired frontend ECS tasks."
  type        = number
  default     = 0
}

variable "backend_desired_count" {
  description = "Desired backend ECS tasks."
  type        = number
  default     = 0
}

variable "worker_desired_count" {
  description = "Desired worker ECS tasks."
  type        = number
  default     = 0
}

variable "frontend_cpu" {
  description = "Frontend task CPU units."
  type        = number
  default     = 512
}

variable "frontend_memory" {
  description = "Frontend task memory in MiB."
  type        = number
  default     = 1024
}

variable "backend_cpu" {
  description = "Backend task CPU units."
  type        = number
  default     = 1024
}

variable "backend_memory" {
  description = "Backend task memory in MiB."
  type        = number
  default     = 2048
}

variable "worker_cpu" {
  description = "Worker task CPU units."
  type        = number
  default     = 1024
}

variable "worker_memory" {
  description = "Worker task memory in MiB."
  type        = number
  default     = 2048
}

variable "image_tag" {
  description = "Container image tag to deploy."
  type        = string
  default     = "latest"
}

variable "frontend_secret_names" {
  description = "Frontend secret environment variable names to create in Secrets Manager and inject into the frontend task."
  type        = set(string)
  default = [
    "AUTH0_SECRET",
    "AUTH0_ISSUER_BASE_URL",
    "AUTH0_CLIENT_ID",
    "AUTH0_CLIENT_SECRET",
    "AUTH0_AUDIENCE"
  ]
}

variable "runtime_secret_names" {
  description = "All application secret names to create in Secrets Manager. Not every created secret is injected into every task."
  type        = set(string)
  default = [
    "SECRET_KEY",
    "AUTH0_DOMAIN",
    "AUTH0_AUDIENCE",
    "AUTH0_SECRET",
    "AUTH0_ISSUER_BASE_URL",
    "AUTH0_CLIENT_ID",
    "AUTH0_CLIENT_SECRET",
    "AUTH0_M2M_CLIENT_ID",
    "AUTH0_M2M_CLIENT_SECRET",
    "AUTH0_WEBHOOK_SECRET",
    "OPENAI_API_KEY",
    "NEWSAPI_API_KEY",
    "NGX_MARKET_DATA_API_KEY",
    "NGX_MARKET_DATA_BASE_URL",
    "X_BEARER_TOKEN",
    "SERPAPI_API_KEY",
    "RESEND_API_KEY",
    "RESEND_FROM_EMAIL",
    "PAYSTACK_SECRET_KEY",
    "PAYSTACK_PUBLIC_KEY",
    "SENTRY_DSN",
    "POSTHOG_API_KEY",
    "POSTHOG_HOST",
    "LOGTAIL_TOKEN"
  ]
}

variable "backend_secret_names" {
  description = "Backend secret environment variable names to create in Secrets Manager and inject into the backend task."
  type        = set(string)
  default = [
    "SECRET_KEY",
    "AUTH0_DOMAIN",
    "AUTH0_AUDIENCE",
    "AUTH0_M2M_CLIENT_ID",
    "AUTH0_M2M_CLIENT_SECRET",
    "AUTH0_WEBHOOK_SECRET"
  ]
}

variable "worker_secret_names" {
  description = "Worker secret environment variable names to create in Secrets Manager and inject into the worker task."
  type        = set(string)
  default = [
    "SECRET_KEY",
    "AUTH0_DOMAIN",
    "AUTH0_AUDIENCE",
    "AUTH0_M2M_CLIENT_ID",
    "AUTH0_M2M_CLIENT_SECRET"
  ]
}

variable "additional_backend_environment" {
  description = "Additional non-secret backend environment variables."
  type        = map(string)
  default     = {}
}

variable "additional_frontend_environment" {
  description = "Additional non-secret frontend environment variables."
  type        = map(string)
  default     = {}
}

variable "additional_worker_environment" {
  description = "Additional non-secret worker environment variables."
  type        = map(string)
  default     = {}
}

variable "tags" {
  description = "Additional AWS tags."
  type        = map(string)
  default     = {}
}
