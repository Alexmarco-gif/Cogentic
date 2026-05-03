# Cogent Infrastructure

The active infrastructure implementation now lives in:

- `infrastructure-aws/`

The previous cloud deployment path has been removed so the repository has one primary deployment story: AWS ECS Fargate, ECR, RDS PostgreSQL, ElastiCache Redis, Secrets Manager, S3, ALB, and CloudWatch.

Generic monitoring and alerting assets remain in this directory.
