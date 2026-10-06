# Versions, coverage, and keeping this pack current

This pack is dated documentation. Use its workflow guidance, but verify installed SDK signatures, account metadata, and current source semantics whenever a version-sensitive assumption matters. Do not silently upgrade the provider SDK, decoder, or retained dataset during an experiment.

## Separate the versions

- Python/C++ client releases define language interfaces, compatibility, and fixes.
- Historical/Live service releases define gateway behavior and HTTP/raw contracts.
- DBN format versions define binary metadata and record layouts.
- Data releases can regenerate historical dates or change normalization independently of the client.

The [official release page](https://databento.com/docs/release-notes) contains C++, Python, Rust, HTTP, Raw, and Data families. Each discovered route is listed in the catalog and coverage manifest. Historical entries are migration evidence, not a recommendation to use that version. Upcoming entries are not shipped releases.

## Upgrade procedure

1. Record the existing client/decoder versions, compiler/runtime, lockfile, dataset identity, and successful fixture outputs.
2. Read all relevant intervening client, service, DBN, and Data changes. Check field additions/removals, dtype width, symbol mapping, enum coverage, callback lifecycle, and normalization fixes.
3. Make a bounded dependency change and regenerate the lock/build definition. Preserve original raw bytes and manifests.
4. Replay a small retained fixture and compare identities, units, timestamps, record counts/order, and derived outputs. Investigate differences instead of normalizing them away.
5. If regenerated provider data changes experiment input, preserve both identities and document the change under the repository's experiment amendment rules.

The DBN version 3 transition is especially relevant to strategy-leg definitions and statistics quantity width. Do not use one hard-coded binary layout across all files. [DBN versioning](https://databento.com/docs/standards-and-conventions/databento-binary-encoding).

## Coverage boundaries

`coverage.json` records each discovered route, official title, retrieval/recovery state, source identity, upstream placeholder status, and local card path. `COVERAGE.md` summarizes it. The catalog is generated from retained documentation evidence, with concise original guidance and factual API/field inventories; source HTML is held separately in the Second Brain and excluded from the portable pack.

Some website links point to release sections that do not serve standalone rendered pages. Their content is recovered from matching sections of the rendered parent when available. Routes whose linked title cannot be matched are recorded as unresolved; do not infer their changes. Reconcile a refreshed official release page or official client changelog before relying on such an entry.

When refreshing, compare sitemap and navigation inventories, inspect changed sections, update both guides and coverage, and preserve the date and previous evidence. A cadence in this file does not schedule automatic work.
