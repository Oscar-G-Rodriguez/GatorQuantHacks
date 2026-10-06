"""Prepare standalone Overleaf sources from registered plans or verified returns.

This presentation utility does not compile a PDF, acquire data, fit models or
replay portfolios. The user selected Overleaf for compilation and export.
"""
from __future__ import annotations

import argparse
import csv
from datetime import date, datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
REGISTRATION = "b4159e2917248d588072ef5d9ae55bd88c3f8063"
EXPOSURE = "1d531db17acc3cd6f0df6cebdb2ff503b0d40b95"
STUDIES = {
    "H23": {
        "folder": "H23 - Debt Issuance Option Repricing",
        "title": "Debt issuance and option repricing",
        "filename": "h23-debt-issuance",
        "category": "debt_issuance",
        "delay": 1,
        "question": "Does a standard debt-issuance disclosure identify an option-overlay opportunity beyond prior prices and option premiums?",
        "mechanism": "Financing terms can change assessments of funding access and leverage. If funding uncertainty is resolved before option prices fully adjust, selling a call against funded shares may earn an unusual net increment. If new leverage or financing pressure instead leaves downside underpriced, purchased protection may reduce losses within a fixed premium budget. Neither implication follows automatically from the label.",
        "persistence": "The proposed persistence is different speeds of interpreting financing details. Call buyers seek upside exposure; put sellers accept contingent downside for premium. These participant descriptions are proposed mechanisms, not observed order-flow findings.",
        "coverage": "H21 served 526 debt-issuance filings across 87 issuers. These are raw source counts, not usable matched pairs or executed trades.",
        "failure": "Ordinary option carry, stock exposure, already priced financing information, late entry or friction can explain or remove the proposed increment. A completion or receipt-of-funds phrase is not required for primary eligibility.",
    },
    "H24": {
        "folder": "H24 - Credit Facility Risk Repricing",
        "title": "Credit facilities and risk repricing",
        "filename": "h24-credit-facility",
        "category": "credit_facility",
        "delay": 0,
        "question": "Does a credit-facility disclosure identify changes in residual funding risk that option premiums do not already incorporate?",
        "mechanism": "A facility may provide a liquidity buffer while also revealing reliance on credit or financing constraints. The covered-call branch tests whether greater predictability leaves upside premium unusually rich. The protective-put branch tests whether continuing funding risk leaves downside protection unusually useful after all premiums and costs. A label does not establish a draw, cash receipt or elimination of risk.",
        "persistence": "Uneven interpretation of access to credit and dependence on credit is the proposed persistence channel. Call buyers demand optional upside; put sellers accept contingent losses for compensation. Actual participant behavior is not observed in this study.",
        "coverage": "H21 served 154 credit-facility filings across 55 issuers. The source count does not establish option eligibility, drawn funding or net trading benefit.",
        "failure": "The mechanism fails if prior market and option information, ordinary option carry or a single stressed issuer explains the result, or if realistic lag and costs consume it. Agreements and amendments remain eligible under the served category.",
    },
    "H25": {
        "folder": "H25 - Debt Underwriting Interaction",
        "title": "Debt issuance with underwriting: an interaction test",
        "filename": "h25-debt-underwriting",
        "category": "debt_issuance AND underwriting_agreement, same CIK/accession",
        "delay": 1,
        "question": "Does a same-filing debt/underwriting conjunction add information beyond either component category for option overlays?",
        "mechanism": "Disclosing issuance and distribution arrangements together may clarify placement exposure while new obligations change equity risk. A covered call tests an unusual premium benefit from resolved uncertainty; a protective put tests useful insurance against remaining downside. The conjunction must add beyond each component. Two labels may simply describe ordinary features of one financing.",
        "persistence": "Different attention to financing headlines and combined transaction details is the proposed persistence channel. Call buyers and put sellers supply the respective risk-transfer counterparties. These descriptions remain hypotheses; same-filing co-occurrence does not prove one economic transaction or completed funding.",
        "coverage": "The exposed H21 example had 61/48/81 validation activations in 2023/2024/2025 across 41/33/56 issuers. These overlap component events and are not independent trade counts or a newly reconciled total cohort.",
        "failure": "The interaction fails if either component, redundant labels, ordinary financing exposure or one issuer/year explains it. Different accessions on the same date do not qualify. Missing component matches prevent an interaction claim without deleting eligible ordinary comparisons.",
    },
}
REFERENCES = [
    ("Gator Quant Hacks, Systematic Trading and Massive challenge, retained October 3 review.", "https://www.gqhacks.com/tracks/systematic-trading/massive"),
    ("Massive, disclosure taxonomy and supporting-excerpt methodology. Historical delivery clocks remain unverified.", "https://massive.com/blog/tagging-8-k-disclosures-with-ai-corporate-events-labelled-by-what-actually-happened"),
    ("Massive, historical contract reference; historical as-of selection and deliverables.", "https://massive.com/docs/rest/options/contracts/all-contracts"),
    ("Massive, option daily aggregates; access and coverage remain source-specific.", "https://massive.com/docs/rest/options/aggregates/custom-bars"),
    ("Massive, historical option quotes; synchronized quotes and complete pagination require separate verification.", "https://massive.com/docs/rest/options/quotes"),
    ("The Options Playbook, covered-call construction and continuing equity downside.", "https://www.optionsplaybook.com/option-strategies/covered-call"),
    ("The Options Playbook, protective-put construction and premium costs.", "https://www.optionsplaybook.com/option-strategies/protective-put"),
    ("Romano and Wolf, dependence-aware resampling and multiple-test methodology. Citation does not validate implementation.", "https://www.econ.uzh.ch/dam/jcr%3Affffffff-935a-b0d6-ffff-ffffd823d949/jasa.pdf"),
]


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def digest(path):
    with Path(path).open("rb") as stream:
        result = hashlib.file_digest(stream, "sha256").hexdigest()
    return result


