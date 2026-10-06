# Corporate actions, adjustments, and security master

Reference data is a separate API with different identity, indexing, and revision behavior from normalized market records. Its official client coverage is Python and Rust plus HTTP. Use `db.Reference()` in Python, or a clearly documented artifact/HTTP boundary for C++. Do not assume historical market-data entitlements include every reference product. [Reference API](https://databento.com/docs/api-reference-reference).

## Corporate actions

`corporate_actions.get_range` filters events and listings by symbols, events, country/exchange/security type, and the chosen index. `index` can be `event_date`, `ex_date`, or `ts_record`; rows with a null selected index are excluded. `pit=True` retains event history, while the default selects the latest record for each `event_unique_id`. Use `ts_record` and the actual dataset's availability semantics to restrict versions for a historical decision. An ex-date query alone does not establish that a record was known beforehand. [Corporate-actions request](https://databento.com/docs/api-reference-reference/corporate-actions/corporate-actions-get-range).

Discover valid event types and enum values with `list_events` and `list_enums`, and consult the schema's nested/flattened fields. Do not confuse the listing, security, and issuer identities. Keep event actions, cancellations, replacements, and revisions in the data contract. [Event enumeration](https://databento.com/docs/api-reference-reference/corporate-actions/corporate-actions-list-events), [field schema](https://databento.com/docs/schemas-and-data-formats/corporate-actions).

## Adjustment factors

`adjustment_factors.get_range` uses `ex_date` for filtering/indexing. Explain the direction and effective date of multiplication, price versus volume adjustments, and how multiple events combine. Keep raw execution prices and adjusted analysis series distinct. A smooth backward-adjusted series can embed later corporate events, so its suitability depends on the experiment's purpose. [Adjustment request](https://databento.com/docs/api-reference-reference/adjustment-factors/adjustment-factors-get-range), [factor application](https://databento.com/docs/examples/adjustment-factors/applying-adjustment-factors).

Do not extrapolate the corporate-actions `pit` parameter to endpoints that do not expose it. Reference endpoint defaults also differ: several omitted `end` values return all subsequent available data rather than forward-filling a historical interval. Use explicit end bounds.

## Security master

Use historical security-master records when constructing a dated universe or joining listing/security attributes. A latest record from `get_last` is useful for current enrichment, but cannot prove historical membership. Review `get_range`'s date/index/PIT options and the dataset's listing-continuity rules. [History](https://databento.com/docs/api-reference-reference/security-master/security-master-get-range), [latest state](https://databento.com/docs/api-reference-reference/security-master/security-master-get-last), [dataset guide](https://databento.com/docs/venues-and-datasets/security-master).

Reference symbology includes identifiers beyond market-data stypes, with endpoint-specific support. `allocate_isins` can affect ISIN-limited plan allocation and returned rows. Configure it deliberately and check omissions; do not turn a broad symbol request into an undocumented account allocation. [Reference symbology](https://databento.com/docs/api-reference-reference/basics/symbology).

The public tutorials contain several unfinished corporate-action articles. The catalog marks them as upstream placeholders. Their titles supply no verified implementation recipe; use the actual API/schema and finished examples.
