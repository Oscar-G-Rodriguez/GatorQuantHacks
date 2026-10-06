"""H18: owned option construction and event eligibility.

Adapted from the Webull/Backtrader offline strategy interface. No live calls.
The funded ledger prices all synthetic and overlay legs at backward quotes.
"""
from discovery.mechanism_engine import FundedStrategy
from discovery.mechanism_accounting import construction
from discovery.mechanism_features import classification

CATEGORY = "ceo_departure"
SHAPE = "covered_call"


def eligible(anchor, reviews):
    return True


class Strategy(FundedStrategy):
    """H18 uses covered_call with the frozen event, reserve and risk rules."""
    option_units = construction(SHAPE)
