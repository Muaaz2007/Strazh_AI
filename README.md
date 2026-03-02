# Strazh_AI (Monorepo)

This repo contains:

- `frontend/` Next.js web UI
- `backend/` FastAPI service that runs the AegisAI pipeline (`intelligence/`)

## Quick start (local)

### 1) Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

# Set your key (optional, but needed for live LLM calls)
# Windows PowerShell: $env:MISTRAL_API_KEY="..."
# macOS/Linux: export MISTRAL_API_KEY="..."

uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Health check: open `http://127.0.0.1:8000/`

### 2) Frontend

```bash
cd frontend
npm install
# or: npm ci
npm run dev
```

Open: `http://localhost:3000`

Set backend URL (optional): create `frontend/.env.local`

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

## API contract (frontend -> backend)

Frontend calls:

- `POST /audit` (recommended)

Request body:
```json
{
  "name": "My System",
  "domain": "employment",
  "description": "…",
  "intended_users": "HR managers",
  "outputs": "risk band + checklist",
  "deployment": "public web app",
  "data_types": "PII, resumes",
  "country": "DE"
}
```

Response is the final report used by the report page:
- `risk_band`, `prohibited`, `prohibition_reasons`, `deterministic_score`, `summary`,
  `threats`, `checklist`, `jurisdiction`, `retrieval_sources`, etc.

Advanced endpoint:
- `POST /assess` expects `{ "audit_request": {...}, "normalization_flags": {...} }`

## Docker (optional)

```bash
docker compose up --build
```

Frontend: `http://localhost:3000`  
Backend: `http://localhost:8000`
