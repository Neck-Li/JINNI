"""
RAG quality audit script — detect duplicate/broken chunks.
Usage: python rag_audit.py <markdown_file>
"""
from __future__ import annotations

import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="ascii", errors="replace", closefd=False)

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
SIM_THRESHOLD = 0.8


def read_md(path: str) -> str:
    content = Path(path).read_text(encoding="utf-8")
    content = re.sub(r"^---(.|\n)*?---\n*", "", content)
    return content


def chunk_text(text: str, size: int, overlap: int) -> list[str]:
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start += size - overlap
    return chunks


def report_chunks(chunks: list[str]) -> None:
    print(f"\n{'='*60}")
    print(f"[CHUNKS] Total: {len(chunks)}, size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP}")
    print(f"{'='*60}")
    lengths = [len(c) for c in chunks]
    print(f"  Size: min={min(lengths)} max={max(lengths)} avg={sum(lengths)//len(lengths)}")
    print(f"  First 5:")
    for i, c in enumerate(chunks[:5]):
        print(f"    [{i}] ({len(c)}c) {c[:60]}...")
    if len(chunks) > 5:
        print(f"    ... (total {len(chunks)})")


def find_duplicates(chunks: list[str]) -> list[tuple[int, int, float]]:
    pairs: list[tuple[int, int, float]] = []
    print(f"\n{'='*60}")
    print(f"[DUP] Pairwise {len(chunks)} chunks, threshold>={SIM_THRESHOLD}")
    print(f"{'='*60}")
    for i in range(len(chunks)):
        for j in range(i + 1, len(chunks)):
            ratio = SequenceMatcher(None, chunks[i], chunks[j]).ratio()
            if ratio >= SIM_THRESHOLD:
                pairs.append((i, j, ratio))
    return pairs


def report_duplicates(pairs: list[tuple[int, int, float]], chunks: list[str]) -> None:
    print(f"  Similar pairs: {len(pairs)}")
    if pairs:
        for k, (a, b, score) in enumerate(pairs[:10]):
            print(f"  [{k+1}] Chunk {a}<->{b} sim={score:.2f}")
            print(f"    A: {chunks[a][:80]}...")
            print(f"    B: {chunks[b][:80]}...")
    else:
        print(f"  [OK] No similar pairs found")


def find_broken(chunks: list[str]) -> list[tuple[int, str, str]]:
    results: list[tuple[int, str, str]] = []
    print(f"\n{'='*60}")
    print(f"[BROKEN] Scanning chunk boundaries")
    print(f"{'='*60}")
    for i, c in enumerate(chunks):
        s = c.strip()
        if not s:
            continue
        reasons = []
        if s[0].islower():
            reasons.append("starts_lower")
        if s[0].isdigit() or s[0] in "([{'\"-":
            reasons.append(f"starts_sym('{s[0]}')")
        if s[-1] not in ".!?。！？）)]\"'":
            reasons.append("no_end")
        if reasons:
            results.append((i, ", ".join(reasons), s[:80]))
    return results


def report_broken(results: list[tuple[int, str, str]], total: int) -> None:
    print(f"  Suspicious: {len(results)}/{total}")
    for i, reason, preview in results:
        print(f"    [{i}] {reason}: {preview}...")


HAS_EMBED = False
try:
    from sentence_transformers import SentenceTransformer
    HAS_EMBED = True
except ImportError:
    pass


def embed_search(chunks, questions):
    if not HAS_EMBED:
        print(f"\n[EMBED] Skipped (pip install sentence-transformers)")
        return
    print(f"\n[EMBED] all-MiniLM-L6-v2")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    chunk_embs = model.encode(chunks, show_progress_bar=False)
    for q in questions:
        q_emb = model.encode([q])[0]
        scores = [(i, _cos_sim(q_emb, chunk_embs[i])) for i in range(len(chunks))]
        scores.sort(key=lambda x: -x[1])
        print(f"\n  Q: {q}")
        for rank, (idx, score) in enumerate(scores[:5], 1):
            label = ""
            if rank > 1 and abs(scores[rank - 1][0] - idx) < 3 and score > 0.85:
                label += " [WARN] adjacent similar"
            if chunks[idx].strip()[0].islower():
                label += " [WARN] starts_lower"
            print(f"    #{rank} chunk[{idx}] (score={score:.3f}){label}")
            print(f"      {chunks[idx][:100]}...")


def _cos_sim(a, b):
    import numpy as np
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-10))


def main():
    if len(sys.argv) < 2:
        print("Usage: python rag_audit.py <file.md>")
        sys.exit(1)
    path = sys.argv[1]
    raw = read_md(path)
    print(f"Read: {path}")
    print(f"Chars: {len(raw)}")

    chunks = chunk_text(raw, CHUNK_SIZE, CHUNK_OVERLAP)
    report_chunks(chunks)

    pairs = find_duplicates(chunks)
    report_duplicates(pairs, chunks)

    broken = find_broken(chunks)
    report_broken(broken, len(chunks))

    embed_search(chunks, [
        "IBRD 2024 commitment?",
        "World Bank Group vision?",
    ])


if __name__ == "__main__":
    main()
