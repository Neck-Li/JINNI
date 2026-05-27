"""Run rag_audit with ASCII-safe output."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="ascii", errors="replace")

with open("G:/my code/claude code/嵌入式金句.md", "r", encoding="utf-8") as f:
    text = f.read()

# Override sys.argv so rag_audit reads from our variable
import rag_audit

rag_audit.main_inline(text)
