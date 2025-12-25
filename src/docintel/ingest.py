from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import re
from pypdf import PdfReader

@dataclass(frozen=True)
class Document:
    doc_id: str
    source_path: str
    text: str

def normalize_text(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def read_text(path: Path) -> str:
    return normalize_text(path.read_text(encoding="utf-8", errors="ignore"))

def read_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    pages = []
    for p in reader.pages:
        try:
            pages.append(p.extract_text() or "")
        except Exception:
            pages.append("")
    return normalize_text("\n".join(pages))

def load_document(path: Path, doc_id: Optional[str] = None) -> Document:
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        txt = read_text(path)
    elif suffix == ".pdf":
        txt = read_pdf(path)
    else:
        raise ValueError(f"Unsupported file type: {suffix}")
    did = doc_id or path.name
    return Document(doc_id=did, source_path=str(path), text=txt)
