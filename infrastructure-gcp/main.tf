locals {
  name_prefix = "cogent-${var.environment}"

  required_secret_names = toset([
    "database-url",
    "redis-url",
    "secret-key",
    "auth0-domain",
    "auth0-audience",
    "auth0-m2m-client-id",
    "auth0-m2m-client-secret",
    "auth0-webhook-secret",
    "auth0-frontend-secret",
    "auth0-client-id",
    "auth0-client-secret",
    "openai-api-key",
    "newsapi-api-key",
    "ngx-market-data-api-key",
    "ngx-market-data-base-url",
    "x-bearer-token",
    "serpapi-api-key",
    "resend-api-key",
    "paystack-public-key",
    "paystack-secret-key",
    "sentry-dsn",
    "logtail-token",
    "posthog-api-key",
    "neo4j-uri",
    "neo4j-user",
    "neo4j-password",
  ])
  runtime_secret_names = setsubtract(local.required_secret_names, toset(["database-url"]))

  generated_database_url = "postgresql+asyncpg://${var.database_user}:${random_password.database.result}@/${var.database_name}?host=/cloudsql/${google_sql_database_instance.postgres.connection_name}"

  backend_secret_env = {
    DATABASE_URL             = "database-url"
    REDIS_URL                = "redis-url"
    SECRET_KEY               = "secret-key"
    AUTH0_DOMAIN             = "auth0-domain"
    AUTH0_AUDIENCE           = "auth0-audience"
    AUTH0_M2M_CLIENT_ID      = "auth0-m2m-client-id"
    AUTH0_M2M_CLIENT_SECRET  = "auth0-m2m-client-secret"
    AUTH0_WEBHOOK_SECRET     = "auth0-webhook-secret"
    OPENAI_API_KEY           = "openai-api-key"
    NEWSAPI_API_KEY          = "newsapi-api-key"
    NGX_MARKET_DATA_API_KEY  = "ngx-market-data-api-key"
    NGX_MARKET_DATA_BASE_URL = "ngx-market-data-base-url"
    X_BEARER_TOKEN           = "x-bearer-token"
    SERPAPI_API_KEY          = "serpapi-api-key"
    RESEND_API_KEY           = "resend-api-key"
    PAYSTACK_PUBLIC_KEY      = "paystack-public-key"
    PAYSTACK_SECRET_KEY      = "paystack-secret-key"
    SENTRY_DSN               = "sentry-dsn"
    LOGTAIL_TOKEN            = "logtail-token"
    POSTHOG_API_KEY          = "posthog-api-key"
    NEO4J_URI                = "neo4j-uri"
    NEO4J_USER               = "neo4j-user"
    NEO4J_PASSWORD           = "neo4j-password"
  }

  frontend_secret_env = {
    AUTH0_SECRET         = "auth0-frontend-secret"
    AUTH0_DOMAIN         = "auth0-domain"
    AUTH0_CLIENT_ID      = "auth0-client-id"
    AUTH0_CLIENT_SECRET  = "auth0-client-secret"
    AUTH0_AUDIENCE       = "auth0-audience"
    AUTH0_WEBHOOK_SECRET = "auth0-webhook-secret"
  }
}

resource "google_artifact_registry_repository" "images" {
  location      = var.region
  repository_id = var.artifact_repository_id
  description   = "Cogent container images"
  format        = "DOCKER"
}

resource "random_password" "database" {
  length  = 32
  special = false
}

resource "google_sql_database_instance" "postgres" {
  name             = "${local.name_prefix}-postgres"
  database_version = var.database_version
  region           = var.region

  settings {
    tier              = var.database_tier
    availability_type = var.environment == "production" ? "REGIONAL" : "ZONAL"
    disk_size         = 32
    disk_type         = "PD_SSD"

    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
    }
  }
}

resource "google_sql_database" "app" {
  name     = var.database_name
  instance = google_sql_database_instance.postgres.name
}

resource "google_sql_user" "app" {
  name     = var.database_user
  instance = google_sql_database_instance.postgres.name
  password = random_password.database.result
}

resource "google_storage_bucket" "models" {
  name                        = "${var.project_id}-${local.name_prefix}-ml-models"
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = false
}

resource "google_storage_bucket" "documents" {
  name                        = "${var.project_id}-${local.name_prefix}-documents"
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = false
}

resource "google_secret_manager_secret" "secrets" {
  for_each  = local.required_secret_names
  secret_id = "${local.name_prefix}-${each.key}"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "database_url" {
  secret      = google_secret_manager_secret.secrets["database-url"].id
  secret_data = local.generated_database_url
}

resource "google_secret_manager_secret_version" "provided" {
  for_each = local.runtime_secret_names

  secret      = google_secret_manager_secret.secrets[each.key].id
  secret_data = lookup(var.secret_values, each.key, "")
}

resource "google_service_account" "backend" {
  account_id   = "${local.name_prefix}-backend"
  display_name = "Cogent backend ${var.environment}"
}

resource "google_service_account" "worker" {
  account_id   = "${local.name_prefix}-worker"
  display_name = "Cogent worker ${var.environment}"
}

resource "google_service_account" "frontend" {
  account_id   = "${local.name_prefix}-frontend"
  display_name = "Cogent frontend ${var.environment}"
}

resource "google_project_iam_member" "backend_cloudsql" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.backend.email}"
}