def csv_rows(path):
    with Path(path).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def ascii_text(value):
    value = str(value).replace("\u2014", " - ").replace("\u2013", "-")
    value = value.replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"')
    return value


def tex(value):
    substitutions = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}
    escaped = "".join(substitutions.get(character, character) for character in ascii_text(value))
    return re.sub(r"\b[0-9a-f]{40,64}\b", lambda match: r"\nolinkurl{" + match.group(0) + "}", escaped)


def display(value, percent=False):
    if value in [None, "", "nan", "NaN"]:
        return "Unavailable"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return ascii_text(value)
    if not math.isfinite(number):
        return "Unavailable"
    return f"{number * 100:.3f}%" if percent else f"{number:.3f}"


def scheduler_jobs(value):
    """Read recorded terminal states; never infer success from a result file."""
    jobs = []
    if isinstance(value, dict):
        if value.get("state") is not None and value.get("exit_code") is not None:
            jobs.append(value)
        for child in value.values():
            jobs.extend(scheduler_jobs(child))
    elif isinstance(value, list):
        if len(value) >= 3 and re.fullmatch(r"[0-9]+(?:_[0-9]+)?(?:\.(?:batch|extern))?", str(value[0])) and isinstance(value[1], str) and isinstance(value[2], str) and re.fullmatch(r"[0-9]+:[0-9]+", value[2]):
            jobs.append({"job_id": value[0], "state": value[1], "exit_code": value[2]})
        else:
            for child in value:
                jobs.extend(scheduler_jobs(child))
    return jobs


