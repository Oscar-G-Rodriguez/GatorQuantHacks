---
schema_version: 1
id: guide-gqh-submission-references-credits-20261003
type: guide
note_state: maintained
created: 2026-10-03
updated: 2026-10-03
description: Preliminary submission references and source credits across eleven QuantHacks chats, with a deduplicated URL inventory and explicit evidence boundaries.
tags: [theme/statistics, theme/software-engineering]
projects: ['[[Projects/GatorQuantHacks/Project Hub]]']
---

# QuantHacks references and credits

This inventory preserves the sources behind all eleven chats Oscar selected on October 3. [SOURCE_INVENTORY.csv](SOURCE_INVENTORY.csv) contains **627 distinct public URLs**, with chat provenance, retained source-register paths and review boundaries. The Overleaf paper (private Overleaf copy) and [local source](main.tex) contain a smaller preliminary bibliography for the Massive challenge and statistical methods. The economic hypothesis and results remain open.

A collected URL can be a reviewed source, an abstract, a documentation lead or an unsuccessful retrieval. The CSV does not upgrade those into fully read or implemented sources. Retained registers record the original depth. A source mentioned in an earlier idea does not automatically belong in the final paper. Add an in-text citation when a completed section uses its definition, method, code or claim, then retain the corresponding bibliography entry.

## Coverage of the selected chats

The app's accessible history was paged to its end for each selected chat, as observed on October 3. These are returned turn summaries and visible source items, rather than retained full conversation transcripts; unavailable or truncated content can omit links. Only public user/assistant references and source requests were extracted. The collection also includes 41 retained source-register or candidate-matrix files. URL counts overlap across chats; their sum is not the distinct total.

