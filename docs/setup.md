# Setup Guide

Development setup instructions for the Conversational Survey Engine.

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.11+ | Backend runtime |
| Node.js | 18+ | Frontend runtime |
| npm | 9+ | Frontend package manager |
| Git | any | Version control |

---

## 1. Clone the Repository

```bash
git clone https://github.com/your-org/conversational-survey-engine.git
cd conversational-survey-engine
```

---

## 2. Backend Setup

### Create virtual environment

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### Install dependencies

```bash
pip install -e ".[dev]"
```

This installs the project and all runtime + dev dependencies defined in `pyproject.toml`:
- FastAPI, Uvicorn, SQLAlchemy, aiosqlite
- LiteLLM, OpenAI Agent SDK
- Pydantic Settings, Alembic, httpx
- pytest, pytest-asyncio (dev)

### Configure environment variables

Create a `.env` file in the `backend/` directory:

```env
GEMINI_API_KEY=your-gemini-api-key-here
DATABASE_URL=sqlite+aiosqlite:///./data/cse.db
CORS_ORIGINS=["http://localhost:5173"]
LOG_LEVEL=info
```

> **Note:** You need a [Google Gemini API key](https://aistudio.google.com/apikey) for question generation and embedding-based validation.

### Run database migrations (optional)

The application auto-creates tables on startup, but you can also use Alembic:

```bash
alembic upgrade head
```

### Start the backend server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

---

## 3. Frontend Setup

### Install dependencies

```bash
cd frontend
npm install
```

### Configure environment (optional)

Create a `.env` file in the `frontend/` directory if the backend runs on a non-default URL:

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

If omitted, the frontend defaults to `/api/v1` (works with a reverse proxy or Vite proxy config).

### Start the dev server

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
- `tests/test_validator.py` — Validator logic tests

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

> Requires both backend and frontend running.

---

## 5. Environment Variables Reference

### Backend (`backend/.env`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GEMINI_API_KEY` | Yes | `""` | Google Gemini API key for LLM and embeddings |
| `DATABASE_URL` | No | `sqlite+aiosqlite:///./data/cse.db` | Async SQLAlchemy database URL |
| `CORS_ORIGINS` | No | `["http://localhost:5173"]` | JSON array of allowed CORS origins |
| `LOG_LEVEL` | No | `info` | Logging level (`debug`, `info`, `warning`, `error`) |

### Frontend (`frontend/.env`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VITE_API_BASE_URL` | No | `/api/v1` | Backend API base URL |

---

## Project Structure

```
conversational-survey-engine/
├── backend/                  # FastAPI backend
│   ├── app/
│   │   ├── main.py           # Application entry point
│   │   ├── agents/           # AI agent (generator + validator)
│   │   ├── api/              # Route handlers
│   │   ├── core/             # Config, DB, dependencies
│   │   ├── models/           # SQLAlchemy ORM models
│   │   ├── repositories/     # Data access layer
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   └── services/         # Business logic
│   ├── tests/                # Backend tests
│   ├── alembic/              # DB migrations
│   └── pyproject.toml        # Python project config
├── frontend/                 # React frontend
│   ├── src/
│   │   ├── components/       # Reusable UI components
│   │   ├── hooks/            # Custom React hooks
│   │   ├── pages/            # Page-level components
│   │   ├── services/         # API client
│   │   └── types/            # TypeScript type definitions
│   └── package.json
├── database/                 # SQL schema and seed data
├── docs/                     # Documentation
├── shared/                   # Project plans and metadata
└── tests/e2e/                # End-to-end tests
```
