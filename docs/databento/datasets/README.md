# Dataset selection and venue exceptions

A dataset ID selects a feed/product. A publisher identifies a venue within that dataset. Schema support, history, timestamp quality, instrument coverage, source granularity, and normalization exceptions must be checked for the selected feed. The catalog covers every discovered dataset guide; use its official source before implementing a venue-dependent assumption. [Venue and dataset index](https://databento.com/docs/venues-and-datasets).

## Useful QuantHacks distinctions

| Family | Read before using it |
| --- | --- |
| CME futures/options: `GLBX.MDP3` | [CME guide](https://databento.com/docs/venues-and-datasets/glbx-mdp3), dated definitions, MBO/implied-book rules, statistics timing |
| ICE commodities/financials/US/Endex | Each `IFEU.IMPACT`, `IFLL.IMPACT`, `IFUS.IMPACT`, or `NDEX.IMPACT` guide; off-market trades and system-priced legs |
| CFE, Eurex, EEX | `XCBF.PITCH`, `XEUR.EOBI`, `XEEE.EOBI` guide; product identity, matching/session rules, normalization |
| US direct equity feeds | Venue-specific ITCH/PILLAR/PITCH/MEMOIR/TOPS guides; native symbol conventions and publisher attribution |
| Derived equity products | `EQUS.MINI`, `EQUS.SUMMARY`, `DBEQ.BASIC`; distinguish aggregate quotes, summaries, and component feeds |
| US equity options | `OPRA.PILLAR`; consolidated versus regional quotes, venue identity, condition/statistics behavior |
| Indices and NAVs | CGIF/DBIX guides; index values are not automatically executable market quotes |
| Reference products | Corporate-action, adjustment-factor, and security-master guides; separate access and revision contracts |

## CME and agricultural research

For corn or another future, start with a parent query for definitions and explicitly select the desired outright/spread classes. Define the contract roll before research. `GLBX.MDP3` covers several CME Group exchanges; the publisher map supplies the venue context.

The reviewed guide separates native order book liquidity from the implied book and describes combined top-of-book schemas. It also distinguishes older MDP2 history, whose receipt timestamps are synthetic and MBO is unavailable. OI/cleared-volume release times and preliminary/final settlement flags require an availability-aware join. Raw contract symbols may use two-digit years. Read the complete dataset card before assuming a universal book or clock. [CME guide](https://databento.com/docs/venues-and-datasets/glbx-mdp3).

## Equity products

`EQUS.MINI` supplies aggregated BBO across component venues. It anonymizes trade venue attribution, sets sequence to zero, and does not aggregate order counts (`bid_ct_00`/`ask_ct_00` are zero). It therefore cannot support per-venue queue reconstruction. [Mini guide](https://databento.com/docs/venues-and-datasets/equs-mini).

A synthetic consolidated quote from direct feeds can differ from official SIP NBBO because contributors, odd-lot rules, clocks, and consolidation location differ. Declare which quote is used for a signal and which price supports execution. [Consolidation example](https://databento.com/docs/examples/equities/consolidated-bbo).

Use `EQUS.SUMMARY` only for its documented summary semantics; UTC trade bars and official closing statistics answer different questions. [Summary guide](https://databento.com/docs/venues-and-datasets/equs-summary), [equity closing prices](https://databento.com/docs/examples/equities/closing-prices).

## Validate what the account actually returns

Discover the current dataset IDs and account-visible ranges. Do not infer that a mentioned product is available because an enum or public guide exists. Retain failed requests and partial resolution. Verify that fields you use are populated in the actual sample; zeros and sentinel values may be expected normalization rather than real economic observations.
