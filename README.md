# Cogent - AI-Powered SaaS Platform


## 1. Architecture Overview

**Cogent** is an AI-powered market intelligence platform with a three-tier architecture:

| Layer | Technology | Role |
|-------|-----------|------|
| **Frontend** | Next.js 14 (App Router) + Tailwind + Auth0 SDK | SSR/CSR SPA, handles auth flow, renders dashboards |
| **Backend API** | FastAPI (async) + SQLAlchemy 2.0 + Pydantic v2 | REST API, JWT auth, business logic, AI orchestration |
| **Workers** | RQ (Redis Queue) + Python | Background jobs: signal acquisition, document analysis, ML training |
| **Data Stores** | PostgreSQL (Neon) + pgvector, Redis, Neo4j | Relational data, caching/queues, knowledge graph |




```
Routes (api/v1/) → Services (services/) → Repositories (repositories/) → Models (models/) → PostgreSQL
                 ↘ AI layer (ai/)       → OpenAI API
                 ↘ ML layer (ml/)       → ONNX Runtime (local inference)
                 ↘ Signals (signals/)   → External data sources (RSS, APIs)
```

**Key Subsystems:**

- **Signal Intelligence Pipeline**: Fetchers → Processors → Dedup → Scoring → Storage
- **Causal Knowledge Graph**: Entity resolution → Relationship mapping → Causal inference (Neo4j + pgvector)
- **Intelligence Moat**: Feedback loops → Prediction backtesting → Replicability testing → Moat metrics
- **Chat Agent**: OpenAI-powered chat with tool calling, RAG over signals/briefs
- **Pricing & Feature Gating**: Tier-based access (Free → Starter → Professional → Enterprise)

---

## 2. System Flow Diagram

```
User Browser
    │
    ├─── Auth0 Login ──→ Auth0 ──→ JWT issued
    │
    ▼
Next.js Frontend (localhost:3000)
    │ fetch('/api/v1/...')        ← NO proxy configured (CORS issue)
    ▼
FastAPI Backend (localhost:8000)
    │
    ├── CORS Middleware (outermost)
    ├── RequestID Middleware
    ├── Metrics Middleware (Prometheus)
    ├── JWT Middleware (Auth0 JWKS validation)
    │          │
    │          ├── Token valid → request.state.token_payload
    │          └── Token invalid → 401
    │
    ├── Rate Limiter (slowapi) ← BROKEN: in-memory, never reads user ID
    │
    ▼
API v1 Router (146 endpoints)
    │
    ├── get_current_user() dependency → DB lookup → AuthContext
    │          │
    │          └── Auto-creates user if not found ← BUG: garbage email
    │
    ├── Service Layer ← Some routes bypass this (direct DB access)
    │      │
    │      ├── OpenAI API (chat, synthesis, embeddings)
    │      ├── ONNX Runtime (scoring, anomaly detection)
    │      └── Neo4j (causal graph queries)
    │
    ├── Repository Layer → SQLAlchemy AsyncSession → PostgreSQL (Neon)
    │
    └── Background Jobs → Redis Queue → RQ Worker ← BROKEN: won't start
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

   Follow the complete setup guide: [`docs/auth/auth0-setup.md`](docs/auth/auth0-setup.md)

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

   Backend (coming in Stage 1.5):
   ```bash
   # Not yet implemented
   cd backend
   uvicorn main:app --reload
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
├── docs/                       # Documentation
│   ├── auth/                   # Auth0 setup guides
│   │   ├── auth0-setup.md      # Complete Auth0 configuration
│   │   ├── webhooks-setup.md   # Webhook configuration with ngrok
│   │   ├── stage-1-validation.md # QA checklist for Stage 1
│   │   └── auth0-action-custom-claims.js # Custom claims action
│   └── auth-implementation-plan.md # Full auth roadmap
│
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
├── backend/                    # FastAPI backend (coming in Stage 1.5)
│   └── (not yet implemented)
│
├── pyproject.toml              # Python project config
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

---

## 🔐 Authentication Features

### Currently Implemented (Stage 1)

- ✅ **Auth0 Integration**
  - Email/password authentication
  - Google OAuth
  - GitHub OAuth
  - Email verification

- ✅ **Custom JWT Claims**
  - `org_id` - Organization ID
  - `roles` - User roles array
  - `plan` - Subscription tier

- ✅ **Protected Routes**
  - Middleware-based route protection
  - Role-based access control examples
  - Token verification on every request

- ✅ **Webhook Events**
  - User signup tracking
  - Login event logging
  - Failed authentication monitoring
  - Signature verification

### Coming Soon (Stage 1.5)

- ⏳ **Backend Integration**
  - FastAPI JWT middleware
  - Database user sync
  - Authorization guards
  - Query scoping for multi-tenancy

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

### Run Validation Checklist

Complete QA checklist: [`docs/auth/stage-1-validation.md`](docs/auth/stage-1-validation.md)

---

## 🔧 Development Workflow

### Frontend Development

```bash
cd frontend
npm run dev          # Start dev server
npm run build        # Build for production
npm run lint         # Run ESLint
```

### Backend Development (Coming Soon)

```bash
source .venv/bin/activate  # Activate virtualenv
cd backend
uvicorn main:app --reload  # Start FastAPI server
pytest                      # Run tests
ruff check .                # Lint Python code
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

Full guide: [`docs/auth/webhooks-setup.md`](docs/auth/webhooks-setup.md)

---

## 📚 Documentation

### Authentication Setup

- [Auth0 Setup Guide](docs/auth/auth0-setup.md) - Complete tenant configuration
- [Webhooks Setup](docs/auth/webhooks-setup.md) - Webhook configuration with ngrok
- [Stage 1 Validation](docs/auth/stage-1-validation.md) - QA checklist
- [Auth Implementation Plan](docs/auth-implementation-plan.md) - Full roadmap

### Code Documentation

- Custom claims action: [`docs/auth/auth0-action-custom-claims.js`](docs/auth/auth0-action-custom-claims.js)
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
3. **Feature Flags**: Plan-based access (Free/Pro/Enterprise)

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

### Completed (Stage 1)

- ✅ Phase 1.1: Auth0 tenant configuration
- ✅ Phase 1.2: Authentication methods (email, Google, GitHub)
- ✅ Phase 1.3: Custom JWT claims
- ✅ Phase 1.4: Webhook event handling

### In Progress (Stage 1.5)

- ⏳ Backend Integration (FastAPI)
- ⏳ Database schema design
- ⏳ JWT middleware for backend
- ⏳ Authorization guards

### Next Up (Stage 2-7)

- 📋 Data & domain modeling
- 📋 Role-based access control
- 📋 Feature flags
- 📋 Testing & validation
- 📋 Production deployment

See full roadmap: [`docs/auth-implementation-plan.md`](docs/auth-implementation-plan.md)

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

- **Documentation**: See [`docs/`](docs/) folder
- **Issues**: [GitHub Issues](your-repo-url/issues)
- **Discussions**: [GitHub Discussions](your-repo-url/discussions)

---

**Last Updated**: January 30, 2026
**Current Version**: Stage 1 Complete, Stage 1.5 In Progress

# Deployment Test
