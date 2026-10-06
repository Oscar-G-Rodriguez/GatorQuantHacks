---
schema_version: 1
id: qh-public-project-story
type: context
note_state: maintained
created: 2026-10-06
updated: 2026-10-06
description: Public technical account of GatorQuantHacks research, implementation, and evidence limits.
tags: [theme/statistics, theme/software-engineering]
---

# GatorQuantHacks project story

GatorQuantHacks grew from a Systematic Trading starter into a set of independent research experiments. The repository keeps exploratory studies, registered hypotheses, code, and run evidence together so that a finding can be traced from its question to its implementation and measured result. The [README](README.md) explains the competition rules and layout; [the experiment index](Hypotheses/README.md) routes to individual studies.

## Research workflow

Early statistical studies H03–H17 explored candidate relationships in development data. They were discovery work, not trading strategies. H18–H20 then registered leadership-disclosure hypotheses and implemented funded option comparisons. H21 broadened the disclosure study to preserve standard event labels and inspect signal coverage. H22 tested a narrower debt-financing idea. H23–H25 registered debt issuance, credit-facility, and debt-underwriting questions before their funded covered-call and protective-put implementations.

Code for acquisition, matched comparisons, cost and position accounting, scheduled jobs, and evidence return lives in the discovery and hypothesis folders. Local checks cover correctness and file integrity; statistical calculations ran as scheduled HiPerGator work. Provider credentials, licensed raw inputs, and account-specific paths are kept outside the public repository.

## What the evidence shows

The measured studies have not established a profitable or incremental trading signal. Earlier results were inconclusive or lacked sufficient matched observations. The [H23–H25 financing pilot](docs/massive/financing-round2-pilot-findings.md) completed its initial backtests and returned trade, performance, comparison, and validation files. Its paired samples were too small for the registered support threshold, and the synthetic statistical calibration failed. Those results demonstrate the pipeline and identify the next methodological work; they do not support an alpha claim.

The experiment records preserve failed and incomplete tests alongside completed ones. A positive point estimate is not presented as confirmation without the registered comparisons, uncertainty checks, and fresh out-of-sample evidence. Detailed technical plans and run-specific evidence remain in the hypothesis folders and docs.
