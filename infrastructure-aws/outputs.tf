output "alb_dns_name" {
  description = "Application Load Balancer DNS name."
  value       = aws_lb.app.dns_name
}

output "frontend_url" {
  description = "Resolved frontend URL."
  value       = local.frontend_url
}

output "backend_url" {
  description = "Resolved backend URL."
  value       = local.backend_url
}

output "ecr_repositories" {
  description = "ECR repository URLs for application images."
  value = {
    base_analytics = aws_ecr_repository.base_analytics.repository_url
    frontend       = aws_ecr_repository.frontend.repository_url
    backend        = aws_ecr_repository.backend.repository_url
    worker         = aws_ecr_repository.worker.repository_url
  }
}

output "ecs_cluster_name" {
  description = "ECS cluster name."
  value       = aws_ecs_cluster.app.name
}

output "ecs_services" {
  description = "ECS service names."
  value = {
    frontend = aws_ecs_service.frontend.name
    backend  = aws_ecs_service.backend.name
    worker   = aws_ecs_service.worker.name
  }
}

output "artifact_bucket" {
  description = "S3 bucket used for documents, model artifacts, and generated artifacts."
  value       = aws_s3_bucket.app.bucket
}

output "runtime_secret_names" {
  description = "Secrets Manager names that must be populated before services can run successfully."
  value       = [for secret in aws_secretsmanager_secret.runtime : secret.name]
}

output "database_secret_name" {
  description = "Secrets Manager name containing DATABASE_URL."
  value       = aws_secretsmanager_secret.database_url.name
}

output "redis_secret_name" {
  description = "Secrets Manager name containing REDIS_URL."
  value       = aws_secretsmanager_secret.redis_url.name
}
