# Massive options and buffered relationships: discovery plan

Oscar requested local installation/acquisition, complete variable and connection analysis at several times, HiPerGator execution, and a list of possible hypotheses. He also required new folders and a plan commit before any new data or methods, followed by a code commit when complete. This plan covers H12–H17 and supersedes the earlier discovery allowance for this new work. It is a completed **exploration specification**; it does not register a trading strategy. Earlier H03–H11 code/results predate this commit and remain dated exploratory history.

## Data and fixed acquisition choices

Keep the supplied static 100-company universe and the development interval January 1, 2024 through December 31, 2025. Preserve January–August 2026 and the judges' sealed window. Use the existing verified stock/session panel only as an auxiliary diagnostic; the core new source is Massive historical option contracts and daily bars. Keep the existing 65 source lead rows and deduplicate pricing anchors by ticker/CIK/accession while retaining every category. A missing mapped ticker remains an exclusion rather than a guessed identity.

For each eligible lead, pre is the latest observed exchange session strictly before filing_date. Assumed label observation begins at the first session on/after filing_date+1 calendar day; buffers are 1, 3 and 5 sessions after that starting session. These assumptions are sensitivities, not verified historical vendor release timestamps. A pre-filing observation is explicitly retrospective. The historical label service may not have existed then.

Use one ordinary anchor for the same issuer 84 sessions before each event where available, with no lead label within five sessions. Preserve unavailable controls instead of substituting future days. This anchor is a descriptive prior comparison, not a matched causal experiment. The full 2024–2025 stock/context panel supplies dense ordinary rows separately.

Query contract reference as_of the pre session. Maturity buckets are 21–45 days (target 30), 46–80 (target 60) and 90–180 (target 120). Choose the nearest target expiry with paired call/put strikes, then the paired strike nearest the unadjusted pre-session stock close. Acquire unadjusted daily stock bars for the already-mapped lead issuers before selecting strikes: the existing split-adjusted history could put pre-split strikes in the wrong units. This auxiliary stock-based selection is reported separately from the final Massive starter's parity-only replay. Retain contract attributes, multiplier/deliverables and actual achieved strike/expiry. Contracts with nonstandard multiplier/deliverables remain flagged; no strategy payoff is computed.

Download each selected leg's daily bars from ten sessions before pre through the earlier of expiry, 63 sessions after the last buffered observation, and December 31, 2025. Cache each exact request by SHA-256, retain immutable raw bytes and receipts, and reuse completed downloads. No current option snapshot becomes historical IV or OI. Contract selection is frozen before reading later prices. Use at most 2,000 new Massive requests at the documented existing conservative five-per-minute pace, resumable and with explicit partial status. If pagination/empty chains consume the cap, report incomplete coverage and do not silently thin the event sample.

A historical quote audit is bounded to the selected primary-120-day call/put on the pre session for each available anchor, at most 300 additional requests within the same overall cap. Query backward from that day's regular market close (using a verified calendar, including early closes) and retain both timestamps/ages/spreads. Daily-bar pricing and quote-audit coverage are separate, because last trades and quote mids are different marks. No quotation is assumed executable or synchronous without evidence.

Install Databento once in the shared root environment/lockfile and verify the installed version. Existing free metadata established OPRA minute quotes and historical OI schemas, with nonzero account estimates. Do not purchase time series without a concrete bounded request/cost cap. Massive-only acquisition and analysis continues independently; paid OI is an explicitly optional extension, not a prerequisite for completing this study.

## Variables, time points and outcomes

The fixed stock inputs are past 1/5/20-session return, past 20-session RMS volatility and volume state where already present. Disclosure groups are CFO appointment, CEO departure, earnings (quarterly/annual/preliminary), guidance (issuance/update or withdrawal), executive compensation change and debt issuance. Guidance categories do not encode a verified positive/negative sign. Context absence is zero only for an issuer whose interval was completely downloaded.

For dense relationships, input offsets are 0, 1, 3 and 5 sessions before observation; category recency windows are 5, 21 and 63 sessions, strictly earlier than observation. For options, fixed historical contract identities are compared at pre and each buffered post observation. Targets use the mandated 1, 2, 3, 5, 10, 21, 42 and 63-session horizons. Target-end dates enforce purging and the development boundary. Outcomes exceeding expiry or data coverage remain missing with a reason.

