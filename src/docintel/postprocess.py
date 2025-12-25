from __future__ import annotations
import json
import re
from typing import Any, Dict

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)

def extract_json_object(text: str) -> Dict[str, Any]:
    m = _JSON_BLOCK_RE.search(text)
    if not m:
        raise ValueError("No JSON object found in LLM output.")
    candidate = m.group(0)
    candidate = re.sub(r",\s*([}\]])", r"\1", candidate)
    return json.loads(candidate)

def coerce_common_fields(obj: Dict[str, Any]) -> Dict[str, Any]:
    if "total_amount" in obj and isinstance(obj.get("total_amount"), str):
        try:
            obj["total_amount"] = float(re.sub(r"[^0-9.\-]", "", obj["total_amount"]))
        except Exception:
            pass
    if "tax_amount" in obj and isinstance(obj.get("tax_amount"), str):
        try:
            obj["tax_amount"] = float(re.sub(r"[^0-9.\-]", "", obj["tax_amount"]))
        except Exception:
            pass
    return obj
