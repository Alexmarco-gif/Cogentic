"""
Backend Tests Package
=====================

This package contains end-to-end tests for the Cogent API.

Test Categories:
- test_preprod_e2e.py: Pre-production smoke tests (hits live API)

Run tests:
    pytest backend/tests/ -v

Run pre-prod E2E tests:
    PREPROD_API_URL=https://your-api.azurecontainerapps.io pytest backend/tests/test_preprod_e2e.py -v
"""
