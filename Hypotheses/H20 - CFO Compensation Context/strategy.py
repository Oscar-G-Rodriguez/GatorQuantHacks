"""H20: owned option construction and event eligibility.

Adapted from the Webull/Backtrader offline strategy interface. No live calls.
The funded ledger prices all synthetic and overlay legs at backward quotes.
"""
from discovery.mechanism_engine import FundedStrategy
from discovery.mechanism_accounting import construction
from discovery.mechanism_features import classification

CATEGORY = "cfo_appointment"
SHAPE = "cash_secured_put"


def eligible(anchor, reviews):
    return classification(anchor, reviews) == "verified_incoming_cfo_terms"


class Strategy(FundedStrategy):
    """H20 uses cash_secured_put with the frozen event, reserve and risk rules."""
    option_units = construction(SHAPE)
