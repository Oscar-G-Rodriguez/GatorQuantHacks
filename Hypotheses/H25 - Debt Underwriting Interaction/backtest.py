"""Folder-owned Webull/Backtrader research interface; registered funded shapes."""
from pathlib import Path
import argparse, json, sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]))
STUDY = 'H25'

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('stage',choices=['prepare','run','analyze','export','placebo-prepare'])
 p.add_argument('--run',required=True);p.add_argument('--task',type=int,default=0);p.add_argument('--replica',type=int,default=0)
 p.add_argument('--phase',choices=['development','final-oos'],default='development');a=p.parse_args()
 if a.phase=='final-oos':raise ValueError('No attested unseen confirmation window/freeze; prior exposure cannot be reset')
 if a.stage=='run':
  tasks=json.loads((Path(a.run)/'tasks.json').read_text())
  if tasks[a.task]['study']!=STUDY:raise ValueError('Task belongs to another hypothesis')
 from discovery.financing_pipeline import execute
 execute(a.run,a.stage,a.task,a.replica,a.phase)

if __name__=='__main__':main()
