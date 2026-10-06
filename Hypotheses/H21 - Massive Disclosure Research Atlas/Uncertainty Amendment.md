# H21 uncertainty amendment — calendar-year strata

This amendment is recorded before its implementation. It repairs the sampling clock for the completed v3 stock/disclosure comparisons without changing their inputs, fits, support rules, targets or point estimates. The original plan and original uncertainty attempt remain retained. This is development research, with no trading or alpha verdict.

## Why the amendment is needed

Source inspection showed that the original joint moving-block sampler draws calendar blocks over the whole 2022–2025 session grid, while each forecast comparison is evaluated within one calendar year. A draw can therefore omit an entire evaluation year. The inference implementation requires every draw to contain an estimate, so such omission invalidates even broad-panel annual comparisons. An artificial 1,003-session fixture, with the second year represented by sessions252–501 and seeds17–1016, produced4 omitted-year draws out of1,000 at length63 and15 at length126. No real uncertainty estimates or adjusted p-values were inspected to select this amendment.

## Fixed replacement

Use one joint issuer-history bootstrap in each draw, shared across all years and comparisons. Independently sample common circular moving calendar blocks **within each calendar year**, shared across all issuers. Sample exactly that year's number of sessions, using uniform block starts, wrap within the year, and truncate the last block to the year's length. Multiply issuer counts, calendar counts and the existing issuer/share-class weights. The year boundary is an explicit resampling boundary; blocks do not cross it. This conditions annual comparisons on their evaluation-year strata and assumes local dependence/exchangeability within each year. It is an approximate finite-sample procedure.

Retain9,999 draws per block length, primary63 sessions and sensitivity126, deterministic original seed formula, the complete original stock comparison family, centered/studentized Romano–Wolf stepdown, and all original support thresholds. Do not discard or redraw samples because a sparse event group has no weight. Such a group remains explicitly unsupported if any draw is undefined; report finite/missing draw counts, the declared family size and the actually eligible adjustment size. Pointwise intervals alone do not establish significance. Preserve raw descriptive means outside the inferential family, as in the original implementation.

## Execution and acceptance

Commit this document before the new method module. Use a separate, immutable uncertainty-stage manifest linked to the v3 parent manifest and this amendment. Reuse verified completed parent losses. Preserve the original sampler, draws, inference and scheduler receipts on Blue; never overwrite them. Write the amended draws and inference into a new sibling stage. All real computations run through scheduled HiPerGator jobs. Local checks use artificial data only, covering shared issuer counts, shared calendar blocks, every-year representation, determinism, empty inputs, unsupported sparse groups, null centering, family adjustment and transfer integrity.

Verify code/settings/parent hashes before execution and complete stage outputs after return. The PC may display a derivative that joins amended inference by exact comparison ID, while retaining the unchanged original stock report. The full499-search placebo and options requirements remain pending and cannot be replaced by this repair. The atlas stays partial until all declared stages have terminal accounting and verified evidence. No midnight completion guarantee follows from this amendment.