def load_verified(run):
    run = Path(run).resolve()
    imported = read_json(run / "import-receipt.json")
    returned = read_json(run / "return.json")
    manifest = read_json(run / "manifest.json")
    if imported.get("manifest_id") != manifest.get("manifest_id") or returned.get("manifest_id") != manifest.get("manifest_id"):
        raise ValueError("Return/import/manifest identities differ")
    if manifest.get("registration_commit") != REGISTRATION:
        raise ValueError("Wrong hypothesis registration")
    canonical_manifest = json.dumps({key: value for key, value in manifest.items() if key != "manifest_id"}, sort_keys=True, separators=(",", ":"), allow_nan=False)
    if hashlib.sha256(canonical_manifest.encode()).hexdigest() != manifest["manifest_id"]:
        raise ValueError("Manifest content identity differs")
    if returned.get("registration_commit") != REGISTRATION or returned.get("code_commit") != manifest.get("code_commit"):
        raise ValueError("Returned registration or code identity differs")
    if imported.get("files") != returned.get("files"):
        raise ValueError("Imported and returned member maps differ")
    if not re.fullmatch(r"[0-9a-f]{64}", imported.get("sha256", "")) or not imported.get("verified_at"):
        raise ValueError("Whole-archive import verification receipt required")
    observation = read_json(run / "scheduler-observation.json")
    jobs = scheduler_jobs(observation)
    if not jobs or any(job["state"] != "COMPLETED" or job["exit_code"] != "0:0" for job in jobs):
        raise ValueError("Completed scheduler evidence required for displayed stage")
    file_hashes = returned.get("files", {})
    data = {"run": str(run), "manifest_id": manifest["manifest_id"], "archive_sha256": imported["sha256"], "scope": manifest.get("scope", "unknown"), "stage": returned.get("stage", "unknown"), "code_commit": manifest.get("code_commit"), "studies": {}, "file_hashes": {}}
    calendar_relative = "prepared/calendar.json"
    calendar_path = run / calendar_relative
    if calendar_relative not in file_hashes or digest(calendar_path) != file_hashes[calendar_relative]:
        raise ValueError("Verified portfolio calendar required")
    data["calendar_dates"] = read_json(calendar_path)["dates"]
    data["file_hashes"][calendar_relative] = file_hashes[calendar_relative]
    calibration_relative = "results/calibration/summary.json"
    data["calibration"] = None
    if calibration_relative in file_hashes:
        calibration_path = run / calibration_relative
        if digest(calibration_path) != file_hashes[calibration_relative]:
            raise ValueError("Calibration summary hash differs")
        calibration = read_json(calibration_path)
        if calibration.get("manifest_id") != manifest["manifest_id"]:
            raise ValueError("Calibration belongs to a different manifest")
        data["calibration"] = calibration
        data["file_hashes"][calibration_relative] = file_hashes[calibration_relative]
    for study in STUDIES:
        folder = run / "results" / study
        if not (folder / "summary.json").exists():
            data["studies"][study] = None
            continue
        tables = {}
        for name in ["summary.json", "performance.csv", "baseline_comparison.csv", "robustness.csv"]:
            path = folder / name
            relative = path.relative_to(run).as_posix()
            if relative not in file_hashes or digest(path) != file_hashes[relative]:
                raise ValueError("Unverified or changed result: " + relative)
            data["file_hashes"][relative] = file_hashes[relative]
            tables[name] = read_json(path) if name.endswith(".json") else csv_rows(path)
        summary = tables["summary.json"]
        if summary.get("registration_commit") != REGISTRATION or summary.get("study") != study:
            raise ValueError("Wrong study summary")
        if data["calibration"] is not None and summary.get("calibration_status") != data["calibration"]["status"]:
            raise ValueError("Study and calibration statuses differ")
        if summary.get("fresh_oos_status", "").lower().startswith("untouched") or str(summary.get("verdict", "")).upper().startswith("SUPPORTED"):
            raise ValueError("Exposed development cannot establish fresh confirmation")
        curves = []
        for relative, expected in file_hashes.items():
            if relative.endswith("/nav.csv") and (relative.startswith("tasks/") or relative.startswith("results/")):
                path = (run / relative).resolve()
                if not path.is_relative_to(run) or digest(path) != expected:
                    raise ValueError("Unverified NAV member")
                rows = [row for row in csv_rows(path) if row.get("study") == study and row.get("variant") == "primary"]
                curves.extend(rows)
                if rows:
                    data["file_hashes"][relative] = expected
        data["studies"][study] = {"summary": summary, "performance": tables["performance.csv"], "effects": tables["baseline_comparison.csv"], "robustness": tables["robustness.csv"], "curves": curves, "calendar_dates": data["calendar_dates"]}
    return data


def table(headers, rows, widths):
    columns = "".join("p{" + str(width) + r"\textwidth}" for width in widths)
    body = [r"\begin{tabular}{@{}" + columns + r"@{}}", r"\toprule", " & ".join(r"\textbf{" + tex(header) + "}" for header in headers) + r" \\", r"\midrule"]
    for row in rows:
        body.append(" & ".join(tex(cell) for cell in row) + r" \\")
    body.extend([r"\bottomrule", r"\end{tabular}", r"\par\smallskip"])
    return "\n".join(body) + "\n"


def primary_metrics(data):
    if not data:
        return []
    return [row for row in data["performance"] if row.get("variant") == "primary" and row.get("role") == "event" and row.get("year") in ["", "all", "overall", "2022-2025"] and row.get("stock_only", "").lower() not in ["true", "1"]]


def truth(value):
    return str(value).strip().lower() in {"true", "1", "yes"}


