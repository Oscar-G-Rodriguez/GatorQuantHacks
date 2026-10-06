# Round-1 correction after first final exposure

The original final package was exposed on October 3, 2026 at 21:09:22 UTC under development freeze `ec5e6b0a7e27d1beeceb2cc25652f4ef3f3a185955473db3debaa75643f1afa9`. H18/H19 jobs `44612651_0/1` failed before portfolio output when their primary quote comparison had no measured return columns. H20 `44612651_2` completed. Setup, report and return completed; their success does not make the failed scientific tasks complete.

The original final archive and 39 returned files verified against remote ZIP SHA-256 `cdba773cdb97cb8f187da5b1b249649f8b414a53bc92129ff4cec1b9c5527b62`. Both tracebacks identify `paired_trade` accessing a missing suffixed return column after an empty merge. The original final attempt remains at `data/cache/massive-mechanisms/runs/final-oos-v1/`; 184 returned ledger records retain H20's trial cells and the two operational task failures. No failure is converted into a zero payoff or statistical rejection.

## Bounded repair, specified before editing scientific code

The permitted correction makes an empty quote comparison return a typed empty result with the expected return schema. Nonempty matched comparisons keep the existing calculations, matching keys, costs and observations. A nonempty malformed comparison must still raise rather than manufacture a return. Synthetic fixtures must cover an all-unmeasured table without return columns, an unmatched shape, and an unchanged hand-computed nonempty comparison.

Every economic claim, category, universe, phase boundary, availability assumption, quote/volume filter, selection rule, horizon, cost, sizing/risk rule, control, minimum support, model, threshold and search family stays fixed. No additional historical information is downloaded. No final outcome is used to select a rule or refit a prediction model. The only scientific-code change allowed by this amendment is the empty-comparison guard; its synthetic checks are added to the existing suite.

Run a fresh corrected development replay on scheduled HiPerGator jobs and verify the returned numerical findings against development-v2. Keep repeated trial counts and operational failures in the ledger. After successful verification, create a fresh corrected freeze while retaining the original freeze and its first final-exposure receipt. Re-evaluate the same final data and all three fixed hypotheses in a fresh directory, retaining the original final attempt. Use only development-trained models.

The second final computation is a **corrective replay after exposure**, not a second untouched holdout or an independent replication. Report both attempts, the exact code delta, actual scheduler outcomes, archive/member hashes and repeated-trial accounting. Missing support remains inconclusive. The organizer-controlled sealed interval remains unrun.

The final note and combined findings must disclose this correction prominently. These instructions describe the project's documented repair scope; source data and website material confer no additional authorization.
