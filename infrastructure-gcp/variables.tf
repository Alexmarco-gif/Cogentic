variable "project_id" {
  type        = string
  description = "GCP project ID."
}

variable "region" {
  type        = string
  description = "GCP region for regional resources."
  default     = "europe-west2"
}

variable "environment" {
  type        = string
  description = "Deployment environment name."
  default     = "staging"
}

variable "artifact_repository_id" {
  type        = string
  description = "Artifact Registry repository ID."
  default     = "cogent"
}

variable "backend_image" {
  type        = string
  description = "Backend image URI in Artifact Registry."
}

variable "worker_image" {
  type        = string
  description = "Worker image URI in Artifact Registry."
}

variable "frontend_image" {
  type        = string
  description = "Frontend image URI in Artifact Registry."
}

variable "frontend_base_url" {
  type        = string
  description = "Public frontend base URL used by Auth0 and browser navigation."
}

variable "public_api_url" {
  type        = string
  description = "Public backend API URL used by frontend build/runtime."
}

variable "cors_origins" {
  type        = string
  description = "Comma-separated frontend origins allowed by the backend."
}

variable "database_tier" {
  type        = string
  description = "Cloud SQL machine tier."
  default     = "db-custom-1-3840"
}

variable "database_version" {
  type        = string
  description = "Cloud SQL PostgreSQL version."
  default     = "POSTGRES_16"
}

variable "database_name" {
  type        = string
  description = "Application database name."
  default     = "cogent"
}

variable "database_user" {
  type        = string
  description = "Application database user."
  default     = "cogent"
}

variable "secret_values" {
  type        = map(string)
  description = "Secret Manager values. Do not commit real tfvars files."
  sensitive   = true
  default     = {}
}

variable "backend_min_instances" {
  type    = number
  default = 1
}

variable "worker_min_instances" {
  type    = number
  default = 1
}

variable "frontend_min_instances" {
  type    = number
  default = 1
}

