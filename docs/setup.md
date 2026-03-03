# Setup Guide

Development setup instructions for the Conversational Survey Engine.

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.11+ | Backend + LLM Service runtime |
| Node.js | 18+ | Frontend runtime |
| npm | 9+ | Frontend package manager |
| Docker | 24+ | Containerization (for Docker Compose setup) |
| Docker Compose | v2+ | Multi-service orchestration |
| Git | any | Version control |

> **Docker-only setup:** If using Docker Compose, you only need Docker + Docker Compose installed. Python and Node.js are not required on the host.

---

## Option A: Docker Compose (Recommended)

The fastest way to run the full stack locally.

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/conversational-survey-engine.git
cd conversational-survey-engine
```

### 2. Configure Environment

Create a `.env` file at the workspace root:

```env
# Required
GEMINI_API_KEY=your-gemini-api-key-here

# Optional overrides (defaults work for local dev)
DATABASE_URL=sqlite+aiosqlite:///./data/cse.db
GEMINI_MODEL=vertex_ai/gemini-2.0-flash
GEMINI_VALIDATOR_MODEL=gemini/gemini-2.0-flash
CORS_ORIGINS=["http://localhost","http://localhost:80"]
LOG_LEVEL=info

# Google service account credentials file (for Vertex AI models)
GOOGLE_CREDENTIALS_FILE=./gen-lang-client-0575690477-7f0434f5aa44.json
```

### 3. Start All Services

```bash
docker compose up --build
```

This starts three services:

| Service | URL | Description |
|---------|-----|-------------|
| **Frontend** | http://localhost | React SPA + nginx reverse proxy |
| **Backend** | http://localhost:8000 | FastAPI REST API |
| **LLM Service** | http://localhost:8001 | AI question generation |

The frontend proxies `/api/*` requests to the backend automatically.

### 4. Stop Services

```bash
docker compose down
```

### Development Mode with Hot Reload

For active development, use the dev override to enable hot reload (code changes apply without rebuild):

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

This mounts source directories as volumes:
- `./backend/app` → backend container
- `./llm-service/app` → LLM service container

Both backend and LLM service run with `uvicorn --reload`.

---

## Option B: Traditional Setup (Without Docker)

Run each service directly on the host for maximum debugging flexibility.

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/conversational-survey-engine.git
cd conversational-survey-engine
```

### 2. Backend Setup

#### Create virtual environment

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

#### Install dependencies

```bash
pip install -e ".[dev]"
```

This installs all runtime + dev dependencies defined in `pyproject.toml`:
- FastAPI, Uvicorn, SQLAlchemy, aiosqlite, asyncpg
- httpx (HTTP client for LLM service calls)
- Pydantic Settings, Alembic
- pytest, pytest-asyncio (dev)

#### Configure environment variables

Create a `.env` file in the `backend/` directory:

```env
GEMINI_API_KEY=your-gemini-api-key-here
DATABASE_URL=sqlite+aiosqlite:///./data/cse.db
LLM_SERVICE_URL=http://localhost:8001
CORS_ORIGINS=["http://localhost:5173"]
LOG_LEVEL=info
```

> **Note:** You need a [Google Gemini API key](https://aistudio.google.com/apikey) for question generation and embedding-based validation.

#### Run database migrations (optional)

The application auto-creates tables on startup, but you can also use Alembic:

```bash
alembic upgrade head
```

#### Start the backend server

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

> **Important:** Always start uvicorn from the `backend/` directory to avoid path resolution issues with SQLite.

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

### 3. LLM Service Setup

#### Install dependencies

In a separate terminal:

```bash
cd llm-service
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -e .
```

#### Configure environment variables

Create a `.env` file in the `llm-service/` directory:

```env
GEMINI_API_KEY=your-gemini-api-key-here
GEMINI_MODEL=vertex_ai/gemini-2.0-flash
GEMINI_VALIDATOR_MODEL=gemini/gemini-2.0-flash
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json
LOG_LEVEL=info
```

#### Start the LLM service

```bash
cd llm-service
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

The LLM service will be available at `http://localhost:8001`. Health check at `http://localhost:8001/health`.

### 4. Frontend Setup

#### Install dependencies

```bash
cd frontend
npm install
```

#### Configure environment (optional)

Create a `.env` file in the `frontend/` directory if the backend runs on a non-default URL:

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

If omitted, the frontend defaults to `/api/v1` (works with a reverse proxy or Vite proxy config).

#### Start the dev server

```bash
npm run dev
```

The frontend will be available at `http://localhost:5173`.

---

## 4. Running Tests

### Backend tests

```bash
cd backend
python -m pytest tests/ -v
```

Key test files:
- `tests/test_admin_api.py` — Admin CRUD endpoints
- `tests/test_participant_api.py` — Session and response endpoints
- `tests/test_services.py` — Service layer logic
- `tests/test_generator_agent.py` — Generator agent tests
- `tests/test_guardrails.py` — Answer guardrails tests
- `tests/test_validator.py` — Validator logic tests
- `tests/test_preset_questions.py` — Preset question generation tests

> Backend tests use in-memory SQLite and mock the LLM client. No running LLM service or database is required.

### Frontend tests

```bash
cd frontend
npm test
```

### End-to-end tests

```bash
cd tests/e2e
python -m pytest test_full_flow.py -v
```

> Requires both backend and LLM service running.

---

## 5. Environment Variables Reference

### Backend

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | No | `sqlite+aiosqlite:///./data/cse.db` | Async SQLAlchemy database URL. Use `postgresql+asyncpg://...` for NeonDB |
| `LLM_SERVICE_URL` | No | `http://localhost:8001` | URL of the LLM microservice |
| `CORS_ORIGINS` | No | `["http://localhost:5173"]` | JSON array of allowed CORS origins |
| `LOG_LEVEL` | No | `info` | Logging level (`debug`, `info`, `warning`, `error`) |
| `GOOGLE_APPLICATION_CREDENTIALS` | No | — | Path to GCP service account JSON (for Vertex AI, if used in backend) |

### LLM Service

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GEMINI_API_KEY` | Yes* | `""` | Google Gemini API key (for `gemini/` model prefix) |
| `GEMINI_MODEL` | No | `vertex_ai/gemini-2.0-flash` | LLM model for question generation |
| `GEMINI_VALIDATOR_MODEL` | No | `gemini/gemini-2.0-flash` | LLM model for validation |
| `GOOGLE_APPLICATION_CREDENTIALS` | Yes* | — | Path to GCP service account JSON (for `vertex_ai/` model prefix) |
| `GOOGLE_API_KEY` | No | — | Alternative Google API key |
| `LOG_LEVEL` | No | `info` | Logging level |

> \* Either `GEMINI_API_KEY` or `GOOGLE_APPLICATION_CREDENTIALS` is required depending on the model prefix used (`gemini/` vs `vertex_ai/`).

### Frontend

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VITE_API_BASE_URL` | No | `/api/v1` | Backend API base URL |

### Docker Compose (root `.env`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GEMINI_API_KEY` | Yes | — | Passed to LLM service container |
| `DATABASE_URL` | No | `sqlite+aiosqlite:///./data/cse.db` | Backend database URL |
| `CORS_ORIGINS` | No | `["http://localhost","http://localhost:80"]` | Backend CORS origins |
| `LOG_LEVEL` | No | `info` | Log level for all services |
| `GOOGLE_CREDENTIALS_FILE` | No | `./gen-lang-client-...json` | Host path to GCP service account file (mounted into LLM service) |

---

## Project Structure

```
conversational-survey-engine/
├── backend/                  # FastAPI backend (API + business logic + DB)
│   ├── app/
│   │   ├── main.py           # Application entry point
│   │   ├── agents/           # Preserved agent code (reference/fallback)
│   │   ├── api/              # Route handlers
│   │   ├── clients/          # HTTP clients (llm_client.py)
│   │   ├── core/             # Config, DB, dependencies
│   │   ├── models/           # SQLAlchemy ORM models
│   │   ├── repositories/     # Data access layer
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   └── services/         # Business logic
│   ├── tests/                # Backend tests
│   ├── alembic/              # DB migrations
│   ├── Dockerfile            # Multi-stage Docker build
│   └── pyproject.toml        # Python project config
├── llm-service/              # LLM microservice (AI operations)
│   ├── app/
│   │   ├── main.py           # FastAPI entry point
│   │   ├── routes.py         # HTTP endpoints
│   │   ├── schemas.py        # Pydantic models
│   │   ├── config.py         # Settings
│   │   └── agents/           # Generator, validator, guardrails
│   ├── Dockerfile            # Multi-stage Docker build
│   └── pyproject.toml        # Python project config
├── frontend/                 # React frontend
│   ├── src/
│   │   ├── components/       # Reusable UI components
│   │   ├── hooks/            # Custom React hooks
│   │   ├── pages/            # Page-level components
│   │   ├── services/         # API client
│   │   └── types/            # TypeScript type definitions
│   ├── nginx.conf            # nginx config (reverse proxy + SPA)
│   ├── Dockerfile            # Multi-stage Docker build
│   └── package.json
├── k8s/                      # Kubernetes manifests
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── secrets.yaml
│   ├── migration-job.yaml
│   ├── backend-deployment.yaml
│   ├── backend-service.yaml
│   ├── llm-service-deployment.yaml
│   ├── llm-service-service.yaml
│   ├── frontend-deployment.yaml
│   └── frontend-service.yaml
├── database/                 # SQL schema and seed data
├── docs/                     # Documentation
├── docker-compose.yml        # Production-like local setup
├── docker-compose.dev.yml    # Dev overrides (hot reload)
├── deploy.ps1                # K8s deployment script
├── shared/                   # Project plans and metadata
└── tests/e2e/                # End-to-end tests
```
