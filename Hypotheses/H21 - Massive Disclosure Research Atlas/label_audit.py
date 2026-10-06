"""Folder-owned entry for standard labels and optional evidence annotations."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from discovery.atlas_label_audit import main

if __name__ == '__main__':
    main()
