from uuid import uuid4

import pytest
from starlette.requests import Request

from backend.auth.dependencies import (
    _allowed_permissions_for_role,
    get_current_user_or_api_key,
)
from backend.models.document import Document
from backend.repositories.api_key import APIKeyRepository
from backend.repositories.base import BaseRepository, TenantRepository
from backend.signals.fetchers.base import BaseFetcher
from tests.conftest import create_org_user, create_organization, create_user


def test_capability_permissions_are_separate_from_role_names():
    assert "view_signals" in _allowed_permissions_for_role("viewer")
    assert "manage_signals" in _allowed_permissions_for_role("analyst")
    assert "manage_regulatory_knowledge" in _allowed_permissions_for_role("admin")
    assert "owner" in _allowed_permissions_for_role("owner")
    assert "manage_billing" not in _allowed_permissions_for_role("admin")


@pytest.mark.asyncio
async def test_api_key_dependency_builds_auth_context(db_session):
    org = await create_organization(db_session)
    user = await create_user(db_session)
    await create_org_user(db_session, org=org, user=user, role="admin")

    repo = APIKeyRepository(db_session)
    _, plaintext_key = await repo.create_key(
        org_id=org.id,
        created_by_user_id=user.id,
        name="Contract test key",
        scopes=["read:documents"],
    )
    await db_session.flush()

    request = Request(
        {
            "type": "http",
            "headers": [(b"x-api-key", plaintext_key.encode("utf-8"))],
            "client": ("127.0.0.1", 12345),
        }
    )

    auth = await get_current_user_or_api_key(request, db_session)

    assert auth.auth_method == "api_key"
    assert auth.org_id == org.id
    assert auth.user_id == user.id
    assert auth.api_key_scopes == ["read:documents"]


@pytest.mark.asyncio
async def test_tenant_owned_base_repository_is_guarded_in_strict_mode(
    db_session,
    monkeypatch,
):
    from backend.config import get_settings

    monkeypatch.setenv("ENFORCE_TENANT_SCOPED_REPOSITORIES", "true")
    get_settings.cache_clear()

    base_repo = BaseRepository(Document, db_session)
    with pytest.raises(RuntimeError, match="Unscoped get"):
        await base_repo.get(uuid4())

    tenant_repo = TenantRepository(Document, db_session, uuid4())
    assert await tenant_repo.get(uuid4()) is None

    monkeypatch.delenv("ENFORCE_TENANT_SCOPED_REPOSITORIES", raising=False)
    get_settings.cache_clear()


def test_hardened_fetcher_blocks_private_and_metadata_hosts():
    assert not BaseFetcher._is_safe_url("http://127.0.0.1:8000/health")
    assert not BaseFetcher._is_safe_url("http://169.254.169.254/latest/meta-data")
    assert not BaseFetcher._is_safe_url("file:///etc/passwd")


def test_openapi_contracts_cover_fixed_ml_and_entity_shapes(app):
    app.openapi_schema = None
    schema = app.openapi()

    train_all = schema["components"]["schemas"]["TrainAllQueuedResponse"]
    assert "jobs" in train_all["properties"]
    assert train_all["properties"]["jobs"]["items"]["type"] == "string"

    refinement = schema["components"]["schemas"]["RefinementResponse"]
    assert {"total", "refined", "duplicates", "errors", "duration_ms"}.issubset(
        refinement["properties"].keys()
    )

    relationship_request = schema["components"]["schemas"]["RelationshipUpsertRequest"]
    assert "source_entity_id" in relationship_request["properties"]
    assert "target_entity_id" in relationship_request["properties"]

    relationship_response = schema["components"]["schemas"]["RelationshipUpsertResponse"]
    assert "source_entity_id" in relationship_response["properties"]
    assert "target_entity_id" in relationship_response["properties"]
