"""H21 event identities, session clocks and fold-local sparse disclosure features."""
from __future__ import annotations

import itertools
from collections import defaultdict

import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
import exchange_calendars as xcals

CONTROLS = ["return1", "return5", "return20", "return60", "vol20", "vol60", "log_adv20", "volume_state", "market_return5", "market_return20", "market_vol20"]
KINDS = ["return", "absolute", "volatility", "downside"]


def sessions(config):
    calendar = xcals.get_calendar("XNYS", start=config["start"], end=config["end"])
    grid=pd.DatetimeIndex(calendar.sessions).tz_localize(None)
    return grid[(grid>=pd.Timestamp(config["start"]))&(grid<=pd.Timestamp(config["end"]))]


def normalize(source, objects):
    """Retain accession/category grain and direct issuer mapping, never collapse filings."""
    config = source["settings"]; prices, events, issues = [], {}, []
    for oid, entry in source["objects"].items():
        if "/aggs/ticker/" in entry["path"] and not "/O%3A" in entry["path"]:
            ticker = entry["path"].split("/ticker/")[1].split("/range/")[0]
            from urllib.parse import unquote
            ticker = unquote(ticker)
            for row in objects[oid]:
                day = pd.Timestamp(row["t"], unit="ms", tz="UTC").tz_convert("America/New_York").tz_localize(None).normalize()
                if not pd.Timestamp(config["start"]) <= day <= pd.Timestamp(config["end"]): raise ValueError("Price crosses H21 boundary")
                prices.append({"ticker": ticker, "date": day, "close": row.get("c"), "volume": row.get("v")})
    for collection in source["disclosure_collections"]:
        for row in objects[collection["object_id"]]:
            cik, accession, category = row.get("cik"), row.get("accession_number"), row.get("tertiary_category")
            if not cik or not accession or category not in config["categories"]:
                issues.append({"reason": "Missing identity or unknown taxonomy", "accession": accession}); continue
            day = pd.Timestamp(row["filing_date"])
            if not pd.Timestamp(config["start"]) <= day <= pd.Timestamp(config["end"]): raise ValueError("Filing crosses H21 boundary")
            issuer = str(cik).zfill(10); key = (issuer, accession, category)
            candidate = {"issuer": issuer, "accession": accession, "category": category, "filing_date": str(day.date()),
                         "text": row.get("supporting_text") or "", "filing_url": row.get("filing_url"),
                         "tickers": sorted(set(collection["tickers"]) & set(config["tickers"])), "provider_tickers": row.get("tickers") or []}
            candidate["excerpts"]=[candidate["text"]] if candidate["text"] else []
            if key in events:
                if events[key]["filing_date"] != candidate["filing_date"]: raise ValueError("Conflicting filing date")
                events[key]["tickers"] = sorted(set(events[key]["tickers"] + candidate["tickers"]))
                if candidate["text"] and candidate["text"] not in events[key]["excerpts"]:
                    events[key]["excerpts"].append(candidate["text"])
                    issues.append({"reason": "Additional distinct excerpt within one filing category", "accession": accession,"category":category})
            else: events[key] = candidate
    prices = pd.DataFrame(prices, columns=["ticker", "date", "close", "volume"])
    duplicate = prices.duplicated(["ticker", "date"], keep=False)
    if duplicate.any():
        for _, g in prices[duplicate].groupby(["ticker", "date"]):
            if g[["close", "volume"]].drop_duplicates().shape[0] != 1: raise ValueError("Conflicting overlapping price source")
        prices = prices.drop_duplicates(["ticker", "date"])
    for event in events.values():
        event["excerpts"]=sorted(set(event["excerpts"]));event["text"]="\n".join(event["excerpts"])
    return prices, list(events.values()), issues


