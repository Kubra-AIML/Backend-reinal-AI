# RetinaGuide XAI: Backend API

Backend service for the RetinaGuide XAI project: API contract, persistence, upload safety, review trail and evidence serving.

> **STUB MODE.** This backend currently returns **synthetic example results**. No model is run and no image is analysed. Nothing here is clinically validated. A clinician decides.

## Quick start

### Windows (PowerShell), one command

```powershell
cd backend
.\run.ps1
```

This creates a virtual environment, installs dependencies, copies `.env.example` to `.env` if needed, applies the database migration and starts the API on port 8000. Then open http://localhost:8000/docs.

### Linux, macOS or Codespaces

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m alembic upgrade head
uvicorn app.main:app --reload
```

## Configuration (`.env`)

| Variable | Default | Meaning |
|---|---|---|
| `ENGINE_MODE` | `stub` | `stub`, `cache` or `matlab`. Only `stub` exists today. |
| `DATABASE_URL` | `sqlite:///./retinaguide.db` | Database connection |
| `MAX_UPLOAD_MB` | `10` | Upload size limit |
| `REFERABLE_THRESHOLD` | `0.5` | Threshold published by `/api/meta` |
| `PRODUCT_NAME` | `RetinaGuide XAI` | Display name |
| `CLASSIFIER_VERSION`, `QUALITY_GATE_VERSION`, `PREPROCESS_SPEC_VERSION` | `stub-...-0.0` | Version placeholders until the model registry is available |

## Endpoints

| Method and path | Purpose |
|---|---|
| `GET /api/health` | API, database and engine status |
| `GET /api/meta` | Product metadata, thresholds, policy and limitations text |
| `POST /api/cases` | Upload a JPEG or PNG and create a case (supports `Idempotency-Key`) |
| `GET /api/cases` | Paged case list, newest first |
| `GET /api/cases/{id or case_ref}` | Case detail with reviews |
| `POST /api/cases/{id or case_ref}/reviews` | Add a review (always a new record) |
| `GET /api/reason-codes` | Reason codes (placeholder list) |
| `GET /api/evidence`, `GET /api/evidence/{name}` | Evidence JSON files (404 until provided) |

Interactive docs are at `/docs`. The exported contract is `contracts/openapi.json`, with JSON Schemas beside it.

## Behaviour to know about

- **Quality-first:** unusable or non-fundus results never contain a grade (enforced by the schema).
- **Every result states its engine** (`stub`, `cache` or `matlab`). Stub output carries a notice saying it is not live inference.
- **Upload safety:** size limit, file type checked by signature (not extension), SHA-256, duplicate warning. The image bytes are not stored.
- **Idempotency:** repeating a request with the same `Idempotency-Key` returns the original case (HTTP 200, `Idempotent-Replay: true`). The same key with a different file returns 409.
- **Review trail:** a review is a new record. The original prediction is never overwritten.
- **Audit log:** append-only, enforced in application code and by database triggers.
- **Scores are uncalibrated** unless a result says otherwise.

## Tests

```bash
cd backend
python -m pytest -q
```

CI runs the stub-mode tests on Linux and Windows for every pull request (`.github/workflows/ci.yml`).

### Regenerating contract files

After changing a schema or an endpoint:

```bash
python scripts/generate_contract_files.py   # fixtures and JSON Schemas
python scripts/export_openapi.py            # contracts/openapi.json
```

A test fails if these files are stale.

## Known limitations

- Stub engine only. The MATLAB model is not connected and nothing here is a real prediction.
- No authentication. The `reviewer` field is self-declared text.
- Review decisions, reason codes and the referable definition (grades 2 to 4) are placeholders pending agreement with the project lead.
- Case list is not yet filterable by queue lane (needs the agreed policy file).
- SQLite only. Not hardened for production, and no rate limiting yet.
- Image and heatmap file serving is not implemented. No artifact files exist yet.

## Demo fallback

Stub mode needs no model, MATLAB or network, so the demo can always run. Replay of precomputed outputs (keyed by image SHA-256) is **planned, not built**. When it exists, replayed results will be labelled `cache`, never as live inference.