| Chat title returned by the app | Public URLs traced | Reading route |
| --- | --- | --- |
| Record QuantHacks ideas and API | 58 | [Ideas, public data endpoints and discarded sports-sponsorship ideas](../../Ideas%20and%20Data%20Endpoints.md) |
| Create Databento docs READMEs | 9 | [Databento catalog and academic background](../docs/databento/README.md) |
| Quant hacks prep | 77 | [Strategy, methodology, data and learning registers](../../../../Sources/QuantHacks/Methodology%20Sources.md) |
| quanthacks | 14 | [Massive researchers, working papers and alternative data](../../../../Sources/QuantHacks/2026-10-02%20-%20Massive%20Research%20Sources.md) |
| Document Massive API sections | 16 | [Provider endpoint review and statistical discovery methods](../docs/discovery/README.md) |
| Explore corn futures A7 signal | 20 | [Corn, related futures and agriculture releases](https://databento.com/docs/venues-and-datasets/glbx-mdp3) |
| Find Massive trading signals | 39 | [Sponsor signal candidates and public documentation](../../../../Sources/QuantHacks/2026-10-02%20-%20Sponsor%20Signal%20Discovery%20Sources.md) |
| Find unusual data with Massive | 24 | [Agriculture, corporate-event and market-structure candidates](../../../../Sources/QuantHacks/2026-10-02%20-%20Niche%20Sponsor%20Data%20Sources.md) |
| Find sports outcome prediction repos | 28 | [College-football and Formula 1 repositories reviewed as separate ideas](https://github.com/carterptull/blitzcast) |
| Add RPEO rules and hypothesis scaffo | 7 | [Track rules, starter attribution and fair-test references](../docs/RESEARCH_SOURCES.md) |
| Document Massive options track | 19 | [Massive challenge, notebook, paper outline and API references](../../Massive%20Track/Source%20Index.md) |

The CSV removes fragment anchors and Massive plan-selector variants, merges repeated URLs and retains multiple provenance records. Its group column is coarse navigation inferred from the domain, not a verified classification of each source. Credentials, authenticated cluster URLs, private Overleaf/Notion links and raw Massive API requests are excluded. Failed or superseded public leads remain identifiable through their original chat/register. Provider catalogs are linked below; this inventory is not a second complete crawl of every catalog page.

## Challenge and instrument references

| Reference | What it supports | Current treatment |
| --- | --- | --- |
| [Gator Quant Hacks Systematic Trading](https://www.gqhacks.com/tracks/systematic-trading) | Main rubric, note outline, attribution and reproduction requirements | Page visibly reviewed October 3; preliminary paper reference |
| [Gator Quant Hacks Massive challenge](https://www.gqhacks.com/tracks/systematic-trading/massive) | Category-to-options question, fixed horizons, baseline, OOS, costs, sensitivity and sealed replay | Page visibly reviewed October 3; preliminary paper reference |
| [Official Massive starter ZIP](https://www.gqhacks.com/massive/gqh-massive-8k-starter-kit.zip) and [notebook](https://www.gqhacks.com/massive/gqh-massive-8k-options-starter.ipynb) | Source of the supplied example pipeline and its assumptions | Retained and statically inspected; upstream sample findings belong to the starter |
| [Massive 8-K Disclosures](https://massive.com/docs/rest/stocks/filings/8-k-disclosures) | Record grain, filing identity, dates, supporting excerpts and taxonomy filters | Body refreshed October 3 through its plan-selector URL |
| [Massive disclosure categories](https://massive.com/docs/rest/stocks/filings/disclosure-categories) | Category definitions | Retained documentation and taxonomy evidence; version needed in the final data manifest |
| [Massive All Contracts](https://massive.com/docs/rest/options/contracts/all-contracts) | Historical as-of lookup and contract characteristics | Refreshed October 3 |
| [Massive Custom Bars](https://massive.com/docs/rest/options/aggregates/custom-bars) | Option OHLC, volume and absent-bar semantics | Refreshed October 3 |
| [Massive tagging article](https://www.massive.com/blog/tagging-8-k-disclosures-with-ai-corporate-events-labelled-by-what-actually-happened) | Label construction, quality checks, retrospective coverage and availability discussion | July 22, 2026 article; refreshed October 3 |
| [The Options Playbook strategy library](https://www.optionsplaybook.com/option-strategies) | Strategy definitions and payoff construction | Library refreshed October 3; selected individual strategy page should be cited once chosen |
| [SEC EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) | Filing-source identity and timestamp retrieval route | Retained documentation; cite the actual acceptance-time method if used |
| [NYSE hours and calendars](https://www.nyse.com/trade/hours-calendars) | Sessions and official market calendar reference | Retained lead; match the final calendar implementation to its source |
| [Devpost event](https://gqhacks.devpost.com/) | Submission portal and event metadata | Current portal differs from an older organizer cutoff; preserve source distinction |

The official pages specify a five-page main note; the retained Massive notebook separately says two pages. That discrepancy remains unresolved. The bibliography does not settle it. [Submission and Event Reference](../../Massive%20Track/Submission%20and%20Event%20Reference.md) retains the source passages and timing distinctions.

## Statistical and economic research references

These sources inform research preparation and the discovery guides. Their inclusion records provenance, not a claim that every method is implemented or every paper replicated.

| Source | Relevance | Inspection evidence |
| --- | --- | --- |
| Halbert White (2000), [A Reality Check for Data Snooping](https://www.ssc.wisc.edu/~bhansen/718/White2000.pdf) | Selection after searching many candidates | Earlier method review; title, author and publication metadata refreshed October 3 |
| David H. Bailey and Marcos López de Prado (2014), [The Deflated Sharpe Ratio](https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf) | Selection bias, backtest overfitting and non-normality | July 31, 2014 version metadata refreshed; no DSR result asserted |
| Campbell R. Harvey, Yan Liu and Heqing Zhu (2014), [NBER Working Paper 20592](https://www.nber.org/papers/w20592) | Multiple testing in expected-return research | Indexed primary metadata; direct landing-page retrieval failed with 403 |
| Kacper Chwialkowski and Arthur Gretton (2014), [A Kernel Independence Test for Random Processes](https://proceedings.mlr.press/v32/chwialkowski14.html) | Dependence-aware nonlinear testing | Proceedings metadata and abstract refreshed; no claim of exact method replication |
| [arch time-series bootstraps](https://arch.readthedocs.io/en/stable/bootstrap/timeseries-bootstraps.html) | Block and stationary bootstrap references | Documentation refreshed; arch is a method reference, not a declared runtime dependency |
| [scikit-learn TimeSeriesSplit](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html) and [common pitfalls](https://scikit-learn.org/stable/common_pitfalls.html) | Chronological validation and fitted-transform leakage | Existing register plus refreshed splitter documentation |
| [scikit-learn QuantileRegressor](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.QuantileRegressor.html) | Quantile-response discovery | Referenced in the development-method chat |
| [scikit-learn mutual_info_regression](https://scikit-learn.org/stable/modules/generated/sklearn.feature_selection.mutual_info_regression.html) | Nonlinear dependence estimates | Referenced in the development-method chat |
| [SciPy pearsonr](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.pearsonr.html) and [spearmanr](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.spearmanr.html) | Linear and rank association | Official API references in the method chats; CSV preserves a separate earlier spearmanrho lead |
| [statsmodels multipletests](https://www.statsmodels.org/stable/generated/statsmodels.stats.multitest.multipletests.html) and [fdrcorrection](https://www.statsmodels.org/stable/generated/statsmodels.stats.multitest.fdrcorrection.html) | Multiple-comparison correction | multipletests refreshed; references do not establish use of statsmodels in the runtime |
| [statsmodels HAC covariance](https://www.statsmodels.org/stable/generated/statsmodels.stats.sandwich_covariance.cov_hac.html) | Serial-dependence-aware covariance | Retained method review |
| [Kenneth R. French Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html) | Factor-definition and benchmark candidates | Library refreshed; factor datasets/regressions were not established by the earlier reference review |
| [Grossman and Stiglitz (1980)](https://www.pims.math.ca/files/Grossman_Stiglitz1980.pdf) | Information and market-efficiency background | Lead from Create Databento docs READMEs; retain as background |
| [Economic Links and Predictable Returns](https://people.stern.nyu.edu/afrazzin/pdf/Economic%20Links%20and%20Predictable%20Returns%20-%20Cohen%20and%20Frazzini.pdf) | Customer–supplier information transmission | Primary abstract/data description in the retained Massive register; no panel acquired |
| [Lazy Prices](https://www.nber.org/papers/w25084) | Textual-change information | Lead plus selected sections of the separately retained Harvard PDF |
| [On the Capital Market Consequences of Big Data](https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/on-the-capital-market-consequences-of-big-data-evidence-from-outer-space/2F5F99D68D1F8940F61578F198D6C005) | Satellite-data precedent | Retained abstract/metadata evidence, not a commercial imagery replication |
| [Does Academic Research Destroy Stock Return Predictability?](https://www.onlinelibrary.wiley.com/doi/full/10.1111/jofi.12365) | Publication and predictability decay | Lead from Create Databento docs READMEs; final citation requires matching the version actually used |

The fuller [methodology register](../../../../Sources/QuantHacks/Methodology%20Sources.md), [strategy register](../../../../Sources/QuantHacks/Strategy%20Sources.md), [Massive researcher and paper register](../../../../Sources/QuantHacks/2026-10-02%20-%20Massive%20Research%20Sources.md) and [French reference review](../../../../Sources/QuantHacks/2026-10-03%20-%20Ken%20French%20Library%20and%20Signal%20Testing%20References.md) preserve the earlier review limits. Researcher homepages support discovery and attribution leads; cite the actual paper when a final claim depends on it.

## Provider documentation and other data ideas

[Massive's catalog](../../Massive%20Track/Endpoint%20Discovery.md), the [REST endpoint review](../../../../Sources/Web_Clips/2026-10-03%20-%20Massive%20REST%20API%20Endpoint%20Review.md) and the [Databento implementation pack](../docs/databento/README.md) preserve provider documentation, route inventories and unresolved coverage. The CSV links their primary public references. Databento documentation work does not establish licensed Databento data use in a Massive submission.

Earlier candidate work also used [USDA WASDE](https://www.usda.gov/oce/commodity/wasde), [USDA export sales](https://fas.usda.gov/programs/export-sales-reporting-program), [CFTC COT](https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm), CME contract/mechanics pages, EIA releases, SEC filings, FDA/openFDA, EPA ECHO, OSHA, WARN, USAspending, Federal Register, ClinicalTrials.gov, USGS, NOAA, NASA FIRMS, Wikimedia, GDELT and Google Trends documentation. The [sponsor-signal register](../../../../Sources/QuantHacks/2026-10-02%20-%20Sponsor%20Signal%20Discovery%20Sources.md), [niche-source register](../../../../Sources/QuantHacks/2026-10-02%20-%20Niche%20Sponsor%20Data%20Sources.md) and CSV retain individual routes.

The corn and related-market proposals belong to the broader Systematic Trading preparation. Their economic relationships remain proposals unless supported by actual tests. Sports-sponsorship ideas marked scrapped in [Ideas and Data Endpoints](../../Ideas%20and%20Data%20Endpoints.md) retain their historical sources without reopening those ideas.

## Sports model repository references

The selected sports chat reviewed these public repositories. No adoption of their code or reproduction of author-reported accuracy is established by this inventory. Preserve owner/project attribution if any code is subsequently borrowed, and use its actual license.

- [carterptull/blitzcast](https://github.com/carterptull/blitzcast)
- [sportsdataverse/cfbfastR-cfb-data](https://github.com/sportsdataverse/cfbfastR-cfb-data)
- [sportsdataverse/cfbfastR](https://github.com/sportsdataverse/cfbfastR)
- [bszek213/college_football_machine_learning](https://github.com/bszek213/college_football_machine_learning)
- [T-Burton-ND/TDNet](https://github.com/T-Burton-ND/TDNet)
- [zachringnight/cfbmodel](https://github.com/zachringnight/cfbmodel)
- [omkargadute/f1-predictor](https://github.com/omkargadute/f1-predictor)
- [Om-Ravindra-Patil/F1-Race-Predictor](https://github.com/Om-Ravindra-Patil/F1-Race-Predictor)
- [Matenco/f1-race-predictor](https://github.com/Matenco/f1-race-predictor)
- [enoyola/f1-race-predictor](https://github.com/enoyola/f1-race-predictor)

The chat also used [CollegeFootballData tiers](https://collegefootballdata.com/api-tiers), [cfbfastR model documentation](https://cfbfastr.sportsdataverse.org/articles/college-football-win-probability-model-fundamentals.html) and [OpenF1](https://openf1.org/). These are separate background leads, not sources for a final 8-K options claim.

## Source and software credits

| Contributor or tool | Verified contribution | Attribution treatment |
| --- | --- | --- |
| Gator Quant Hacks and Massive's data team | Official Massive 8-K/options starter and challenge materials | Credit the upstream starter, then explain actual extensions in the final note and README |
| Organizer-hosted Webull/Backtrader starter | Shared integration, examples and sample report retained/adapted in this repository | Keep upstream example/sample attribution; [RESEARCH_SOURCES.md](../docs/RESEARCH_SOURCES.md) records adapted files |
| Massive | Filing taxonomy and market-data documentation; development data acquisition recorded separately in the discovery guide | Cite exact endpoints and final data manifest; do not imply option prices were already used because stock development data exist |
| Databento | Documentation underlying the agent implementation pack and futures leads | Credit documentation work; actual licensed data use remains separate |
| The Options Playbook | Standard strategy definitions and payoff explanations used in challenge preparation | Cite the selected strategy's own page in the completed note |
| Backtrader, Webull OpenAPI Python SDK, python-dotenv and Plotly | Declared dependencies inherited or used by the shared starter | Final runtime attribution follows actual code use and locked versions |
| NumPy, pandas, SciPy, scikit-learn and threadpoolctl | Declared scientific dependencies; discovery code imports NumPy/pandas/threadpoolctl directly | Credit applicable implementations when final methods are known; declarations alone do not prove every library was used |
| Python and uv | Repository runtime and dependency workflow | [pyproject.toml](../pyproject.toml), [uv.lock](../uv.lock) and [CONVENTIONS.md](../CONVENTIONS.md) retain version/reproduction evidence |
| UF Research Computing and HiPerGator | Infrastructure and workflow documentation; scheduled discovery execution is recorded in [the discovery guide](../docs/discovery/README.md) and [project story](../PROJECT_STORY.md) | Acknowledge actual computation once its returned evidence is used in the note; do not infer allocation/funding details |
| OpenAI Codex | Assistance with source research, documentation and LaTeX preparation in this chat | Disclose assistance factually; the team remains responsible for final code and claims |
| Overleaf | Paper editing and compilation | Editing tool credit; not an author or analytical method |
| Human authors and team members | Names and contribution breakdown not selected in this paper | Add only verified names and actual contributions before submission |

The Massive ZIP's retained SHA-256 is `057f66db00a52af8da1ffb6ef9e47a6b26b9c66996027af919aca581106669af`; the Webull ZIP's is `d51695a6d549067216083fa6da0c59e3e0533c1b2a914cca76788cca7db8d08e`. The root MIT license identifies Oscar Rodriguez's repository copyright; it does not replace an upstream package, code, paper or data license. Keep upstream notices with any reused material. Reading an external repository alone is not code reuse.

## Final citation mapping

For each completed section, record the claim or method, source identifier, exact version or dataset date, and where the code implements it. Keep licensed raw data and credentials outside Git. Select bibliography entries based on actual use, preserve the broader inventory for provenance, and remove unused preliminary paper entries before final submission.

No strategy, paper result or human contribution was selected by this reference collection. The saved screenshot selecting the eleven chats is linked from the [project source index](../../Source%20Index.md).
