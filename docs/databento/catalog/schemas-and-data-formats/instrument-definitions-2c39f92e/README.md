# Instrument definitions

Use the listed field names to identify the record contract, then read the official types, sentinels and semantics. Confirm dataset support and version-specific layout through metadata. Keep availability, units and SDK representation explicit.

Official route: [Databento documentation](https://databento.com/docs/schemas-and-data-formats/instrument-definitions).

Review state: `retrieved`.

## Field inventory

`ts_recv`, `ts_event`, `rtype`, `publisher_id`, `instrument_id`, `raw_symbol`, `security_update_action`, `instrument_class`, `min_price_increment`, `display_factor`, `expiration`, `activation`, `high_limit_price`, `low_limit_price`, `max_price_variation`, `unit_of_measure_qty`, `min_price_increment_amount`, `price_ratio`, `inst_attrib_value`, `underlying_id`, `raw_instrument_id`, `market_depth_implied`, `market_depth`, `market_segment_id`, `max_trade_vol`, `min_lot_size`, `min_lot_size_block`, `min_lot_size_round_lot`, `min_trade_vol`, `contract_multiplier`, `decay_quantity`, `original_contract_size`, `appl_id`, `maturity_year`, `decay_start_date`, `channel_id`, `currency`, `settl_currency`, `secsubtype`, `group`, `exchange`, `asset`, `cfi`, `security_type`, `unit_of_measure`, `underlying`, `strike_price_currency`, `strike_price`, `match_algorithm`, `main_fraction`, `price_display_format`, `sub_fraction`, `underlying_product`, `maturity_month`, `maturity_day`, `maturity_week`, `user_defined_instrument`, `contract_multiplier_unit`, `flow_schedule_type`, `tick_rule`, `leg_count`, `leg_index`, `leg_instrument_id`, `leg_raw_symbol`, `leg_instrument_class`, `leg_side`, `leg_price`, `leg_delta`, `leg_ratio_price_numerator`, `leg_ratio_price_denominator`, `leg_ratio_qty_numerator`, `leg_ratio_qty_denominator`, `leg_underlying_id`, `Bond`, `Call`, `Future`, `Stock`, `Put`, `Index`, `Equity`, `Spreads`, `Spot`, `Undefined`, `FIFO`, `Configurable`, `Pro-Rata`, `Allocation`.

Implementation route: [task guide](../../../schemas/README.md). Return to [catalog](../../README.md).
