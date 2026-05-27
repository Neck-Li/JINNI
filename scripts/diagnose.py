"""
【第二步：诊断脚本】量化多栏串行 + 行尾重复
用法: python diagnose.py <PDF路径>
"""
from __future__ import annotations
import re, sys, os
from pathlib import Path

sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="ascii", errors="replace", closefd=False)

import fitz


def diagnose(pdf_path: str):
    name = Path(pdf_path).stem
    doc = fitz.open(pdf_path)
    print(f"\n{'='*70}")
    print(f"FILE: {name}.pdf  ({len(doc)} pages)")
    print(f"{'='*70}")

    total_blocks = 0
    total_lines = 0
    total_tail_repeats = 0
    bad_pages = []  # pages with interleaving

    for pg in range(len(doc)):
        page = doc[pg]
        pw, ph = page.rect.width, page.rect.height
        blocks = page.get_text("dict")["blocks"]
        text_blocks = [b for b in blocks if b["type"] == 0]

        if len(text_blocks) < 3:
            continue

        # --- (A) 检测多栏 ---
        x_centers = [(b["bbox"][0] + b["bbox"][2]) / 2 for b in text_blocks]
        sorted_x = sorted(x_centers)
        gaps = [sorted_x[i+1] - sorted_x[i] for i in range(len(sorted_x)-1)]
        n_cols = sum(1 for g in gaps if g > pw * 0.15) + 1
        is_multi = n_cols >= 2

        # --- (B) 按当前 sort (y, x) 输出前 20 块 ---
        sorted_blocks = sorted(text_blocks, key=lambda b: (b["bbox"][1], b["bbox"][0]))
        total_blocks += len(sorted_blocks)

        # --- (C) 检测交错: 块按 (y, x) 排序后, 检查 (x 坐标是否来回跳) ---
        x_order = [(b["bbox"][0] + b["bbox"][2]) / 2 for b in sorted_blocks]
        switches = 0
        for k in range(1, len(x_order)):
            # 如果 x 从右跳到左（跨栏），说明交错
            if x_order[k] < x_order[k-1] - pw * 0.2:
                switches += 1

        interleaved = switches > len(sorted_blocks) * 0.1

        if is_multi and interleaved:
            bad_pages.append((pg + 1, n_cols, switches, len(sorted_blocks)))
            if len(bad_pages) <= 2:
                print(f"\n  PAGE {pg+1} (检测到 {n_cols} 栏, {switches} 次 x 跳跃):")
                print(f"  {'i':>3} {'type':>5} {'x0':>6} {'y0':>6} {'cx':>6} {'text':30}")
                print(f"  {'-'*60}")
                for i, b in enumerate(sorted_blocks[:15]):
                    x0, y0, x1, y1 = b["bbox"]
                    cx = (x0 + x1) / 2
                    txt = ""
                    for line in b.get("lines", []):
                        for span in line.get("spans", []):
                            txt += span.get("text", "")
                    txt = txt[:30].replace("\n", " ")
                    print(f"  {i:3d} {'text':>5} {x0:6.0f} {y0:6.0f} {cx:6.0f} {txt:30}")

    # --- (D) 行尾重复检测（在最终输出的 Markdown 里扫） ---
    md_dir = "G:/my code/claude code/doc2md/test_output/pdfs_batch"
    md_paths = [
        os.path.join(md_dir, f"{name}.md"),
        os.path.join(md_dir, f"{name.replace('.pdf', '')}.md"),
    ]
    md_path = next((p for p in md_paths if os.path.exists(p)), None)
    if md_path:
        with open(md_path, "r", encoding="utf-8", errors="replace") as f:
            md_lines = [l for l in f.readlines() if l.strip() and not l.startswith("!") and not l.startswith("---")]
        tail_repeats = 0
        for i in range(len(md_lines) - 1):
            a = md_lines[i].strip()
            b = md_lines[i + 1].strip()
            if len(a) < 20 or len(b) < 20:
                continue
            tail = a[-15:]
            head = b[:15]
            if tail == head or tail == b[: len(tail)]:
                tail_repeats += 1
                if tail_repeats <= 5:
                    print(f"\n  [TAIL REPEAT] line {i}:")
                    print(f"    N  : {a[:60]}...")
                    print(f"    N+1: {b[:60]}...")
        total_tail_repeats += tail_repeats
        total_lines += len(md_lines)

    doc.close()

    # --- (E) 总结 ---
    print(f"\n{'='*70}")
    print(f"SUMMARY: {name}")
    print(f"{'='*70}")
    print(f"  多栏页面: {len(bad_pages)}")
    if bad_pages:
        for pg, nc, sw, nb in bad_pages[:5]:
            print(f"    Page {pg}: {nc}栏, {sw}次 x跳变 ({nb}个块)")
    print(f"  文本块总数: {total_blocks}")
    print(f"  行尾重复: {total_tail_repeats} 处")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python diagnose.py <pdf>")
        sys.exit(1)
    diagnose(sys.argv[1])
