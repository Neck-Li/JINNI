"""
向量库可视化 — 显示 chunk 间相似度矩阵 + 聚类
用法: python show_vectors.py <markdown文件>
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="ascii", errors="replace", closefd=False)

from sentence_transformers import SentenceTransformer
import numpy as np

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50


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


# ── 1. 加载 + 切块 + 向量化 ──────────────────────────────────────
path = sys.argv[1]
raw = read_md(path)
chunks = chunk_text(raw, CHUNK_SIZE, CHUNK_OVERLAP)

print(f"读取: {Path(path).name}")
print(f"字符: {len(raw)}")
print(f"切块: {len(chunks)} 块\n")

print("加载 embedding 模型...")
model = SentenceTransformer("all-MiniLM-L6-v2")
vecs = model.encode(chunks, show_progress_bar=True)
print(f"向量维度: {vecs.shape[1]}")
print(f"向量形状: {vecs.shape}\n")

# ── 2. 相似度矩阵 ─────────────────────────────────────────────────
sim = np.dot(vecs, vecs.T)
norms = np.linalg.norm(vecs, axis=1, keepdims=True)
sim = sim / (norms * norms.T + 1e-10)  # 余弦相似度

# ASCII heatmap: 打印相似度矩阵
print("=" * 70)
print(f"[SIMILARITY MATRIX] {len(chunks)}x{len(chunks)} (0=黑 .25=灰 .5=浅 .75=白)")
print("=" * 70)
# 缩小显示 — 只显示 60x60 以内
show_n = min(len(chunks), 60)
for i in range(show_n):
    row = ""
    for j in range(show_n):
        v = sim[i][j]
        if v > 0.9:
            row += "W"  # 极高相似（自己和相邻块）
        elif v > 0.7:
            row += "#"
        elif v > 0.5:
            row += "*"
        elif v > 0.3:
            row += "."
        else:
            row += " "
    # 标记最相似的块
    top = [(k, sim[i][k]) for k in range(len(chunks)) if k != i]
    top.sort(key=lambda x: -x[1])
    top3 = [str(t[0]) for t in top[:3] if t[1] > 0.5]
    label = f"  [{i}]" + (f" sim:{','.join(top3)}" if top3 else "")
    print(f"  {row}  {label}")

# ── 3. 最相似块对（非相邻）────────────────────────────────────────
print("\n" + "=" * 70)
print("[TOP SIMILAR PAIRS] (非相邻块，相似度 > 0.5)")
print("=" * 70)
pairs = []
for i in range(len(chunks)):
    for j in range(i + 1, len(chunks)):
        if abs(i - j) <= 2:
            continue  # 跳过相邻块（天然相似）
        s = float(sim[i][j])
        if s > 0.5:
            pairs.append((s, i, j))
pairs.sort(key=lambda x: -x[0])

if pairs:
    for s, i, j in pairs[:15]:
        print(f"  Chunk[{i}] <-> [{j}]  sim={s:.3f}")
        print(f"    A: {chunks[i][:60]}...")
        print(f"    B: {chunks[j][:60]}...")
else:
    print("  没有发现高相似度跨区对（文档内容多样性好）")

# ── 4. 按问题检索 ─────────────────────────────────────────────────
print("\n" + "=" * 70)
print("[RETRIEVAL DEMO]")
print("=" * 70)
questions = [
    "ARM",
    "instruction",
    "memory",
    "interrupt",
    "UART",
    "I2C",
]
for q in questions:
    qv = model.encode([q])[0]
    scores = [(i, float(np.dot(qv, vecs[i]) / (np.linalg.norm(qv) * np.linalg.norm(vecs[i]) + 1e-10)))
              for i in range(len(vecs))]
    scores.sort(key=lambda x: -x[1])
    top = scores[0]
    print(f"  Q: \"{q}\"  ->  chunk[{top[0]}] (score={top[1]:.3f})")
    print(f"      {chunks[top[0]][:80]}...")
