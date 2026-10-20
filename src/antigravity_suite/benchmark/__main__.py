"""
Package entrypoint for `python3 -m antigravity_suite.benchmark`.
"""

import sys
from .cli import main

if __name__ == "__main__":
    sys.exit(main())
