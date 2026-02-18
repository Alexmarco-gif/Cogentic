"""
Shared test fixtures for the Cogent backend test suite.

Provides:
  - Async SQLite in-memory database (swaps PostgreSQL)
  - Override FastAPI dependencies (get_db, get_current_user, get_redis)
  - Factory fixtures for all core models
  - Mock auth helpers (fake JWT, AuthContext)
  - httpx AsyncClient wired to the FastAPI app
"""

import asyncio
from collections.abc import AsyncGenerator
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
import pytest_asyncio

# ---------------------------------------------------------------------------
# Patch PostgreSQL-only column types BEFORE any model import so that
# SQLAlchemy's Base.metadata uses SQLite-compatible types.
# ---------------------------------------------------------------------------
import sqlalchemy.dialects.postgresql as _pg
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Map JSONB → JSON for SQLite
from sqlalchemy.types import JSON, String, Text

_pg.JSONB = JSON  # type: ignore[attr-defined]
_pg.JSON = JSON  # type: ignore[attr-defined]

# Map UUID(as_uuid=True) → String(36) using TypeDecorator for reliable
# bind/result processing in ALL SQLAlchemy contexts (INSERT, WHERE, etc.)
from uuid import UUID as _PyUUID

from sqlalchemy.types import TypeDecorator  # noqa: E402