Options variables include call and put last-trade marks, summed premium divided by inferred spot, parity spot K*exp(-.04*T)+C-P, premium asymmetry (C-P)/(C+P), achieved strike/spot, DTE, leg volumes and age difference. The flat four-percent rate, no dividend adjustment and American exercise make parity spot approximate; retain nonpositive results as invalid. Premium-sum/sqrt(T) is a maturity-normalized price proxy, not a Black–Scholes IV or event-specific forecast. Targets are fractional same-contract leg/premium changes and auxiliary stock return/RMS volatility. No orders, positions, realized strategy returns or portfolio backtest is generated.

## Methods and support

Every declared cell receives measured/inconclusive/error status, sample/issuer/date counts, units and exclusions. Dense input correlations use Pearson/Spearman and known-coverage pairwise deletion. Continuous regressions scale on training data only; issuer demeaning and main effects precede interactions. Event groups need at least eight usable observations and three issuers; binary interactions need eight observations on each side. These thresholds are support rules, not statistical power guarantees.

Prediction uses three chronological development folds, actual target-end-date purging and fixed Ridge alpha 10. Compare identical evaluation rows for baseline versus augmented features; scale using each training fold only. Report paired MSE and relative improvement, fold signs and event-only counts. No tuning search or smaller-leaf rescue is introduced.

Use 999 deterministic issuer-cluster bootstrap draws for event contrasts when at least eight issuers exist, retaining duplicated sampled clusters; report descriptive means/medians and leave-one-issuer ranges. For dense time-series associations use contiguous blocks at least as long as the outcome horizon and at least four blocks. Report pointwise intervals with the total attempted family size and explicitly flag inability to resolve adjusted extreme tails. Do not present these discovery-selected intervals as independent confirmation. Descriptive cross-input correlations need no predictive claim.

## Computing and outputs

Write/download/prepare locally. Small fixtures may run on the PC; all actual statistics and model fits run inside HiPerGator compute allocations in Oscar's Blue storage. Freeze a credential-free code/config/input manifest and archive hashes before upload. Use capped job arrays for independent folders, a report dependent on their completion, and return all attempts, missingness, models' paired losses, uncertainty summaries and logs to the PC. Verify scheduler terminal states and archive/file hashes before calling the run complete.

Each new folder owns analysis.py and Research Log.md, sharing dependencies and provider adapters at root. The joint report must link tables by variable pair, offset/buffer, horizon, maturity, cohort, support, effect, uncertainty and robustness. Produce a candidate-hypothesis list grounded in measured evidence, including rejected/inconclusive directions and the further registered tests each candidate would need.

## Decision and failure criteria

A useful lead has sufficient independent issuer support, a plausible direction/price mechanism, consistent signs across adjacent times or horizons, and a positive chronological augmentation where a forecasting claim is made. A zero/unstable effect, stale-mark sensitivity, one-issuer dependence, incompatible controls, or lack of future validation counts against advancing it. A descriptive connection may still inform data selection when prediction fails. No threshold on an attractive discovery statistic establishes alpha.

A later strategy plan must separately choose a permitted shape (long call, covered call, protective put, collar or cash-secured put), executable information clock, fills/costs, risk/capital, benchmarks and falsification, and be committed before strategy code/backtests. An ATM straddle remains a diagnostic.

## Reading and provenance

This specification follows the root README, AGENTS.md, CONVENTIONS.md, PROJECT_STORY.md, Webull rules, backtest evidence contract, signal-reading/testing guides, quant-note template, hypothesis workflow and H03–H11 discovery histories. Provider routes are [Massive preparation](../massive/README.md), [Databento](../databento/README.md) and the parent [Massive track](../../../Massive%20Track/README.md), including challenge, research design, API reference and code-review limits. Existing findings are [v4 review](followup-findings.md); the earlier source/acquisition details are [cross-variable specification](cross-variable-options.md).

Primary endpoint sources are [historical contracts](https://massive.com/docs/rest/options/contracts/all-contracts), [daily option bars](https://massive.com/docs/rest/options/aggregates/custom-bars), [historical quotes](https://massive.com/docs/rest/options/quotes), and [Databento OPRA](https://databento.com/docs/venues-and-datasets/opra-pillar). Their fields/history are verified before adapting the new request code. Chat provenance is private project chat, October 3, 2026.
