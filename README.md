# Cogent - AI-Powered SaaS Platform


## 1. Architecture Overview

**Cogent** is an AI-powered market intelligence platform with a three-tier architecture:

| Layer | Technology | Role |
|-------|-----------|------|
| **Frontend** | Next.js 14 (App Router) + Tailwind + Auth0 SDK | SSR/CSR SPA, handles auth flow, renders dashboards |
| **Backend API** | FastAPI (async) + SQLAlchemy 2.0 + Pydantic v2 | REST API, JWT auth, business logic, AI orchestration |
| **Workers** | RQ (Redis Queue) + Python | Background jobs: signal acquisition, document analysis, ML training |
| **Data Stores** | PostgreSQL (Azure) + pgvector, Redis, Neo4j | Relational data, caching/queues, knowledge graph |




```
Routes (api/v1/) → Services (services/) → Repositories (repositories/) → Models (models/) → PostgreSQL
                 ↘ AI layer (ai/)        → OpenAI API
                 ↘ ML layer (ml/)        → ONNX Runtime (local inference)
                 ↘ Signals (signals/)    → External data sources (RSS, APIs)
                 ↘ Agent (agent/)        → OpenAI tool-calling chat agent
                 ↘ Compliance (compliance/) → GDPR data retention & export
```

**Key Subsystems:**

- **Signal Intelligence Pipeline**: Fetchers → Processors → Dedup → Scoring → Storage
- **Causal Knowledge Graph**: Entity resolution → Relationship mapping → Causal inference (Neo4j + pgvector)
- **Intelligence Moat**: Feedback loops → Prediction backtesting → Replicability testing → Moat metrics
- **Chat Agent**: OpenAI-powered chat with tool calling, RAG over signals/briefs
- **Pricing & Feature Gating**: Tier-based access (Explorer → Growth → Mid-Market → Enterprise)

---

## 2. System Flow Diagram

```
User Browser
    │
    ├─── Auth0 Login ──→ Auth0 ──→ JWT issued
    │
    ▼
Next.js Frontend (port 3000)
    │ /api/v1/* rewrites via next.config.js proxy
    ▼
FastAPI Backend (port 8000)
    │
    ├── CORS Middleware (outermost)
    ├── RequestIDMiddleware
    ├── RequestBodyLimitMiddleware
    ├── MetricsMiddleware (Prometheus)
    ├── N1QueryDetectionMiddleware
    ├── JWTMiddleware (Auth0 JWKS validation)
    │          │
    │          ├── Token valid → request.state.token_payload
    │          └── Token invalid → 401
    │
    ├── Rate Limiter (slowapi + Redis)
    │
    ▼
API v1 Router (146+ endpoints)
    │
    ├── get_current_user() dependency → DB lookup → AuthContext
    ├── Service Layer
    │      │
    │      ├── OpenAI API (chat, synthesis, embeddings)
    │      ├── ONNX Runtime (scoring, anomaly detection)
    │      └── Neo4j (causal graph queries)
    │
    ├── Repository Layer → SQLAlchemy AsyncSession → PostgreSQL (Azure)
    │
    └── Background Jobs → Redis Queue → RQ Worker
              │
              └── Signal acquisition, document analysis, ML training
```

---

## 🚀 Quick Start

### Prerequisites

- **Node.js** 18+ and npm
- **Python** 3.9+
- **Auth0 Account** (free tier works)
- **ngrok** or **cloudflared** (for webhook testing)

### Initial Setup

1. **Clone repository**
   ```bash
   git clone <repository-url>
   cd Cogent
   ```

2. **Configure Auth0**

   Quick summary:
   - Create Auth0 tenant
   - Create Regular Web App (Next.js)
   - Create M2M App (FastAPI)
   - Deploy custom claims action
   - Add test user metadata

3. **Configure environment variables**

   Create `frontend/.env.local`:
   ```bash
   # Auth0 Configuration
   AUTH0_SECRET='<generate with: openssl rand -hex 32>'
   AUTH0_BASE_URL='http://localhost:3000'
   AUTH0_ISSUER_BASE_URL='https://<your-tenant>.auth0.com'
   AUTH0_CLIENT_ID='<your-client-id>'
   AUTH0_CLIENT_SECRET='<your-client-secret>'
   AUTH0_AUDIENCE='https://api.cogent.ai'

   # Optional: Webhook secret
   AUTH0_WEBHOOK_SECRET='<generate with: openssl rand -hex 32>'

   # Environment
   NODE_ENV='development'
   ```

