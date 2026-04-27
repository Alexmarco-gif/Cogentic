output "artifact_registry_repository" {
  value = google_artifact_registry_repository.images.name
}

output "backend_url" {
  value = module.backend_service.uri
}

output "frontend_url" {
  value = module.frontend_service.uri
}

output "worker_service" {
  value = module.worker_service.name
}

output "cloud_sql_connection_name" {
  value = google_sql_database_instance.postgres.connection_name
}

output "models_bucket" {
  value = google_storage_bucket.models.name
}

output "documents_bucket" {
  value = google_storage_bucket.documents.name
}

