# #region agent log
import json as _json
import time as _time

open("/opt/cursor/logs/debug.log", "a").write(
    _json.dumps(
        {
            "hypothesisId": "H2",
            "location": "api/index.py",
            "message": "legacy vercel builds entrypoint importing rif_runtime.api",
            "data": {
                "entrypoint": "api/index.py",
                "import_target": "rif_runtime.api:app",
            },
            "timestamp": int(_time.time() * 1000),
        }
    )
    + "\n"
)
# #endregion
from rif_runtime.api import app  # noqa: F401
