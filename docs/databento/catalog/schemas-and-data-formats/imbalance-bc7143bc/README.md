# Imbalance

Use the listed field names to identify the record contract, then read the official types, sentinels and semantics. Confirm dataset support and version-specific layout through metadata. Keep availability, units and SDK representation explicit.

Official route: [Databento documentation](https://databento.com/docs/schemas-and-data-formats/imbalance).

Review state: `retrieved`.

## Field inventory

`ts_recv`, `ts_event`, `rtype`, `publisher_id`, `instrument_id`, `ref_price`, `auction_time`, `cont_book_clr_price`, `auct_interest_clr_price`, `ssr_filling_price`, `ind_match_price`, `upper_collar`, `lower_collar`, `paired_qty`, `total_imbalance_qty`, `market_imbalance_qty`, `unpaired_qty`, `auction_type`, `side`, `auction_status`, `freeze_status`, `num_extensions`, `unpaired_side`, `significant_imbalance`.

Implementation route: [task guide](../../../schemas/README.md). Return to [catalog](../../README.md).
