"""Hugging Face Space entry point."""
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from doc2md.app import create_ui

demo = create_ui()
demo.queue(default_concurrency_limit=5)
