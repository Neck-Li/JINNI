"""Hugging Face Space entry point - fix import path."""
import sys
from pathlib import Path

# Ensure the repo root is on sys.path so doc2md package can be found
_root = Path(__file__).resolve().parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from doc2md.app import main

main()
