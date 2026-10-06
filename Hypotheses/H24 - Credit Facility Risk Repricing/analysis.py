"""Folder-owned reporting entry for the joint registered comparison family."""
from discovery.financing_analysis import analyze
STUDY='H24'

def evaluate(run):
    return analyze(run)
