from __future__ import annotations
from pathlib import Path
import json
import typer
from rich import print
from openai import OpenAI

from docintel.config import get_settings
from docintel.logging import configure_logging
from docintel.tracing import configure_tracing, TracingConfig
from docintel.cache import DiskCache
from docintel.ingest import load_document
from docintel.schemas import SCHEMA_REGISTRY
from docintel.llm import LLMClient
from docintel.extractor import SchemaExtractor
from docintel.eval import load_golden, run_eval

app = typer.Typer(add_completion=False)

def build_sync_extractor():
    s = get_settings()
    configure_logging()
    configure_tracing(TracingConfig(service_name=s.service_name, otlp_endpoint=s.otlp_endpoint))
    cache = None
    if s.enable_cache:
        s.cache_dir.mkdir(parents=True, exist_ok=True)
        cache = DiskCache(str(s.cache_dir))
    client = OpenAI()
    llm = LLMClient(client, s.llm_model, cache, s.llm_cache_ttl_s, s.max_retries, s.request_timeout_s)
    extractor = SchemaExtractor(llm, s)
    return s, extractor

@app.command()
def extract(path: str, schema: str = typer.Option("contract")):
    p = Path(path)
    s, ext = build_sync_extractor()
    doc = load_document(p)
    model = SCHEMA_REGISTRY.get(schema)
    if not model:
        raise typer.BadParameter(f"Unknown schema: {schema}")
    res = ext.extract_sync(schema, model, doc.doc_id, doc.text)
    print(json.dumps(res.data, indent=2, ensure_ascii=False))

@app.command()
def eval(golden_path: str = "eval/golden.json"):
    s, ext = build_sync_extractor()
    cases = load_golden(Path(golden_path))

    def _extract(schema_name: str, doc_path: Path):
        doc = load_document(doc_path)
        model = SCHEMA_REGISTRY[schema_name]
        res = ext.extract_sync(schema_name, model, doc.doc_id, doc.text)
        return res.data

    results = run_eval(_extract, cases)
    passed = sum(1 for r in results if r.passed)
    print(f"[bold]{passed}/{len(results)}[/bold] cases passed")
    for r in results:
        status = "[green]PASS[/green]" if r.passed else "[red]FAIL[/red]"
        print(f"{status} {r.schema} {r.doc_path}")

if __name__ == "__main__":
    app()