def build_panel(prices, events, source):
    c = source["settings"]; grid = sessions(c); n = len(grid)
    market = prices[prices.ticker == c["benchmark"]].set_index("date").reindex(grid)
    if market.close.notna().sum() < 60: raise ValueError("Insufficient observed market data")
    market_return = market.close.pct_change(fill_method=None)
    known = {ticker: str(data.get("cik")).zfill(10) if data.get("cik") else "ticker:" + ticker for ticker, data in source["mapping"].items()}
    for event in events:
        for ticker in event["tickers"]:
            if known.get(ticker, "ticker:").startswith("ticker:"):
                known[ticker] = event["issuer"]
            elif known[ticker] != event["issuer"]:
                raise ValueError("Conflicting issuer mapping: " + ticker)
    parts = []; ticker_offset = {}; filing_map = {}; issues = []
    for ticker in c["tickers"]:
        rows = prices[prices.ticker == ticker]
        if rows.empty:
            issues.append({"ticker": ticker, "reason": "No observed stock history"}); continue
        g = rows.set_index("date").reindex(grid)
        close, volume = g.close.astype(float), g.volume.astype(float)
        if (close.dropna() <= 0).any() or (volume.dropna() < 0).any(): raise ValueError("Invalid stock units")
        r = close.pct_change(fill_method=None)
        p = pd.DataFrame({"ticker": ticker, "issuer": known[ticker], "session": np.arange(n), "date": grid,
                          "close": close.values, "volume": volume.values})
        for h in [1, 5, 20, 60]: p[f"return{h}"] = close.pct_change(h, fill_method=None).values
        for h in [20, 60]: p[f"vol{h}"] = np.sqrt(r.pow(2).rolling(h, min_periods=h).mean()).values
        p["log_adv20"] = np.log1p((close * volume).rolling(20, min_periods=20).mean()).values
        p["volume_state"] = (volume / volume.rolling(20, min_periods=20).mean().replace(0, np.nan)).values
        p["market_return5"] = market.close.pct_change(5, fill_method=None).values
        p["market_return20"] = market.close.pct_change(20, fill_method=None).values
        p["market_vol20"] = np.sqrt(market_return.pow(2).rolling(20, min_periods=20).mean()).values
        for h in c["horizons"]:
            future = pd.concat([r.shift(-j) for j in range(1, h + 1)], axis=1)
            complete = future.notna().all(axis=1)
            ret = (close.shift(-h) / close - 1).where(complete)
            p[f"return_{h}"] = ret.values; p[f"absolute_{h}"] = ret.abs().values
            p[f"volatility_{h}"] = np.sqrt(future.pow(2).mean(axis=1)).where(complete).values
            path = pd.concat([close.shift(-j) / close for j in range(1, h + 1)], axis=1)
            p[f"downside_{h}"] = (1 - path.min(axis=1)).clip(lower=0).where(complete).values
            p[f"target_end_{h}"] = pd.Series(grid).shift(-h).values
        ticker_offset[ticker] = len(parts) * n; parts.append(p)
    if not parts: raise ValueError("No research stock data")
    panel = pd.concat(parts, ignore_index=True)
    counts = panel.groupby(["issuer", "date"])["ticker"].transform("count")
    panel["weight"] = 1 / counts
    for event in events:
        available = pd.Timestamp(event["filing_date"]) + pd.Timedelta(days=1)
        s = int(grid.searchsorted(available))
        key = (event["issuer"], event["accession"])
        f = filing_map.setdefault(key, {"issuer": event["issuer"], "accession": event["accession"], "session": s,
                                       "filing_date": event["filing_date"], "categories": set(), "texts": [], "rows": set()})
        if f["session"] != s: raise ValueError("Filing availability conflict")
        f["categories"].add(event["category"])
        if event["text"]: f["texts"].append(event["text"])
        for ticker in event["tickers"]:
            if ticker in ticker_offset and s < n: f["rows"].add(ticker_offset[ticker] + s)
    filings = []
    for f in filing_map.values():
        f["categories"] = sorted(f["categories"]); f["rows"] = sorted(f["rows"])
        f["text"] = "\n".join(sorted(set(f.pop("texts"))))
        filings.append(f)
    return panel, sorted(filings, key=lambda x: (x["issuer"], x["session"], x["accession"])), issues


