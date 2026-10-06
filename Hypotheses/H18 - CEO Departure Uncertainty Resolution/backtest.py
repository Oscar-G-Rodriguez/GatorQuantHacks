"""Own H18 scheduled entry point; see the registered mechanism-round1 plan."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from discovery.mechanism_run import main

if __name__ == "__main__":
    main("H18")
