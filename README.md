# LLM Document Intelligence (Production-lean)

A production-oriented reference implementation for **document intelligence** using LLMs:
- Ingest PDFs / text
- Normalize and chunk
- Extract **structured fields** using a strict JSON schema
- Validate + post-process
- Provide an API (FastAPI) and CLI
- Add caching, retries, tracing, rate limiting, and token/cost accounting

This repo focuses on **deployable engineering patterns**, not notebooks.

## Features
- PDF and text ingestion (`.pdf`, `.txt`, `.md`)
- Deterministic chunking + metadata
- Schema-driven extraction with **Pydantic**
- Automatic JSON repair + validation loop
- Disk caching (requests + extraction outputs)
- Retries with exponential backoff/jitter
- OpenTelemetry tracing (console by default; OTLP supported)
- Rate limiting (sync + async)
- FastAPI service + Dockerfile
- Golden-set evaluation + pytest tests

## Quickstart

### Install
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### Configure
```bash
export OPENAI_API_KEY="..."
export DI_DATA_DIR="data/samples"
```

### CLI
```bash
python -m docintel.cli extract data/samples/sample_contract.txt --schema contract
```

### API
```bash
uvicorn docintel.api:app --reload
```

Endpoints:
- `POST /extract` (single doc)
- `POST /extract/batch` (multiple docs)
- `GET /health`

### Docker
```bash
docker build -t docintel .
docker run -p 8000:8000 -e OPENAI_API_KEY=... docintel
```

## Schemas
Included example schemas:
- `contract` (counterparty, dates, obligations)
- `invoice` (vendor, invoice number, totals)

Add your own schemas under `src/docintel/schemas.py`.

## Disclaimer
Reference architecture for educational and implementation guidance.
