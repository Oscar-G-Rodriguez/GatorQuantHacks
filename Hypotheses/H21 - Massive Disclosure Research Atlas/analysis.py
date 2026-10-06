"""Folder-owned H21 scheduled entry point; shared dependencies stay at the root."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from discovery.atlas import main

if __name__ == "__main__":
    main()
