import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("AM_PROVIDER", "mock")
os.environ.setdefault("AM_BLOCK_SECONDS", "60")
os.environ.setdefault("AM_TOKEN_BUDGET", "999999999")
