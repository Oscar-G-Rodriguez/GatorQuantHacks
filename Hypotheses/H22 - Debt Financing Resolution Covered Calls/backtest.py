"""H22 entry point adapted from the Webull starter's Cerebro/Strategy flow.

Massive-only offline prices feed a funded stock/option ledger. No Webull order
client or live-trading entry point is imported. Numerical stages require SLURM.
"""
from pathlib import Path
import argparse
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE))

from research import prepare, scheduled


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("stage", choices=["prepare","run","analyze","export"])
    p.add_argument("--run", required=True)
    p.add_argument("--phase", choices=["development","final-oos"], default="development")
    p.add_argument("--task", type=int, default=0)
    a = p.parse_args()
    if a.phase == "final-oos":
        raise ValueError("No verified unseen H22 confirmation window/freeze exists; exposed dates cannot be final OOS")
    scheduled()
    if a.stage == "prepare": prepare(a.run)
    elif a.stage == "run":
        from strategy import run_task
        run_task(a.run, a.task)
    elif a.stage == "analyze":
        from analysis import analyze
        analyze(a.run)
    elif a.stage == "export":
        from pipeline import export
        export(a.run)


if __name__ == "__main__": main()
