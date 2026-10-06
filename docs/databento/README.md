# Databento implementation guide for QuantHacks

This folder turns the public [Databento documentation](https://databento.com/docs/) into a reference that a coding agent can use in this repository. Start with the task guides below, then open the relevant page cards in [the documentation catalog](catalog/README.md). The catalog follows the documentation sitemap and linked sections, including release history. The coverage report distinguishes retrieved sections, sections recovered from a parent page, unfinished upstream articles, and unresolved routes.

Reviewed **October 2–3, 2026**, in America/New_York. This is an independent implementation reference, with original explanations and links to the official specifications. It is a dated snapshot: the installed SDK, returned metadata, and current official specification settle version-sensitive details. Python and C++ have separate interfaces. Reference data has Python, Rust, and HTTP interfaces; the reviewed docs do not advertise a C++ Reference client.

## Choose the reading route

| Work | Read these files in order |
| --- | --- |
| First integration | [Research contract](research/README.md), [Python](python/README.md) or [C++](cpp/README.md), [Historical](historical/README.md) |
| Download a research dataset | [Historical](historical/README.md), [Symbology](symbology/README.md), [Datasets](datasets/README.md), [Storage](storage/README.md) |
| Futures, corn, spreads, or open interest | [Symbology](symbology/README.md), [Schemas](schemas/README.md), [Datasets](datasets/README.md), [Research contract](research/README.md) |
| Order book reconstruction or queue features | [Conventions](conventions/README.md), [Schemas](schemas/README.md), [Order books](order-book/README.md), the selected dataset card |
| Live capture or replay | [Live](live/README.md), [Operations](operations/README.md), [Storage](storage/README.md) |
| Equity adjustments, listings, or corporate actions | [Reference data](reference/README.md), [Symbology](symbology/README.md), [Research contract](research/README.md) |
| Find a worked example | [Tutorials](tutorials/README.md), then its catalog card and official example |
| Change SDK or historical data version | [Maintenance](maintenance/README.md), [Coverage](COVERAGE.md), the corresponding release cards |

## Instructions for a coding agent

Read the repository's root `AGENTS.md`, root README, and selected hypothesis registration first. These guides explain the data provider; the repository rules still govern research and execution. Documentation preparation does not register an economic hypothesis or authorize a backtest.

Before implementing a request, write down its dataset, schema, symbols, symbology, explicit UTC interval, expected units, clock used for availability, storage destination, and cost bound. Discover schema support and account-visible history using metadata. Resolve instruments for the actual dates. A public dataset page does not establish the team's sponsor entitlements.

Keep source data and transformations separate. Retain licensed raw DBN outside Git, with permitted metadata and hashes in an experiment manifest. Implement a provider adapter that emits a documented internal representation; keep signal logic independent of the download client. Use one interpretation of prices, missing values, symbol mappings, and clocks in Python and C++.

Use narrowly bounded requests for integration work. `ALL_SYMBOLS`, omitted symbols, broad parent symbols, and omitted end dates can expand a request substantially. A record limit truncates a response and does not prove complete interval coverage. Check the returned records and resolution report before declaring a download usable.

## What has been verified

Public documentation was retrieved and analyzed; coverage and source evidence are recorded in `COVERAGE.md` and `coverage.json`. Examples here were written as implementation patterns. No Databento key was used, no licensed market data was downloaded, no SDK environment was installed, and no C++ example was compiled. Network examples are deliberately not run by documentation validation. Account rights, actual request costs, and live behavior require a separate authorized integration check.

## Copy into another repository

See the [coverage report](COVERAGE.md), [route inventory](coverage.json), and [validation record](VALIDATION.md) for the scope and checks. `MANIFEST.sha256` identifies the packaged files.

Copy this entire `databento/` folder into `docs/`. Add a pointer to `docs/databento/README.md` in that repository's root agent instructions. Keep relative links intact. The folder contains no private vault paths, source HTML archives, real credentials, or market data.
