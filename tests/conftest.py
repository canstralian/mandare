import sys
from pathlib import Path

RUNNERS_DIR = (
    Path(__file__).resolve().parent.parent
    / "rif-evals"
    / "code_refinement_mst"
    / "runners"
)
if str(RUNNERS_DIR) not in sys.path:
    sys.path.insert(0, str(RUNNERS_DIR))