resource "google_project_iam_member" "worker_cloudsql" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.worker.email}"
}

resource "google_project_iam_member" "runtime_secret_access" {
  for_each = {
    backend  = google_service_account.backend.email
    worker   = google_service_account.worker.email
    frontend = google_service_account.frontend.email
  }

  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${each.value}"
}

resource "google_storage_bucket_iam_member" "backend_documents" {
  bucket = google_storage_bucket.documents.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.backend.email}"
}

resource "google_storage_bucket_iam_member" "worker_documents" {
  bucket = google_storage_bucket.documents.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.worker.email}"
}

resource "google_storage_bucket_iam_member" "worker_models" {
  bucket = google_storage_bucket.models.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.worker.email}"
}

module "backend_service" {
  source = "./modules/cloud-run-service"

  name                = "${local.name_prefix}-backend"
  location            = var.region
  image               = var.backend_image
  service_account     = google_service_account.backend.email
  container_port      = 8000
  min_instances       = var.backend_min_instances
  max_instances       = 5
  cpu                 = "2"
  memory              = "2Gi"
  cpu_idle            = false
  cloud_sql_instances = [google_sql_database_instance.postgres.connection_name]
  public_ingress      = true
  secret_env          = local.backend_secret_env
  secret_prefix       = local.name_prefix
  plain_env = {
    APP_ENV                          = var.environment
    ENVIRONMENT                      = var.environment
    DEBUG                            = "false"
    REQUIRE_HEALTHY_DB_ON_STARTUP    = "true"
    REQUIRE_HEALTHY_REDIS_ON_STARTUP = "true"
    BOOTSTRAP_CATALOG_ON_STARTUP     = "true"
    CORS_ORIGINS                     = var.cors_origins
    GOOGLE_CLOUD_PROJECT             = var.project_id
    GCS_MODEL_BUCKET                 = google_storage_bucket.models.name
    GCS_DOCUMENT_BUCKET              = google_storage_bucket.documents.name
  }

  depends_on = [
    google_secret_manager_secret.secrets,
    google_secret_manager_secret_version.database_url,
    google_secret_manager_secret_version.provided,
  ]
}

module "worker_service" {
  source = "./modules/cloud-run-service"

  name                = "${local.name_prefix}-worker"
  location            = var.region
  image               = var.worker_image
  service_account     = google_service_account.worker.email
  container_port      = 8001
  min_instances       = var.worker_min_instances
  max_instances       = 3
  cpu                 = "2"
  memory              = "2Gi"
  cpu_idle            = false
  cloud_sql_instances = [google_sql_database_instance.postgres.connection_name]
  public_ingress      = false
  secret_env          = local.backend_secret_env
  secret_prefix       = local.name_prefix
  plain_env = {
    APP_ENV              = var.environment
    ENVIRONMENT          = var.environment
    DEBUG                = "false"
    GOOGLE_CLOUD_PROJECT = var.project_id
    GCS_MODEL_BUCKET     = google_storage_bucket.models.name
    GCS_DOCUMENT_BUCKET  = google_storage_bucket.documents.name
    WORKER_HEALTH_PORT   = "8001"
  }

  depends_on = [
    google_secret_manager_secret.secrets,
    google_secret_manager_secret_version.database_url,
    google_secret_manager_secret_version.provided,
  ]
}

module "frontend_service" {
  source = "./modules/cloud-run-service"

  name            = "${local.name_prefix}-frontend"
  location        = var.region
  image           = var.frontend_image
  service_account = google_service_account.frontend.email
  container_port  = 3000
  min_instances   = var.frontend_min_instances
  max_instances   = 5
  cpu             = "1"
  memory          = "1Gi"
  cpu_idle        = true
  public_ingress  = true
  secret_env      = local.frontend_secret_env
  secret_prefix   = local.name_prefix
  plain_env = {
    NODE_ENV                       = "production"
    APP_BASE_URL                   = var.frontend_base_url
    AUTH0_BASE_URL                 = var.frontend_base_url
    NEXT_PUBLIC_API_URL            = var.public_api_url
    BACKEND_URL                    = var.public_api_url
    NEXT_PUBLIC_LOGIN_ROUTE        = "/api/auth/login"
    NEXT_PUBLIC_PROFILE_ROUTE      = "/api/auth/profile"
    NEXT_PUBLIC_ACCESS_TOKEN_ROUTE = "/api/auth/access-token"
  }

  depends_on = [
    google_secret_manager_secret.secrets,
    google_secret_manager_secret_version.provided,
  ]
}

resource "google_cloud_run_v2_job" "migrate" {
  name     = "${local.name_prefix}-migrate"
  location = var.region

  template {
    template {
      service_account = google_service_account.backend.email

      volumes {
        name = "cloudsql"
        cloud_sql_instance {
          instances = [google_sql_database_instance.postgres.connection_name]
        }
      }

      containers {
        image   = var.backend_image
        command = ["alembic"]
        args    = ["upgrade", "head"]

        volume_mounts {
          name       = "cloudsql"
          mount_path = "/cloudsql"
        }

        env {
          name = "DATABASE_URL"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.secrets["database-url"].secret_id
              version = "latest"
            }
          }
        }
      }
    }
  }
}
