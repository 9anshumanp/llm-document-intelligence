from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Type
import logging

from pydantic import BaseModel

from docintel.chunking import build_chunks
from docintel.postprocess import extract_json_object, coerce_common_fields
from docintel.prompts import build_extraction_messages
from docintel.tracing import get_tracer

log = logging.getLogger("docintel.extractor")
tracer = get_tracer("docintel.extractor")

@dataclass(frozen=True)
class ExtractionResult:
    schema: str
    doc_id: str
    data: Dict[str, Any]
    confidence: float
    used_chunks: int

def _validate(schema_model: Type[BaseModel], obj: Dict[str, Any]) -> Dict[str, Any]:
    obj = coerce_common_fields(obj)
    model = schema_model.model_validate(obj)
    return model.model_dump()

class SchemaExtractor:
    def __init__(self, llm_client, settings):
        self._llm = llm_client
        self._s = settings

    def extract_sync(self, schema_name: str, schema_model: Type[BaseModel], doc_id: str, text: str) -> ExtractionResult:
        chunks = build_chunks(doc_id, text, self._s.chunk_size, self._s.chunk_overlap)
        used = min(len(chunks), 6)
        selected = chunks[:used]
        payload_text = "\n\n".join([f"[chunk {c.chunk_id}] {c.text}" for c in selected])

        with tracer.start_as_current_span("extract_sync") as span:
            span.set_attribute("schema", schema_name)
            span.set_attribute("doc_id", doc_id)
            span.set_attribute("chunks_used", used)

            messages = build_extraction_messages(schema_model, payload_text, doc_id, chunk_hint="Chunks are labeled. Use them to ground extracted facts.")
            raw = self._llm.complete(messages)

            try:
                obj = extract_json_object(raw)
                data = _validate(schema_model, obj)
                return ExtractionResult(schema=schema_name, doc_id=doc_id, data=data, confidence=0.85, used_chunks=used)
            except Exception:
                log.warning("Invalid JSON; requesting corrected output", extra={"component":"extractor","event":"repair","doc_id":doc_id,"schema":schema_name})
                fix_messages = messages + [{"role":"user","content":"Your previous output was invalid. Return ONLY corrected JSON matching the schema."}]
                raw2 = self._llm.complete(fix_messages)
                obj2 = extract_json_object(raw2)
                data2 = _validate(schema_model, obj2)
                return ExtractionResult(schema=schema_name, doc_id=doc_id, data=data2, confidence=0.75, used_chunks=used)

class AsyncSchemaExtractor:
    def __init__(self, async_llm_client, settings):
        self._llm = async_llm_client
        self._s = settings

    async def extract(self, schema_name: str, schema_model: Type[BaseModel], doc_id: str, text: str):
        chunks = build_chunks(doc_id, text, self._s.chunk_size, self._s.chunk_overlap)
        used = min(len(chunks), 6)
        selected = chunks[:used]
        payload_text = "\n\n".join([f"[chunk {c.chunk_id}] {c.text}" for c in selected])

        with tracer.start_as_current_span("extract_async") as span:
            span.set_attribute("schema", schema_name)
            span.set_attribute("doc_id", doc_id)
            span.set_attribute("chunks_used", used)

            messages = build_extraction_messages(schema_model, payload_text, doc_id, chunk_hint="Chunks are labeled. Use them to ground extracted facts.")
            raw, usage, cost = await self._llm.complete(messages)

            try:
                obj = extract_json_object(raw)
                data = _validate(schema_model, obj)
                res = ExtractionResult(schema=schema_name, doc_id=doc_id, data=data, confidence=0.85, used_chunks=used)
                return res, usage, cost
            except Exception:
                fix_messages = messages + [{"role":"user","content":"Your previous output was invalid. Return ONLY corrected JSON matching the schema."}]
                raw2, usage2, cost2 = await self._llm.complete(fix_messages)
                obj2 = extract_json_object(raw2)
                data2 = _validate(schema_model, obj2)
                res2 = ExtractionResult(schema=schema_name, doc_id=doc_id, data=data2, confidence=0.75, used_chunks=used)
                usage2.prompt_tokens += usage.prompt_tokens
                usage2.completion_tokens += usage.completion_tokens
                return res2, usage2, cost + cost2