def figure(curves, performance, expected_dates):
    """Display only complete verified portfolios; never bridge unknown NAV."""
    groups = {}
    for row in curves:
        if row.get("role") != "event" or truth(row.get("stock_only")) or row.get("variant") != "primary":
            continue
        groups.setdefault(row.get("shape", "unknown"), []).append(row)
    complete = {}; unavailable = {}
    for shape in ["covered_call", "protective_put"]:
        rows = groups.get(shape, [])
        matching = [row for row in performance if row.get("shape") == shape and row.get("role") == "event" and row.get("variant") == "primary" and str(row.get("year")) == "all" and not truth(row.get("stock_only"))]
        if not rows:
            unavailable[shape] = "no verified primary event NAV series"
        elif not expected_dates or sorted(str(row.get("date") or "") for row in rows) != expected_dates:
            unavailable[shape] = "missing, duplicate or unexpected portfolio-calendar sessions"
        elif len(matching) != 1 or matching[0].get("status") != "completed_descriptive":
            unavailable[shape] = "complete matching event-portfolio performance unavailable"
        elif "full_nav_available" in matching[0] and not truth(matching[0]["full_nav_available"]):
            unavailable[shape] = "matching event performance marks full NAV unavailable"
        elif any(truth(row.get("unknown_nav")) for row in rows):
            unavailable[shape] = "at least one expected NAV is explicitly unknown"
        else:
            try:
                points = [(row["date"], float(row["nav"])) for row in rows]
                for day, value in points:
                    date.fromisoformat(day)
                    if not math.isfinite(value) or value <= 0:
                        raise ValueError("invalid NAV")
            except (KeyError, TypeError, ValueError):
                unavailable[shape] = "at least one expected NAV is missing, nonfinite or invalid"
            else:
                complete[shape] = sorted(points)
    if not complete:
        return {"latex": None, "unavailable": unavailable}
    output = [r"\begin{center}", r"\begin{tikzpicture}", r"\begin{axis}[width=0.88\textwidth,height=2.55in,date coordinates in=x,xlabel={Development dates},ylabel={Returned NAV (USD)},xticklabel=\year-\month,tick label style={font=\normalsize},label style={font=\normalsize},legend style={font=\normalsize,at={(0.5,-0.32)},anchor=north},scaled y ticks=false,yticklabel style={/pgf/number format/fixed},grid=major]" ]
    for shape, points in sorted(complete.items()):
        output.append(r"\addplot+[mark=none,line width=0.9pt] coordinates {" + " ".join(f"({day},{nav:.8f})" for day, nav in points) + "};")
        output.append(r"\addlegendentry{" + tex(shape.replace("_", " ")) + "}")
    output.extend([r"\end{axis}", r"\end{tikzpicture}", r"\end{center}"])
    return {"latex": "\n".join(output), "unavailable": unavailable}


