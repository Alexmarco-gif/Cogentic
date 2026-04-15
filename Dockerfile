# ==============================================
# DOCKERFILE - FastAPI Backend
# ==============================================
# Multi-stage build for production-ready container
# Optimized for Azure Container Apps

# Stage 1: Builder
ARG BASE_IMAGE=cogent-python-analytics:latest
FROM ${BASE_IMAGE} AS builder

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /usr/local /usr/local

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port (Azure Container Apps will override this)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Run FastAPI with Gunicorn + Uvicorn workers for production concurrency.
# WEB_CONCURRENCY env var overrides --workers (Azure Container Apps sets it automatically).
CMD ["gunicorn", "backend.main:app", "--worker-class", "uvicorn.workers.UvicornWorker", "--workers", "4", "--bind", "0.0.0.0:8000", "--timeout", "120", "--graceful-timeout", "30", "--keep-alive", "5", "--limit-request-body", "10485760", "--access-logfile", "-", "--error-logfile", "-"]
