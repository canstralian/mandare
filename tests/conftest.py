import atexit
import os
import sys
import tempfile
from pathlib import Path

# Isolate persistent runtime state into a throwaway directory. MandareRuntime now
# restores its posture from posture_history.jsonl / decisions.jsonl at startup,
# so a shared data/ would let one test's escalation decide the posture every
# later MandareRuntime() — in this run and in the next one — starts in.
#
# Set at import time, before any test module (and therefore mandare.api's
# module-level MandareRuntime) is imported, and before config caches its settings.
# That rules out a fixture, so the directory is cleaned up via atexit rather
# than by pytest — otherwise every local run would leak a rif-test-data-* dir.
if "RIF_DATA_DIR" not in os.environ:
    _data_dir = tempfile.TemporaryDirectory(prefix="rif-test-data-")
    atexit.register(_data_dir.cleanup)
    os.environ["RIF_DATA_DIR"] = _data_dir.name

RUNNERS_DIR = (
    Path(__file__).resolve().parent.parent
    / "rif-evals"
    / "code_refinement_mst"
    / "runners"
)
if str(RUNNERS_DIR) not in sys.path:
    sys.path.insert(0, str(RUNNERS_DIR))
