"""Hugging Face Space entry point."""
import sys
import os

# Debug: print environment
print(f"CWD: {os.getcwd()}")
print(f"Script dir: {os.path.dirname(__file__)}")
print(f"sys.path: {sys.path}")
print(f"Repo contents: {os.listdir('.')}")
print(f"doc2md exists: {os.path.isdir('doc2md')}")
print(f"doc2md/__init__ exists: {os.path.isfile('doc2md/__init__.py')}")
sys.stdout.flush()

# Try to add current dir to path
_root = os.path.dirname(os.path.abspath(__file__))
if _root not in sys.path:
    sys.path.insert(0, _root)

# Try import
try:
    import doc2md
    print(f"doc2md imported OK from {doc2md.__file__}")
except Exception as e:
    print(f"doc2md import failed: {e}")

# Direct import of app
try:
    from doc2md.app import main
    print("Starting main()")
    sys.stdout.flush()
    main()
except Exception as e:
    print(f"Failed to start: {e}")
    import traceback
    traceback.print_exc()