def build(study, cfg, evidence=None):
    spec = STUDIES[study]
    data = evidence["studies"].get(study) if evidence else None
    summary = data["summary"] if data else None
    status = "INCONCLUSIVE - not yet evaluated" if not summary else str(summary["verdict"])
    scope = "Registered plan; numerical results pending" if not summary else f"Verified {summary.get('scope', evidence['scope'])} development output; fresh OOS unavailable"
    pages = []
    markdown = []
    def paragraph(value):
        markdown.append(value + "\n")
        return tex(value) + "\n\n"
    def heading(title):
        markdown.append("## " + title + "\n")
        return r"\section{" + tex(title) + "}\n"
    def paper_table(headers, rows, widths):
        def md_cell(value):
            return str(value).replace("|", "\\|").replace("\n", " ")
        markdown.append("| " + " | ".join(map(md_cell, headers)) + " |\n| " + " | ".join("---" for _ in headers) + " |\n" + "\n".join("| " + " | ".join(map(md_cell, row)) + " |" for row in rows) + "\n")
        return table(headers, rows, widths)
    p = r"\begin{center}{\Large\bfseries " + tex(spec["title"]) + r"}\par\smallskip " + tex(study + " | Massive track | October 4, 2026") + r"\end{center}" + "\n"
    markdown.append("# " + spec["title"] + "\n")
    p += heading("Summary")
    p += paragraph(spec["question"] + " Both covered-call and protective-put branches are fixed before implementation. " + scope + ". Verdict: " + status + ".")
    p += heading("Economic Hypothesis")
    p += paragraph(spec["mechanism"])
    p += paragraph(spec["persistence"] + " " + spec["failure"])
    p += paragraph("Complete economic registration " + REGISTRATION + " preceded the new implementation. Both branches are retained; no favorable issuer or option payoff chooses the primary rule.")
    p += heading("Data & Universe")
    p += paragraph("The static sponsor universe contains 100 companies. Financial inputs are Massive API data for January 1, 2022 through December 31, 2025: disclosures, historical standard contracts, nominal stock and option bars, available quotes, splits and dividends. " + spec["coverage"])
    p += paragraph("All 2022-2025 is exposed development. Earlier 2026 research is exposed and cannot provide fresh confirmation. Historical membership, service-release clocks and prior public-announcement timing remain limitations. The organizer's sealed interval stays excluded.")
    pages.append(p)

    p = heading("Methodology")
    p += paragraph("Signal: " + spec["category"] + ". Use every served primary label with no completion, receipt or excerpt-word gate. CIK/accession identity preserves bundles; the lexicographically first mapped share class is chosen before outcomes. Same-issuer decisions on one date are consolidated.")
    p += paragraph(f"Assume availability at the session aligned to filing plus one calendar day, then add {spec['delay']} session(s). Decide and select contracts at that close; enter at the next session close. Target expiry nearest 120 calendar days within 90-180 DTE and strikes near 5% OTM within one percentage point. Require verified 100-share deliverables. Buy 100 actual shares with one short call or one long put; exit ten sessions after entry.")
    p += paragraph("Match one same-issuer ordinary date 84-252 earlier sessions using strictly prior momentum, RMS volatility, volume and SPY conditions. Ordinary dates have no served bundle in their preceding five sessions. Compare complete event/ordinary strategy and stock-only quartets, with matched DTE, moneyness and premium calipers. H25 additionally uses earlier debt-only and underwriting-only controls; absent component matches prevent interaction claims.")
    p += paragraph("Per-side research friction is stock 6 basis points; options 5% of premium plus $0.65 per contract. These are assumptions, not measured spreads. Fresh synchronized quote checks remain separate. Charge all premiums, dividends and modeled assignment/corporate-action cash flows. Marked trade bars do not establish executable closing fills.")
    p += paragraph("All eight horizons (1, 2, 3, 5, 10, 21, 42, 63 sessions) and observable expiry are retained. Eleven variants per study cover costs, delay, maturity, moneyness, assignment and size. The shared S01-S12 specification controls training-only fitting, attribution, matching and exclusions; the 19-effect family uses 9,999 joint issuer/calendar draws at 63 and 126 sessions after synthetic-null calibration. Both lengths must pass. The focused 199 timing placebos do not replace H21's unfinished full-atlas placebo family.")
    if evidence and evidence.get("calibration"):
        calibration = evidence["calibration"]
        p += r"\subsection*{Measured calibration gate}" + "\n"
        markdown.append("### Measured calibration gate\n")
        p += paper_table(["Block sessions", "False rejections / datasets", "Allowed", "Status"], [[row["block"], f"{row['false_rejections']} / {row['datasets']}", row["maximum_allowed"], row["status"]] for row in calibration["blocks"]], [.18, .38, .13, .15])
        p += paragraph("This is synthetic estimator calibration, not market-performance evidence. Status: " + calibration["status"] + ". " + ("Failure blocks inferential significance and practical-bound claims. Descriptive pilot estimates remain visible; no seed retry or threshold change repairs this result." if calibration["status"] != "pass" else "A passing calibration alone does not establish a market signal or fresh confirmation."))
    pages.append(p)

    p = heading("Results")
    p += paragraph(scope + ". Performance below is sourced only from verified returned tables when supplied. Unrun, unsupported and unavailable quantities remain explicit. A positive funded stock return does not identify an event-timing contribution.")
    metrics = primary_metrics(data)
    lookup = {row["shape"]: row for row in metrics}
    metric_rows = []
    for label, key, percent in [("Annualized return", "annualized_return", True), ("Annualized volatility", "annualized_volatility", True), ("Sharpe", "sharpe", False), ("Maximum drawdown", "max_drawdown", True), ("Turnover", "turnover", True), ("Sessions", "sessions", False)]:
        metric_rows.append([label, display(lookup.get("covered_call", {}).get(key), percent) if data else "Pending", display(lookup.get("protective_put", {}).get(key), percent) if data else "Pending"])
    if data:
        stocks = {row["shape"]: row for row in data["performance"] if row.get("variant") == "primary" and row.get("role") == "event" and str(row.get("year")) == "all" and truth(row.get("stock_only"))}
        metric_rows.append(["Stock-only annualized return", display(stocks.get("covered_call", {}).get("annualized_return"), True), display(stocks.get("protective_put", {}).get("annualized_return"), True)])
    p += paper_table(["Primary event portfolio", "Covered call", "Protective put"], metric_rows, [.42, .23, .23])
    if summary:
        p += paragraph("Observed tasks: " + str(summary.get("observed_tasks", "unknown")) + "; planned: " + str(summary.get("planned_tasks", "unknown")) + ". Coverage: " + str(summary.get("coverage_status", "unknown")) + ". Calibration: " + str(summary.get("calibration_status", "unknown")) + "; block inference: " + str(summary.get("block_inference_status", "unknown")) + "; placebos: " + str(summary.get("placebo_status", "unknown")) + ".")
        effects = summary.get("primary_effects", [])
        if effects:
            names = {"overlay_increment": "Call overlay", "strategy_increment": "Call strategy", "hedge_increment": "Put hedge", "event_downside_reduction": "Put downside", "event_return_drag": "Put return drag"}
            p += paper_table(["Primary effect / comparator", "Estimate (pp)", "Pairs / issuers"], [[names.get(row.get("metric"), row.get("metric", "unknown")) + " / " + row.get("comparator", "unknown").replace("_", " "), display(row.get("estimate"), True).removesuffix("%"), f"{row.get('pairs', 'N/A')} / {row.get('issuers', 'N/A')}"] for row in effects], [.53, .20, .18])
            p += paragraph("Effect estimates are percentage-point differences over the ten-session horizon, not annualized alpha. Evidence statuses: " + ", ".join(sorted({row.get("status", "unknown").replace("_", " ") for row in effects})) + ". The registered overall floor is 30 pairs across eight issuers. This coverage-only pilot cannot replace the full cohort.")
    else:
        p += paragraph("No scheduled round-2 trading result has been imported for this paper draft. Trade counts, matched support, paired option outcomes, uncertainty, calibration and portfolio metrics are pending. Zero is not substituted for missing evidence.")
    p += paragraph("Fresh OOS: unavailable. All historical output in this round is development evidence. A registered failure is retained as rejected; missing support or required evidence is inconclusive. No supported incremental-signal verdict is permitted from exposed history alone.")
    pages.append(p)

    p = r"\subsection*{Results continued: response, curves and robustness}" + "\n"
    markdown.append("### Results continued: response, curves and robustness\n")
    figure_result = figure(data["curves"], data["performance"], data["calendar_dates"]) if data else {"latex": None, "unavailable": {}}
    plot = figure_result["latex"]
    if plot:
        p += plot
        p += paragraph("Figure: returned primary event-portfolio NAV, including the run's cash and cost convention. The curve is a display of retained scheduled output; it is not an OOS result, ablation test or independent replication. Baseline tables retain the comparable stock-only and ordinary-date evidence.")
    else:
        p += paragraph("No equity curve is shown: there is no verified complete eligible NAV series. Missing or unknown values are never dropped to connect the remaining dates. No performance statistic is inferred from a displayed curve.")
    if figure_result["unavailable"]:
        p += paragraph("Unavailable curves: " + "; ".join(shape.replace("_", " ") + " - " + reason for shape, reason in figure_result["unavailable"].items()) + ".")
    if plot:
        p += paragraph("Fixed advancement thresholds: call overlay lower bound >0.10 percentage points and strategy increment >0; put hedge benefit >0, downside reduction >0.25 points and return drag >-0.50 points. Overall support is 30 pairs/eight issuers; annual support ten pairs/five issuers. H25 additionally requires positive contrasts against both components. All numbers must come from the returned comparison tables.")
    else:
        p += paper_table(["Predeclared contrast", "Development advancement criterion"], [["Covered call", "Simultaneous lower bounds: overlay increment >0.10 percentage points; strategy increment >0."], ["Protective put", "Lower bounds: additional hedge benefit >0; event downside reduction >0.25 percentage points; return drag >-0.50 percentage points."], ["Support", "At least 30 pairs / 8 issuers overall; annual cells 10 pairs / 5 issuers."], ["H25 interaction", "Positive simultaneous component contrasts against debt-only and underwriting-only observations."]], [.25, .65])
    p += paragraph("Horizon and robustness results remain pending unless returned. Report every registered horizon, failed mark, expiry boundary, base/doubled cost, extra delay, 30/60-day maturity, 3%/10% OTM, assignment and ten-contract variant. These are diagnostics; they do not authorize a favorable variant to replace the primary.")
    p += paragraph("Prior discovery: financing examples improved full-feature-group absolute-return prediction in each evaluation year, but all displayed adjusted p-values were 1 at both block lengths. Exposure commit " + EXPOSURE + " records that selection. H21's 350 cross-year-positive groups overlap; none passed the complete declared screen.")
    pages.append(p)

    p = heading("Risk Management")
    p += paragraph("Each study/shape starts with $1 million, zero cash yield, no leverage and one 100-share/one-contract unit. Name exposure is capped at 5% of NAV; funded-share gross/net and sector caps are 20%. Unknown sectors share one conservative bucket. No overlapping position in an issuer is opened. A 5% drawdown requests next-feasible liquidation and a 21-session entry cooldown. Gaps and missing exits can defeat timely liquidation.")
    p += paragraph("Covered calls retain equity downside and cap upside. Protective puts cost premium and depend on valid contract/action/settlement accounting. Modeled early assignment is an assumption, with a conservative sensitivity. Unresolved actions or long mark gaps suppress reliable full-period metrics; they are not filled from future prices.")
    p += heading("Liquidity & Capacity")
    p += paragraph("Eligibility uses only completed pre-decision volume history. Bounded quote checks require fresh, synchronized, positive sized quotes with registered spread limits. Per-side fees and impact stress are separate from observed bid/ask. Daily volume and snapshot size do not establish intraday depth. Ten-contract stress remains a scenario; dollar capacity cannot be claimed before a supported net benefit and measured liquidity exist.")
    p += heading("Limitations & Next Steps")
    p += paragraph("Standard labels can be heterogeneous, and same-filing labels may describe different economic transactions. Matching is observational rather than causal. Static membership, historical label delivery, announcement timing and approximate execution remain limitations. Earlier H21/H22 selection, failed inference and inconclusive outcomes are preserved. Complete option coverage, calibrated inference, placebos and genuinely unseen confirmation are required before advancement.")
    p += paragraph("PC work creates code, downloads, immutable packages and paper sources. Actual matching, backtests and inference use HiPerGator allocations; returned archives, member hashes and scheduler states must verify. Overleaf compiles and exports this standalone source. The note is a pending research draft until those evidence and compilation checks complete; it is not a competition-submission receipt.")
    pages.append(p)

    references = r"\section*{References and reproduction record}" + "\n"
    markdown.append("## References and reproduction record\n")
    for description, url in REFERENCES:
        references += tex(description) + r"\par\url{" + url + r"}\par\medskip" + "\n"
        markdown.append("- [" + description + "](" + url + ")\n")
    references += paragraph("Local authoritative specification: docs/massive/financing-round2-plan.md and config/financing-round2.json, with this folder's Hypothesis.md and Research Log.md. The Webull/Backtrader starter and Massive starter supply attributed infrastructure/shape references; H22 funded-share accounting is reuse context, not evidence for these hypotheses.")
    references += paragraph("Paper reproduction: scripts/build_financing_paper_sources.py without --run creates the registered pending draft. With --run it requires the actual verified import, returned member hashes and completed scheduler observation before displaying returned metrics. Upload the generated single-file main.tex ZIP to Overleaf; no key, raw provider object or environment is included.")
    if evidence:
        references += paragraph("Returned run scope: " + evidence["scope"] + "; stage: " + evidence["stage"] + ". Manifest " + evidence["manifest_id"] + ". Verified archive SHA-256 " + evidence["archive_sha256"] + ".")
    references += paragraph("Credits: organizer source material, Massive market data, documented option shapes and cited methods informed the study. OpenAI Codex assisted with research/code/documentation and LaTeX preparation. The team is responsible for the code and claims. References are outside the main five-page budget; decisive evidence belongs in the main text. The starter's shorter-write-up instruction and reviewed five-page guidance remain a documented source conflict.")
    preamble = r"""\documentclass[11pt,letterpaper]{article}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{lmodern}
\usepackage[margin=1in]{geometry}
\usepackage{microtype,amsmath,booktabs,array,xurl,hyperref,fancyhdr,titlesec}
\usepackage{tikz,pgfplots}
\usepgfplotslibrary{dateplot}
\pgfplotsset{compat=1.18}
\hypersetup{hidelinks}
\urlstyle{same}
% PDF points (bp) meet the literal minimum; article[11pt] is only nominal.
\renewcommand{\normalsize}{\fontsize{11bp}{13.6bp}\selectfont}
\let\small\normalsize
\let\footnotesize\normalsize
\let\scriptsize\normalsize
\let\tiny\normalsize
\AtBeginDocument{\normalsize}
\setlength{\parindent}{0pt}
\setlength{\parskip}{4pt}
\setlength{\tabcolsep}{4pt}
\renewcommand{\arraystretch}{1.12}
\titleformat{\section}{\large\bfseries}{\thesection.}{0.5em}{}
\titleformat{\subsection}{\normalsize\bfseries}{\thesubsection.}{0.5em}{}
\titlespacing*{\section}{0pt}{8pt}{4pt}
\titlespacing*{\subsection}{0pt}{6pt}{4pt}
\pagestyle{fancy}
\fancyhf{}
\fancyfoot[L]{\normalsize Financing round 2 | Development evidence}
\fancyfoot[R]{\normalsize\thepage}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0pt}
\begin{document}
"""
    source = preamble + "\n\\clearpage\n".join(pages) + "\n\\label{mainend}\n\\clearpage\n" + references + "\n\\end{document}\n"
    return source, "\n".join(markdown)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, help="Imported returned run with manifest, return.json, import-receipt.json and scheduler-observation.json")
    parser.add_argument("--study", choices=STUDIES, action="append", help="Default: all three studies")
    parser.add_argument("--bundle-dir", type=Path, default=ROOT / "data/cache/transfer-bundles/financing-papers")
    args = parser.parse_args()
    cfg = read_json(ROOT / "config/financing-round2.json")
    if cfg["primary_horizon"] != 10 or cfg["fresh_final_oos_available"] or cfg["primary_family_size"] != 19:
        raise ValueError("Registered paper settings differ")
    evidence = load_verified(args.run) if args.run else None
    args.bundle_dir.mkdir(parents=True, exist_ok=True)
    outputs = []
    for study in args.study or STUDIES:
        spec = STUDIES[study]
        source, markdown = build(study, cfg, evidence)
        folder = ROOT / "Hypotheses" / spec["folder"]
        source_path = folder / "Paper.tex"
        source_path.write_text(source, encoding="utf-8", newline="\n")
        markdown_path = folder / "Paper.md"
        markdown_path.write_text(markdown, encoding="utf-8", newline="\n")
        archive = args.bundle_dir / (spec["filename"] + "-overleaf.zip")
        staging_source = args.bundle_dir / study / "main.tex"
        staging_source.parent.mkdir(parents=True, exist_ok=True)
        staging_source.write_bytes(source_path.read_bytes())
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
            bundle.write(source_path, "main.tex")
        outputs.append({"study": study, "source": str(source_path), "source_sha256": digest(source_path), "markdown": str(markdown_path), "staging_main": str(staging_source), "bundle": str(archive), "bundle_sha256": digest(archive), "bundle_members": ["main.tex"], "status": "source generated; Overleaf compilation/export and PDF visual QA pending"})
    verification = {"created_at": datetime.now(timezone.utc).isoformat(), "registration_commit": REGISTRATION, "generator_sha256": digest(Path(__file__)), "settings_sha256": digest(ROOT / "config/financing-round2.json"), "mode": "verified-return presentation" if evidence else "registered pending draft", "pdf_created_locally": False, "overleaf_compilation": "pending", "main_page_limit": 5, "minimum_font_points": 11, "page_size": "US Letter", "margins_inches": 1, "evidence": evidence and {key: value for key, value in evidence.items() if key != "studies"}, "outputs": outputs}
    verification_path = ROOT / "docs/massive/financing-round2-paper-verification.json"
    if verification_path.exists():
        previous = read_json(verification_path)
        verification["overleaf_history"] = previous.get("overleaf_history", [])
        verification["source_history"] = previous.get("source_history", []) + [{key: previous[key] for key in ["created_at", "generator_sha256", "settings_sha256", "mode", "outputs", "evidence"] if key in previous}]
    else:
        verification["overleaf_history"] = []
        verification["source_history"] = []
    verification_path.write_text(json.dumps(verification, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(verification))


if __name__ == "__main__":
    main()