class _FakeUUID(TypeDecorator):
    """Drop-in for postgresql.UUID — stores as VARCHAR(36) in SQLite,
    automatically converts Python UUID ↔ str on bind/result."""

    impl = String(36)
    cache_ok = True

    def __init__(self, *args, **kwargs):
        # Accept and discard as_uuid and any other PG-specific kwargs
        super().__init__()

    def process_bind_param(self, value, dialect):
        if value is not None:
            return str(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            if not isinstance(value, _PyUUID):
                return _PyUUID(value)
            return value
        return value


_pg.UUID = _FakeUUID  # type: ignore[attr-defined]


# Map ARRAY → JSON for SQLite (store arrays as JSON strings)
class _FakeARRAY(JSON):
    """Drop-in replacement for postgresql.ARRAY that stores as JSON."""

    def __init__(self, *args, **kwargs):
        super().__init__()


_pg.ARRAY = _FakeARRAY  # type: ignore[attr-defined]

# Stub pgvector.sqlalchemy.Vector → nullable Text column
try:
    import pgvector.sqlalchemy as _pgv

    class _FakeVector(Text):
        """Store vectors as plain text in SQLite (not used in tests)."""

        def __init__(self, *args, **kwargs):
            super().__init__()

    _pgv.Vector = _FakeVector  # type: ignore[attr-defined]
except ImportError:
    pass

# NOW it is safe to import application code
from backend.auth.schemas import AuthContext, TokenPayload  # noqa: E402
from backend.database import get_db  # noqa: E402

# Import all models so metadata.create_all picks them up
from backend.models import (  # noqa: E402, F401
    AIJob,
    AIUsageLog,
    APIKey,
    AuditLog,
    BetaAccount,
    BriefSignal,
    CausalEdge,
    CausalEvent,
    ChatMessage,
    ChatSession,
    CreditTransaction,
    Document,
    Entity,
    EntityAlias,
    EntityRelationship,
    EntitySourceProfile,
    FeatureGate,
    Industry,
    IntelligenceBrief,
    MLModelRegistry,
    MLModelRun,
    MoatMetricSnapshot,
    Organization,
    OrgUser,
    PricingConfig,
    Recommendation,
    RegulatoryEvent,
    RegulatoryImpact,
    RegulatoryPattern,
    RegulatoryRule,
    SearchQuery,
    Signal,
    SignalContract,
    SignalEntity,
    SignalScore,
    Subscription,
    User,
    UserFeedback,
)
from backend.models.base import Base  # noqa: E402

# ── async event-loop fixture (session-scoped) ────────────────────────


@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ── Database engine & session ────────────────────────────────────────

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create an async SQLite engine (lives for the whole test session)."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture()
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Per-test DB session wrapped in a SAVEPOINT so each test starts clean.

    Uses nested transactions:
      BEGIN (outer) → SAVEPOINT (inner per-test) → ROLLBACK after test.
    This is fast — no table re-creation between tests.
    """
    async_session_factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with test_engine.connect() as conn:
        trans = await conn.begin()
        session = async_session_factory(bind=conn)

        # Make session.begin_nested() work (SQLite compat)
        # The outer transaction is already started; tests use this session.
        yield session

        await session.close()
        await trans.rollback()


# ── FastAPI app with dependency overrides ────────────────────────────


@pytest_asyncio.fixture()
async def app(db_session: AsyncSession):
    """FastAPI app with DB + auth overrides.

    Patches the JWT middleware helpers so that every request is treated
    as authenticated (the middleware sets ``request.state.token_payload``
    with a fake payload).  Individual route-level auth is still overridden
    via ``dependency_overrides[get_current_user]`` in the client fixtures.
    """
    # Build a plausible TokenPayload that the middleware will accept
    import time as _time

    import backend.auth.utils as _auth_utils
    from backend.main import app as _app

    _fake_token_payload = TokenPayload(
        iss="https://cogent-test.us.auth0.com/",
        sub="auth0|test-user-000000",
        aud="https://api.cogent.ai",
        exp=int(_time.time()) + 3600,
        iat=int(_time.time()),
        azp="test-client-id",
        scope="openid profile email",
        gty=None,
        **{
            "https://cogent.ai/claims/org_id": str(uuid4()),
            "https://cogent.ai/claims/user_id": str(uuid4()),
            "https://cogent.ai/claims/email": "test@cogent.ai",
            "https://cogent.ai/claims/role": "member",
            "https://cogent.ai/claims/plan": "free",
            "https://cogent.ai/claims/is_super_admin": False,
        },
    )

    # Monkey-patch the helpers used by JWTMiddleware.dispatch
    _orig_extract = _auth_utils.extract_token_from_header
    _orig_verify = _auth_utils.verify_token

    _auth_utils.extract_token_from_header = lambda request: "fake-jwt-token"

    async def _fake_verify(token):
        return _fake_token_payload

    _auth_utils.verify_token = _fake_verify

    # Override DB dependency
    async def _override_get_db():
        yield db_session

    _app.dependency_overrides[get_db] = _override_get_db

    yield _app

    _app.dependency_overrides.clear()
    # Restore original auth utils
    _auth_utils.extract_token_from_header = _orig_extract
    _auth_utils.verify_token = _orig_verify


@pytest_asyncio.fixture()
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    """httpx AsyncClient wired to the FastAPI app (no real network)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest_asyncio.fixture()
async def unauthenticated_client(
    db_session: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
    """Client with NO auth bypass — middleware will reject with 401.

    Used to verify that unauthenticated requests are properly rejected.
    Does NOT patch auth_utils, so the real JWT middleware runs.
    """
    from backend.main import app as _app

    async def _override_get_db():
        yield db_session

    _app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    _app.dependency_overrides.clear()


# ── Auth helpers ─────────────────────────────────────────────────────


def make_auth_context(
    *,
    user_id=None,
    auth0_id=None,
    email="test@cogent.ai",
    org_id=None,
    role="member",
    plan="free",
    is_super_admin=False,
) -> AuthContext:
    """Build a fake AuthContext for testing."""
    return AuthContext(
        user_id=user_id or uuid4(),
        auth0_id=auth0_id or f"auth0|{uuid4().hex[:24]}",
        email=email,
        org_id=org_id or uuid4(),
        role=role,
        plan=plan,
        is_super_admin=is_super_admin,
        token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        request_id="test-request-id",
    )


def make_auth_header(auth: AuthContext | None = None) -> dict[str, str]:
    """Return an Authorization header dict.

    In integration tests the JWT middleware is active, but we override
    ``get_current_user`` via ``authenticated_client`` so no real JWT is
    needed.  This helper just sets a placeholder Bearer token so the
    middleware doesn't short-circuit with 401 before the override fires.
    """
    return {"Authorization": "Bearer test-jwt-token"}


@pytest.fixture()
def auth_context():
    """Default member-level AuthContext."""
    return make_auth_context()


@pytest.fixture()
def admin_auth_context():
    """Admin-level AuthContext."""
    return make_auth_context(role="admin")


@pytest.fixture()
def owner_auth_context():
    """Owner-level AuthContext."""
    return make_auth_context(role="owner")


@pytest.fixture()
def viewer_auth_context():
    """Viewer-level AuthContext."""
    return make_auth_context(role="viewer")


@pytest_asyncio.fixture()
async def authenticated_client(app, client, auth_context):
    """Client pre-configured to bypass auth with a member-level context."""
    from backend.auth.dependencies import get_current_user

    app.dependency_overrides[get_current_user] = lambda: auth_context
    yield client, auth_context
    app.dependency_overrides.pop(get_current_user, None)


@pytest_asyncio.fixture()
async def admin_client(app, client, admin_auth_context):
    """Client pre-configured with admin auth."""
    from backend.auth.dependencies import get_current_user

    app.dependency_overrides[get_current_user] = lambda: admin_auth_context
    yield client, admin_auth_context
    app.dependency_overrides.pop(get_current_user, None)


@pytest_asyncio.fixture()
async def owner_client(app, client, owner_auth_context):
    """Client pre-configured with owner auth."""
    from backend.auth.dependencies import get_current_user

    app.dependency_overrides[get_current_user] = lambda: owner_auth_context
    yield client, owner_auth_context
    app.dependency_overrides.pop(get_current_user, None)


# ── Model factory helpers ────────────────────────────────────────────


async def create_user(
    db: AsyncSession,
    *,
    email: str = "user@cogent.ai",
    auth0_id: str | None = None,
    name: str = "Test User",
    user_id=None,
) -> User:
    """Insert a User row and return it."""
    u = User(
        id=user_id or uuid4(),
        auth0_id=auth0_id or f"auth0|{uuid4().hex[:24]}",
        email=email,
        name=name,
    )
    db.add(u)
    await db.flush()
    await db.refresh(u)
    return u


async def create_organization(
    db: AsyncSession,
    *,
    name: str = "Test Org",
    slug: str | None = None,
    org_id=None,
    pricing_tier: str = "explorer",
    credits_allocated: int = 1000,
    credits_consumed: int = 0,
) -> Organization:
    """Insert an Organization row and return it."""
    o = Organization(
        id=org_id or uuid4(),
        name=name,
        slug=slug or f"test-org-{uuid4().hex[:8]}",
        pricing_tier=pricing_tier,
        credits_allocated_monthly=credits_allocated,
        credits_consumed=credits_consumed,
    )
    db.add(o)
    await db.flush()
    await db.refresh(o)
    return o


async def create_org_user(
    db: AsyncSession,
    *,
    org: Organization,
    user: User,
    role: str = "member",
) -> OrgUser:
    """Insert an OrgUser membership."""
    ou = OrgUser(
        id=uuid4(),
        org_id=org.id,
        user_id=user.id,
        role=role,
    )
    db.add(ou)
    await db.flush()
    await db.refresh(ou)
    return ou


async def create_industry(
    db: AsyncSession,
    *,
    name: str = "Fintech",
    slug: str | None = None,
) -> Industry:
    i = Industry(
        id=uuid4(),
        name=name,
        slug=slug or f"ind-{uuid4().hex[:8]}",
    )
    db.add(i)
    await db.flush()
    await db.refresh(i)
    return i


async def create_entity(
    db: AsyncSession,
    *,
    name: str = "TestCorp",
    entity_type: str = "company",
    industry: Industry | None = None,
) -> Entity:
    e = Entity(
        id=uuid4(),
        name=name,
        entity_type=entity_type,
        industry_id=industry.id if industry else None,
    )
    db.add(e)
    await db.flush()
    await db.refresh(e)
    return e


async def create_signal_contract(
    db: AsyncSession,
    *,
    industry: Industry,
    name: str = "Test Contract",
    source_url: str = "https://example.com/feed",
    source_type: str = "rss",
) -> SignalContract:
    sc = SignalContract(
        id=uuid4(),
        name=name,
        industry_id=industry.id,
        source_url=source_url,
        source_type=source_type,
        refresh_cron="0 */1 * * *",
        schedule_tier="standard",
    )
    db.add(sc)
    await db.flush()
    await db.refresh(sc)
    return sc


async def create_signal(
    db: AsyncSession,
    *,
    contract: SignalContract,
    org: Organization | None = None,
    title: str = "Test Signal",
    signal_type: str = "news",
    confidence: float = 0.8,
) -> Signal:
    s = Signal(
        id=uuid4(),
        contract_id=contract.id,
        org_id=org.id if org else None,
        title=title,
        signal_type=signal_type,
        confidence=confidence,
        fetched_at=datetime.now(timezone.utc),
    )
    db.add(s)
    await db.flush()
    await db.refresh(s)
    return s


async def create_subscription(
    db: AsyncSession,
    *,
    org: Organization,
    plan_tier: str = "free",
    status: str = "active",
) -> Subscription:
    sub = Subscription(
        id=uuid4(),
        org_id=org.id,
        plan_tier=plan_tier,
        status=status,
    )
    db.add(sub)
    await db.flush()
    await db.refresh(sub)
    return sub


async def create_chat_session(
    db: AsyncSession,
    *,
    user: User,
    org: Organization,
    industry: Industry | None = None,
    title: str = "Test Chat",
) -> ChatSession:
    cs = ChatSession(
        id=uuid4(),
        user_id=user.id,
        org_id=org.id,
        industry_id=industry.id if industry else None,
        title=title,
    )
    db.add(cs)
    await db.flush()
    await db.refresh(cs)
    return cs


async def create_chat_message(
    db: AsyncSession,
    *,
    session: ChatSession,
    role: str = "user",
    content: str = "Hello",
) -> ChatMessage:
    cm = ChatMessage(
        id=uuid4(),
        session_id=session.id,
        role=role,
        content=content,
    )
    db.add(cm)
    await db.flush()
    await db.refresh(cm)
    return cm


async def create_intelligence_brief(
    db: AsyncSession,
    *,
    industry: Industry,
    org: Organization | None = None,
    title: str = "Test Brief",
    brief_type: str = "pre_built",
    status: str = "published",
) -> IntelligenceBrief:
    ib = IntelligenceBrief(
        id=uuid4(),
        org_id=org.id if org else None,
        industry_id=industry.id,
        title=title,
        brief_type=brief_type,
        status=status,
    )
    db.add(ib)
    await db.flush()
    await db.refresh(ib)
    return ib


async def create_document(
    db: AsyncSession,
    *,
    org: Organization,
    user: User,
    filename: str = "report.pdf",
    size_bytes: int = 1024,
) -> Document:
    d = Document(
        id=uuid4(),
        org_id=org.id,
        owner_id=user.id,
        filename=filename,
        size_bytes=size_bytes,
    )
    db.add(d)
    await db.flush()
    await db.refresh(d)
    return d


async def create_api_key(
    db: AsyncSession,
    *,
    org: Organization,
    user: User | None = None,
    name: str = "Test API Key",
) -> APIKey:
    import hashlib

    raw_key = f"cogent_pk_live_{uuid4().hex[:32]}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    ak = APIKey(
        id=uuid4(),
        org_id=org.id,
        created_by_user_id=user.id if user else None,
        name=name,
        key_hash=key_hash,
        key_prefix=raw_key[:16],
    )
    db.add(ak)
    await db.flush()
    await db.refresh(ak)
    return ak


async def create_credit_transaction(
    db: AsyncSession,
    *,
    org: Organization,
    user: User | None = None,
    action_type: str = "intelligence_brief",
    credits_consumed: int = 50,
    credits_remaining: int = 950,
) -> CreditTransaction:
    ct = CreditTransaction(
        id=uuid4(),
        org_id=org.id,
        user_id=user.id if user else None,
        action_type=action_type,
        credits_consumed=credits_consumed,
        credits_remaining=credits_remaining,
    )
    db.add(ct)
    await db.flush()
    await db.refresh(ct)
    return ct


async def create_feature_gate(
    db: AsyncSession,
    *,
    feature_key: str = "api_access",
    required_tier: str = "growth",
    required_role: str | None = None,
) -> FeatureGate:
    fg = FeatureGate(
        feature_key=feature_key,
        required_tier=required_tier,
        required_role=required_role,
    )
    db.add(fg)
    await db.flush()
    await db.refresh(fg)
    return fg