def pattern_catalog(filings, config, minimum=1):
    """Vertical support pruning enumerates observed conjunctions and true ordered filings."""
    rows = defaultdict(set); filing_support = defaultdict(set); issuers = defaultdict(set)
    def add(name, current, members, length, family, window=None):
        rows[name].update(current["rows"])
        filing_support[name].add((current["issuer"], current["accession"]))
        issuers[name].add(current["issuer"])
        definitions.setdefault(name, {"name": name, "members": members, "length": length, "family": family, "window": window})
    definitions = {}
    for category in config["categories"]:
        name = "tag:" + category
        definitions[name] = {"name": name, "members": [category], "length": 1, "family": "tag", "window": None}
    support_by_tag = defaultdict(set)
    for f in filings:
        for category in f["categories"]: support_by_tag[category].add((f["issuer"], f["accession"]))
    # Full observed inventory precedes support filtering. Rare antecedents can
    # activate a sequence at several later filings, so marginal count pruning
    # is not sound for sequences.
    eligible = set(support_by_tag)
    for f in filings:
        for category in f["categories"]: add("tag:" + category, f, [category], 1, "tag")
        cats = sorted(set(f["categories"]) & eligible)
        for length in range(2, config["maximum_pattern_length"] + 1):
            for combo in itertools.combinations(cats, length): add("set:" + "&".join(combo), f, list(combo), length, "itemset")
    by_issuer = defaultdict(list)
    for f in filings:
        if f["rows"]: by_issuer[f["issuer"]].append(f)
    for stream in by_issuer.values():
        for i, current in enumerate(stream):
            for window in config["sequence_windows"]:
                prior = [f for f in stream[:i] if 0 < current["session"] - f["session"] <= window]
                # Prefix support pruning: each constituent must meet the same occurrence floor.
                for length in range(2, config["maximum_pattern_length"] + 1):
                    for past in itertools.combinations(prior, length - 1):
                        seq = list(past) + [current]
                        if any(a["session"] >= b["session"] for a, b in zip(seq, seq[1:])): continue
                        if current.get("scrambled") and len({(f.get("scramble_year"), f.get("scramble_segment")) for f in seq}) != 1: continue
                        choices = [sorted(set(f["categories"]) & eligible) for f in seq]
                        for combo in itertools.product(*choices):
                            add(f"seq{window}:" + ">".join(combo), current, list(combo), length, "sequence", window)
    catalog = []
    for name, definition in definitions.items():
        count = len(filing_support[name])
        catalog.append({**definition, "source_filings": count, "source_issuers": len(issuers[name]), "rows": sorted(rows[name])})
    return sorted(catalog, key=lambda x: x["name"])


def feature_matrix(panel, filings, catalog, config, lag=0):
    n, days = len(panel), len(sessions(config)); row_ids, col_ids = [], []
    for column, entry in enumerate(catalog):
        for row in entry["rows"]:
            if row % days + lag < days: row_ids.append(row + lag); col_ids.append(column)
    patterns = sparse.csc_matrix((np.ones(len(row_ids)), (row_ids, col_ids)), shape=(n, len(catalog)))
    patterns.data[:] = 1.
    text, active = [""] * n, np.zeros(n, dtype=bool)
    for f in filings:
        for row in f["rows"]:
            if row % days + lag < days:
                row += lag; text[row] += "\n" + f["text"]; active[row] = True
    tags = [i for i, p in enumerate(catalog) if p["family"] == "tag"]
    # Distinct filings on one date remain separate in frequency counts, while
    # the activation matrix retains the issuer/date inferential grain.
    tag_lookup={catalog[column]["members"][0]:j for j,column in enumerate(tags)}
    tag_dense=np.zeros((n,len(tags)))
    for filing in filings:
        for row in filing["rows"]:
            if row % days+lag>=days:continue
            for category in filing["categories"]:
                if category in tag_lookup:tag_dense[row+lag,tag_lookup[category]]+=1
    context = []
    for window in config["sequence_windows"]:
        values = np.full_like(tag_dense, np.nan)
        for offset in range(0, n, days):
            a = tag_dense[offset:offset+days]; cumulative = np.vstack([np.zeros((1, len(tags))), np.cumsum(a, axis=0)])
            values[offset+window:offset+days] = cumulative[window:days] - cumulative[:days-window]
        for f in filings:
            if f.get("scrambled"):
                for row in f["rows"]:
                    offset = row - f["session"]
                    for boundary in f["scramble_boundaries"]:
                        values[offset+boundary:min(offset+boundary+window+lag, offset+days)] = np.nan
        context.append(values)
    # Session age of a strictly earlier served tag, capped at the longest
    # declared lookback. No served tag in that fully observed window is a
    # label-history reading, rather than verified absence of an event.
    maximum=max(config["sequence_windows"])
    recency=np.full_like(tag_dense,np.nan)
    for offset in range(0,n,days):
        last=np.full(len(tags),-maximum-1,dtype=int)
        for session in range(days):
            if session>=maximum:recency[offset+session]=np.minimum(session-last,maximum+1)
            present=tag_dense[offset+session]>0;last[present]=session
    for filing in filings:
        if filing.get("scrambled"):
            for row in filing["rows"]:
                offset=row-filing["session"]
                for boundary in filing["scramble_boundaries"]:
                    recency[offset+boundary:min(offset+boundary+maximum+lag,offset+days)]=np.nan
    context.append(recency)
    contexts = np.column_stack(context)
    return patterns, contexts, np.array(text, dtype=object), active


