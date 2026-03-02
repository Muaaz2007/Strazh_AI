"""
pytest configuration: ensure the project root is on sys.path so that
all imports resolve correctly when running from any working directory.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to sys.path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