4. **Install dependencies**

   Frontend:
   ```bash
   cd frontend
   npm install
   ```

   Backend (Python):
   ```bash
   cd ..
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

5. **Start development servers**

   Frontend:
   ```bash
   cd frontend
   npm run dev
   ```

   Backend:
   ```bash
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   uvicorn backend.main:app --reload
   ```

   Worker (background jobs):
   ```bash
   python worker.py
   ```

6. **Test authentication**

   Open http://localhost:3000/auth-test and verify:
   - ✅ Login/logout works
   - ✅ JWT contains custom claims at `/jwt-test`
   - ✅ Protected routes require auth

---

## 📁 Project Structure

```
Cogent/
├── frontend/                   # Next.js 14 frontend
│   ├── app/                    # App router
│   │   ├── api/                # API routes
│   │   │   ├── auth/[auth0]/   # Auth0 SDK routes
│   │   │   ├── protected/      # Protected API example
│   │   │   └── webhooks/       # Webhook receivers
│   │   ├── auth-test/          # Auth smoke test page
│   │   ├── jwt-test/           # JWT token inspector
│   │   └── webhook-test/       # Webhook event monitor
│   ├── components/             # React components
│   │   └── auth/               # Auth-related components
│   ├── lib/                    # Utilities
│   │   ├── auth0.ts            # Auth0 helpers
│   │   └── webhook-utils.ts    # Webhook utilities
│   └── middleware.ts           # Route protection
│
├── backend/                    # FastAPI backend
│   ├── agent/                  # OpenAI tool-calling chat agent
│   ├── ai/                     # Embeddings, synthesis, model router
│   ├── api/v1/                 # 146+ REST endpoints
│   ├── auth/                   # JWT middleware, Auth0 JWKS
│   ├── briefs/                 # Intelligence brief generation
│   ├── compliance/             # GDPR data retention & export
│   ├── jobs/                   # Scheduled background jobs
│   ├── middleware/             # Feature gating, N+1 detection
│   ├── ml/                     # ONNX inference, entity resolution
│   ├── models/                 # SQLAlchemy ORM models
│   ├── repositories/           # Async DB access layer
│   ├── schemas/                # Pydantic request/response models
│   ├── services/               # Business logic
│   ├── signals/                # Signal acquisition pipeline
│   └── webhooks/               # Auth0 webhook handlers
│
├── pyproject.toml              # Python project config
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

---

## 🔐 Authentication Features

### Implemented

- ✅ **Auth0 Integration** — email/password, Google OAuth, GitHub OAuth, webhooks
- ✅ **FastAPI Backend** — 146+ endpoints, JWT middleware, CORS, rate limiting
- ✅ **Database Layer** — PostgreSQL (Azure), pgvector, Alembic migrations, async SQLAlchemy
- ✅ **Signal Intelligence Pipeline** — RSS fetchers, dedup, scoring, storage
- ✅ **AI Layer** — OpenAI chat agent, RAG, synthesis, embeddings
- ✅ **ML Layer** — ONNX inference, signal scoring, anomaly detection, entity resolution
- ✅ **Knowledge Graph** — Causal inference, regulatory intelligence, influence mapping
- ✅ **Feature Gating** — Tier-based access (Explorer → Growth → Mid-Market → Enterprise)
- ✅ **Pricing & Credits** — Credit transactions, trial management, beta lifecycle
- ✅ **Observability** — Prometheus metrics, structured logging, Sentry, OpenTelemetry
- ✅ **Compliance** — GDPR data retention, user data export
- ✅ **Background Workers** — RQ + Redis, scheduled jobs (signal acquisition, ML training)
- ✅ **CI/CD** — GitHub Actions (lint, typecheck, test, deploy to Azure Container Apps)

---

## 🧪 Testing

### Test Authentication Flow

1. **Auth Test Page** - http://localhost:3000/auth-test
   - Test login/logout
   - View user profile
   - Verify custom claims

2. **JWT Inspector** - http://localhost:3000/jwt-test
   - View decoded access token
   - View decoded ID token
   - Validate custom claims presence

3. **Webhook Monitor** - http://localhost:3000/webhook-test
   - View recent webhook events
   - Monitor event delivery
   - Test webhook endpoint

## 🔧 Development Workflow

### Frontend Development

```bash
cd frontend
npm run dev          # Start dev server
npm run build        # Build for production
npm run lint         # Run ESLint
```

### Backend Development

```bash
source .venv/bin/activate  # Activate virtualenv (Windows: .venv\Scripts\activate)
uvicorn backend.main:app --reload  # Start FastAPI server
python worker.py                   # Start background worker
pytest tests/                      # Run tests
ruff check backend/                # Lint Python code
```

### Webhook Testing

