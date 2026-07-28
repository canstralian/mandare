import os
import sys
import tempfile
from pathlib import Path

# Redirect runtime state to a throwaway directory before any rif_runtime module
# is imported. tests/test_api.py and friends build a RIFRuntime at import time,
# so setting this inside a fixture would be too late.
#
# Without it the suite writes into the repository: appending to the gitignored
# data/*.jsonl logs, and -- via the /v1/policies routes -- rewriting the
# checked-in data/policies.json seed, leaving `git status` dirty after a run.
_DATA_DIR = Path(tempfile.mkdtemp(prefix="rif-test-data-"))
os.environ.setdefault("RIF_DATA_DIR", str(_DATA_DIR))

RUNNERS_DIR = (
    Path(__file__).resolve().parent.parent
    / "rif-evals"
    / "code_refinement_mst"
    / "runners"
)
if str(RUNNERS_DIR) not in sys.path:
    sys.path.insert(0, str(RUNNERS_DIR))
