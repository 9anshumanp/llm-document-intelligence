from __future__ import annotations
from dataclasses import dataclass
from typing import List
import regex as re

@dataclass(frozen=True)
class Chunk:
    doc_id: str
    chunk_id: int
    text: str

def chunk_text(text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be < chunk_size")

    parts = re.split(r"\n\n+|(?<=[.!?])\s+", text)
    parts = [p.strip() for p in parts if p and p.strip()]

    chunks: List[str] = []
    cur: List[str] = []
    cur_len = 0

    def flush():
        nonlocal cur, cur_len
        if cur:
            chunks.append(" ".join(cur).strip())
            cur = []
            cur_len = 0

    for part in parts:
        plen = len(part)
        if cur_len + plen + 1 <= chunk_size:
            cur.append(part)
            cur_len += plen + 1
            continue

        flush()

        if plen > chunk_size:
            start = 0
            while start < plen:
                end = min(start + chunk_size, plen)
                chunks.append(part[start:end].strip())
                start = max(end - chunk_overlap, start + 1)
        else:
            cur.append(part)
            cur_len = plen + 1

    flush()

    if chunk_overlap > 0 and len(chunks) > 1:
        overlapped: List[str] = []
        prev_tail = ""
        for c in chunks:
            overlapped.append((prev_tail + " " + c).strip() if prev_tail else c)
            prev_tail = c[-chunk_overlap:]
        chunks = overlapped

    return [c for c in chunks if c.strip()]

def build_chunks(doc_id: str, text: str, chunk_size: int, chunk_overlap: int) -> List[Chunk]:
    chunks = chunk_text(text, chunk_size, chunk_overlap)
    return [Chunk(doc_id=doc_id, chunk_id=i, text=c) for i, c in enumerate(chunks)]