1. Start ngrok tunnel:
   ```bash
   ngrok http 3000
   ```

2. Configure Auth0 Log Stream with ngrok URL:
   ```
   https://<your-ngrok-url>.ngrok-free.app/api/webhooks/auth0
   ```

3. Monitor events at http://localhost:3000/webhook-test

This checkout does not bundle the older `docs/` tree referenced in some past
materials. Treat the codebase itself and the route surface as the current source
of truth for setup and implementation details.

---

## 📚 Documentation

### Code Documentation

- Auth utilities: [`frontend/lib/auth0.ts`](frontend/lib/auth0.ts)
- Webhook utilities: [`frontend/lib/webhook-utils.ts`](frontend/lib/webhook-utils.ts)

---

## 🏗️ Architecture

### Authentication Flow

```
User → Auth0 Universal Login → Authorization Code Flow →
→ Auth0 Action (Add Custom Claims) → JWT with Claims →
→ Next.js Session (httpOnly cookie) → Protected Routes
```

### Authorization Layers (Planned)

1. **Org-Level Roles**: Owner > Admin > Member > Viewer
2. **Resource-Level Ownership**: User owns their resources
3. **Feature Gates**: Plan-based access (Explorer/Growth/Mid-Market/Enterprise)

### Multi-Tenancy

- Organization-scoped data isolation
- `org_id` in every JWT token
- Database queries scoped to `org_id`
- No cross-org data leakage

---

## 🐛 Troubleshooting

### Authentication Issues

**Problem**: Login redirects to error page
- Check `AUTH0_CLIENT_ID` and `AUTH0_CLIENT_SECRET` in `.env.local`
- Verify callback URLs in Auth0 dashboard match `http://localhost:3000/api/auth/callback`
- Check Auth0 tenant domain is correct

**Problem**: Custom claims not in JWT
- Verify "Add Custom Claims" action is deployed
- Check action is in Login flow (between Start and Complete)
- Ensure test user has `app_metadata` set
- User must logout and login again after adding metadata

**Problem**: "Access Denied" error
- Check application is enabled for the connection (Database, Google, GitHub)
- Verify allowed origins in Auth0 match your domain

### Webhook Issues

**Problem**: Webhooks not received
- Verify ngrok is running and accessible
- Check Auth0 Log Stream URL matches ngrok URL
- Ensure webhook endpoint is running (`/api/webhooks/auth0`)
- Check Auth0 Stream Health tab for delivery errors

**Problem**: Signature verification fails
- Verify `AUTH0_WEBHOOK_SECRET` matches Auth0 Bearer token configuration
- Check signature header name (Authorization or x-auth0-signature)

### General Issues

**Problem**: TypeScript errors
```bash
cd frontend
npm run build  # Check for compilation errors
```

**Problem**: Missing dependencies
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

---

## 📋 Current Status

### Core Platform (Complete)

- ✅ Auth0 authentication + custom JWT claims
- ✅ FastAPI backend with 146+ endpoints
- ✅ PostgreSQL + pgvector + Redis + Neo4j data stores
- ✅ Signal intelligence pipeline
- ✅ AI chat agent + RAG synthesis
- ✅ ML inference (ONNX Runtime)
- ✅ Feature gating + pricing tiers
- ✅ Background workers (RQ)
- ✅ CI/CD pipeline (GitHub Actions → Azure Container Apps)
- ✅ Observability (Prometheus, Sentry, structured logs)

### Pre-Launch Checklist

- 📋 All pre-commit hooks green (in progress)
- 📋 Azure infrastructure provisioned (ACR, Container Apps, Key Vault)
- 📋 Production secrets set in GitHub environments
- 📋 Smoke tests passing against staging
- 📋 Domain + TLS configured

---

## 🤝 Contributing

### Code Style

**Frontend** (TypeScript/Next.js):
- ESLint configuration in `.eslintrc`
- Prettier for formatting
- Follow Next.js 14 app router conventions

**Backend** (Python):
- Ruff for linting
- Black for formatting (88 char line length)
- Type hints required

### Git Workflow

```bash
git checkout -b feature/your-feature-name
# Make changes
git commit -m "feat: add feature description"
git push origin feature/your-feature-name
# Create pull request
```

---

## 📄 License

[Add your license here]

---

## 🆘 Support

- **Documentation**: See the in-repo code and API surface for the current implementation
- **Issues**: [GitHub Issues](your-repo-url/issues)
- **Discussions**: [GitHub Discussions](your-repo-url/discussions)

---

**Last Updated**: February 2026
**Current Version**: Pre-launch (all core features implemented, CI/CD pipeline operational)
