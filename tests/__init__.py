import sys
from pathlib import Path

_SRC_DIR = str(Path(__file__).resolve().parent.parent / "src")
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

# Automatically synchronize local test data into gitignored tests/test_data/
try:
    from .test_data_manager import sync_test_data
    sync_test_data()
except Exception:
    pass