def fitting_catalog(catalog,config):
    """Necessary support bounds prune zero-fit patterns, never marginal antecedents.

    Full-history support is only an inventory bound. Every fitting and selection
    decision must also pass its earlier training-only issuer/date floor.
    """
    return [p for p in catalog if p["family"]=="tag" or (p["source_filings"]>=config["train_min_activations"] and p["source_issuers"]>=config["train_min_issuers"])]


def eligible_columns(matrix, panel, mask, config):
    counts = np.asarray(matrix[mask].sum(axis=0)).ravel()
    columns = []
    for column in np.flatnonzero(counts >= config["train_min_activations"]):
        active = matrix[:, column].toarray().ravel() > 0
        unique = panel.loc[mask & active, ["issuer", "date"]].drop_duplicates()
        if len(unique) >= config["train_min_activations"] and unique.issuer.nunique() >= config["train_min_issuers"]: columns.append(int(column))
    return columns


class TextFeatures:
    def __init__(self, config): self.config = config; self.vectorizer = None; self.svd = None; self.rank = 0
    def fit(self, documents):
        if sum(bool(str(x).strip()) for x in documents) < 3: return self
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=self.config["text_min_df"], max_features=self.config["text_max_features"])
        try: values = self.vectorizer.fit_transform(documents)
        except ValueError: self.vectorizer = None; return self
        self.rank = min(self.config["text_components"], values.shape[0]-1, values.shape[1]-1)
        if self.rank >= 1:
            self.svd = TruncatedSVD(n_components=self.rank, random_state=self.config["seed"]); self.svd.fit(values)
        return self
    def transform(self, documents):
        missing = np.array([not bool(str(x).strip()) for x in documents], dtype=float)[:, None]
        if self.svd is None: return missing
        return np.column_stack([self.svd.transform(self.vectorizer.transform(documents)), missing])


def scramble(filings, panel, config, seed):
    """Shift full bundles together within issuer/year; never infer across a wrap boundary."""
    import copy
    rng = np.random.default_rng(seed); grid = sessions(config); days = len(grid); offsets = {}
    years = np.array(grid.year); results = []
    for original in filings:
        f = copy.deepcopy(original); s = f["session"]
        if s >= days: results.append(f); continue
        year = int(years[s]); indices = np.flatnonzero(years == year); key = (f["issuer"], year)
        if key not in offsets: offsets[key] = int(rng.integers(1, len(indices)))
        new = int(indices[(s-indices[0]+offsets[key]) % len(indices)])
        f["session"] = new; f["rows"] = [r - s + new for r in f["rows"]]
        f["scramble_segment"] = int((s-indices[0]+offsets[key]) // len(indices))
        f["scramble_year"] = year
        f["scramble_boundaries"] = [int(indices[0]), int(indices[0]+offsets[key])]
        f["scrambled"] = True; results.append(f)
    return sorted(results, key=lambda x:(x["issuer"], x["session"], x["accession"]))
