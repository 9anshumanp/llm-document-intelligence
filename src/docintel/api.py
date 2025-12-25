from __future__ import annotations
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pathlib import Path
import base64
from typing import List, Optional

from openai import AsyncOpenAI
from aiolimiter import AsyncLimiter

from docintel.config import get_settings
from docintel.logging import configure_logging
from docintel.tracing import configure_tracing, TracingConfig
from docintel.cache import DiskCache
from docintel.ingest import load_document, Document, normalize_text
from docintel.schemas import SCHEMA_REGISTRY
from docintel.llm import AsyncLLMClient
from docintel.extractor import AsyncSchemaExtractor

app = FastAPI(title="Document Intelligence API", version="0.2.0")

class ExtractRequest(BaseModel):
    schema: str
    raw_text: Optional[str] = None
    base64_file: Optional[str] = None
    filename: Optional[str] = None
    doc_id: Optional[str] = None

class ExtractResponse(BaseModel):
    schema: str
    doc_id: str
    data: dict
    confidence: float
    used_chunks: int
    prompt_tokens_est: int
    completion_tokens_est: int
    total_tokens_est: int
    cost_est_usd: float

class BatchRequest(BaseModel):
    schema: str
    items: List[ExtractRequest]

class BatchResponse(BaseModel):
    schema: str
    results: List[ExtractResponse]

_state = {}

def _init_once():
    if _state:
        return
    s = get_settings()
    configure_logging()
    configure_tracing(TracingConfig(service_name=s.service_name, otlp_endpoint=s.otlp_endpoint))

    cache = None
    if s.enable_cache:
        s.cache_dir.mkdir(parents=True, exist_ok=True)
        cache = DiskCache(str(s.cache_dir))

    limiter = AsyncLimiter(max_rate=s.max_rps, time_period=1) if s.max_rps > 0 else None

    aclient = AsyncOpenAI()
    allm = AsyncLLMClient(aclient, s.llm_model, cache, s.llm_cache_ttl_s, s.max_retries, s.request_timeout_s, limiter=limiter)
    aext = AsyncSchemaExtractor(allm, s)

    _state.update({"s": s, "cache": cache, "aext": aext})

def _document_from_request(req: ExtractRequest) -> Document:
    if req.raw_text:
        did = req.doc_id or "inline"
        return Document(doc_id=did, source_path="inline", text=normalize_text(req.raw_text))
    if req.base64_file and req.filename:
        s = _state["s"]
        tmp_dir = s.cache_dir / "_uploads"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        data = base64.b64decode(req.base64_file.encode("utf-8"))
        p = tmp_dir / req.filename
        p.write_bytes(data)
        return load_document(p, doc_id=req.doc_id or req.filename)
    raise ValueError("Provide either raw_text or base64_file + filename")

@app.get("/health")
def health():
    _init_once()
    return {"status": "ok"}

@app.post("/extract", response_model=ExtractResponse)
async def extract(req: ExtractRequest):
    _init_once()
    schema_name = req.schema
    model = SCHEMA_REGISTRY.get(schema_name)
    if not model:
        raise HTTPException(status_code=400, detail=f"Unknown schema: {schema_name}")

    try:
        doc = _document_from_request(req)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    aext: AsyncSchemaExtractor = _state["aext"]
    res, usage, cost = await aext.extract(schema_name, model, doc.doc_id, doc.text)

    return ExtractResponse(
        schema=schema_name,
        doc_id=res.doc_id,
        data=res.data,
        confidence=res.confidence,
        used_chunks=res.used_chunks,
        prompt_tokens_est=usage.prompt_tokens,
        completion_tokens_est=usage.completion_tokens,
        total_tokens_est=usage.total_tokens,
        cost_est_usd=cost,
    )

@app.post("/extract/batch", response_model=BatchResponse)
async def extract_batch(req: BatchRequest):
    _init_once()
    schema_name = req.schema
    model = SCHEMA_REGISTRY.get(schema_name)
    if not model:
        raise HTTPException(status_code=400, detail=f"Unknown schema: {schema_name}")

    aext: AsyncSchemaExtractor = _state["aext"]
    results = []
    for item in req.items:
        item.schema = schema_name
        try:
            doc = _document_from_request(item)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
        res, usage, cost = await aext.extract(schema_name, model, doc.doc_id, doc.text)
        results.append(ExtractResponse(
            schema=schema_name,
            doc_id=res.doc_id,
            data=res.data,
            confidence=res.confidence,
            used_chunks=res.used_chunks,
            prompt_tokens_est=usage.prompt_tokens,
            completion_tokens_est=usage.completion_tokens,
            total_tokens_est=usage.total_tokens,
            cost_est_usd=cost,
        ))
    return BatchResponse(schema=schema_name, results=results)
