from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

for exporter in ("export_replays.py", "export_strategy_summary.py"):
    subprocess.run(
        [sys.executable, str(ROOT / "showcase" / "exporter" / exporter)], check=True
    )
