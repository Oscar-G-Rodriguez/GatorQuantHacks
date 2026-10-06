from discovery.mechanism_engine import FundedStrategy

class FinancingStrategy(FundedStrategy):
    """Use the registered explicit cash ledger, never constant-feed broker P&L."""
    study = 'H24'
