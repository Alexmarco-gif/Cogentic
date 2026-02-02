"""Quick test to see auth response format"""
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

# Test missing auth
response = client.get("/api/v1/auth/me")
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")
print(f"Headers: {response.headers}")
