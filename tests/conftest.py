import os
import sys
import tempfile
from pathlib import Path

# Isolate persistent runtime state into a throwaway directory. RIFRuntime now
# restores its posture from posture_history.jsonl / decisions.jsonl at startup,
# so a shared data/ would let one test's escalation decide the posture every
# later RIFRuntime() — in this run and in the next one — starts in.
#
# Set at import time, before any test module (and therefore rif_runtime.api's
# module-level RIFRuntime) is imported, and before config caches its settings.
os.environ.setdefault("RIF_DATA_DIR", tempfile.mkdtemp(prefix="rif-test-data-"))

RUNNERS_DIR = (
    Path(__file__).resolve().parent.parent
    / "rif-evals"
    / "code_refinement_mst"
    / "runners"
)
if str(RUNNERS_DIR) not in sys.path:
    sys.path.insert(0, str(RUNNERS_DIR))
