from pathlib import Path
from uuid import uuid4

import pytest

from backend.config import Settings
from backend.models.base import Base
from backend.models.signal_contract import SignalContract
from backend.repositories.signal_contract import SignalContractRepository
from tests.conftest import TEST_ORG_ID, create_industry, create_organization


@pytest.mark.asyncio
async def test_signal_contract_repository_scopes_by_org(db_session):
    industry = await create_industry(db_session, name="Banking")
    other_org = await create_organization(db_session, name="Other Org")

    tenant_contract = SignalContract(
        id=uuid4(),
        org_id=TEST_ORG_ID,
        name="Tenant Contract",
        industry_id=industry.id,
        source_url="https://example.com/tenant.xml",
        source_type="rss",
        refresh_cron="0 * * * *",
        schedule_tier="standard",
        status="active",
        is_active=True,
    )
    global_contract = SignalContract(
        id=uuid4(),
        org_id=None,
        name="Global Contract",
        industry_id=industry.id,
        source_url="https://example.com/global.xml",
        source_type="rss",
        refresh_cron="0 * * * *",
        schedule_tier="standard",
        status="active",
        is_active=True,
    )
    foreign_contract = SignalContract(
        id=uuid4(),
        org_id=other_org.id,
        name="Foreign Contract",
        industry_id=industry.id,
        source_url="https://example.com/foreign.xml",
        source_type="rss",
        refresh_cron="0 * * * *",
        schedule_tier="standard",
        status="active",
        is_active=True,
    )

    db_session.add_all([tenant_contract, global_contract, foreign_contract])
    await db_session.commit()

    repo = SignalContractRepository(db_session)

    visible = await repo.get_active_contracts(org_id=TEST_ORG_ID, include_global=True)
    visible_ids = {contract.id for contract in visible}
    assert tenant_contract.id in visible_ids
    assert global_contract.id in visible_ids
    assert foreign_contract.id not in visible_ids

    assert await repo.get_scoped(tenant_contract.id, org_id=TEST_ORG_ID) is not None
    assert await repo.get_scoped(foreign_contract.id, org_id=TEST_ORG_ID) is None

    count = await repo.count_scoped(
        org_id=TEST_ORG_ID, include_global=True, active_only=True
    )
    assert count == 2


def test_pricing_upgrade_route_initializes_real_checkout_flow():
    source = Path("backend/api/v1/pricing.py").read_text(encoding="utf-8")

    assert "PaystackService" in source
    assert 'status="checkout_initialized"' in source
    assert "initialize_subscription_checkout" in source
    assert '@router.post("/verify"' in source


def test_contract_fetch_route_blocks_webhook_pull_attempts():
    source = Path("backend/api/v1/contracts.py").read_text(encoding="utf-8")

    assert 'contract.source_type == "webhook"' in source
    assert "delivery-only" in source
    assert "scheduled acquisition" in source


def test_settings_accept_release_debug_value():
    settings = Settings(
        database_url="postgresql+asyncpg://user:pass@localhost:5432/cogent",
        auth0_domain="example.auth0.com",
        auth0_audience="https://api.cogent.test",
        auth0_m2m_client_id="client-id",
        auth0_m2m_client_secret="client-secret",
        secret_key="development-secret-key-with-enough-length",
        debug="release",
    )

    assert settings.debug is False


def test_signal_template_models_are_registered_in_metadata():
    assert "signal_templates" in Base.metadata.tables
    assert "signal_template_subscriptions" in Base.metadata.tables
