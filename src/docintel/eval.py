from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Callable

@dataclass(frozen=True)
class GoldenCase:
    schema: str
    doc_path: str
    must_have_any: Dict[str, List[str]]

@dataclass(frozen=True)
class CaseResult:
    schema: str
    doc_path: str
    passed: bool
    details: Dict[str, Any]

def load_golden(path: Path) -> List[GoldenCase]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [GoldenCase(schema=r["schema"], doc_path=r["doc_path"], must_have_any=r["must_have_any"]) for r in raw]

def run_eval(extract_fn: Callable[[str, Path], Dict[str, Any]], cases: List[GoldenCase]) -> List[CaseResult]:
    results: List[CaseResult] = []
    for c in cases:
        data = extract_fn(c.schema, Path(c.doc_path))
        ok = True
        field_details = {}
        for field, substrings in c.must_have_any.items():
            val = data.get(field)
            sval = "" if val is None else str(val).lower()
            found = [s for s in substrings if s.lower() in sval]
            field_details[field] = {"value": val, "found": found}
            if not found:
                ok = False
        results.append(CaseResult(schema=c.schema, doc_path=c.doc_path, passed=ok, details=field_details))
    return results
