"""
QuantBIST
Signal confirmation layer (meta-labeling, DECISIONS K-64, written before the measurement).

The technical trigger ("dip dönüşü", core.market.extended) proposes a signal; a RandomForest
returns its success probability; >= APPROVE (0.60) confirms it, below is a "yalancı sinyal".

No look-ahead, by construction:
- features of candle t use candles up to and including t (core.market.extended);
- the label looks forward (entry at t+1's open, close X candles later >= +Y%), and every row
  carries `label_end`: a training row is used only if its label was known before the first
  event it is tested on (purging), in the outer evaluation and in the hyper-parameter search;
- max_depth / min_samples_leaf are chosen inside the training data only (time-ordered folds,
  log-loss), never on the test data; rows on or after 02.11.2026 (holdout) are not used.

    python -m core.ml.signal_filter --zaman gunluk     # BIST 100 daily, point-in-time members
    python -m core.ml.signal_filter --zaman saatlik    # BIST 30 hourly, last year
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass, field

import numpy as np
import pandas as pd

from core.infrastructure.logger import get_logger
from core.market.limits import limit_up

logger = get_logger(__name__)

APPROVE = 0.60
SPEC = {"gunluk": (10, 0.03), "saatlik": (16, 0.015)}  # (X candles, Y rise), K-64
GRID = {"max_depth": [3, 4, 5], "min_samples_leaf": [10, 25, 50]}
OUTER_CHUNKS = 6  # 5 outer folds: chunk k is tested on a model trained on chunks < k
INNER_CHUNKS = 4  # 3 inner folds for the hyper-parameter search
MIN_APPROVED = 50
BOOTSTRAP = 2000
LIMIT_MOVE = 0.095
FEATURES = ("rsi", "adx", "stoch_k", "stoch_d", "macd_hist", "bb_yuzde", "atr_oran", "cmf", "ema50_uzaklik",
            "ema200_uzaklik", "hacim_5")
DISCLAIMER = "Kural çıktısıdır, öneri değildir. Karar ve sorumluluk kullanıcıdadır."


# --- features and labels -------------------------------------------------------------------------


def features(df: pd.DataFrame) -> pd.DataFrame:
    """The model inputs of every candle (only that candle and the ones before it)."""

    from core.market.extended import add_indicators

    ind = add_indicators(df)
    out = pd.DataFrame(index=df.index)
    for name in ("rsi", "adx", "stoch_k", "stoch_d", "macd_hist", "bb_yuzde", "cmf", "ema50_uzaklik", "ema200_uzaklik"):
        out[name] = ind.get(name)
    out["atr_oran"] = ind.get("atr") / df["close"]
    out["hacim_5"] = df["volume"] / df["volume"].shift(1).rolling(5).mean() - 1  # vs the previous 5 candles
    return out[list(FEATURES)].replace([np.inf, -np.inf], np.nan)


def labels(df: pd.DataFrame, x: int, y: float) -> pd.DataFrame:
    """1 when the close x candles later is at least y above the next candle's open (the entry)."""

    entry = df["open"].shift(-1)
    later = df["close"].shift(-x)
    fill = (entry > 0) & ~limit_up(entry / df["close"] - 1)  # no entry on a limit-up open
    known = later.notna() & entry.notna() & fill
    label = (later / entry - 1 >= y).astype(float).where(known)
    ends = pd.Series(df.index, index=df.index).shift(-x).where(known)
    return pd.DataFrame({"label": label, "label_end": ends})


def events(frames: dict[str, pd.DataFrame], x: int, y: float, members=None, before=None) -> pd.DataFrame:
    """One row per trigger event (first trigger of each x-candle cluster) with features and label."""

    from core.analytics.dip_study import events as cluster
    from core.market.extended import add_indicators, trigger_mask

    rows = []
    for symbol, df in frames.items():
        try:
            if df is None or len(df) < 250:
                continue
            if before is not None:
                df = df[df.index < before]
            mask = cluster(trigger_mask(add_indicators(df)), gap=x)
            part = features(df).join(labels(df, x, y))[mask]
            part = part.assign(symbol=symbol, time=part.index, day=part.index.normalize())
            if members is not None:
                part = part[[symbol in members(t) for t in part["time"]]]
            rows.append(part)
        except Exception as exc:  # noqa: BLE001 - one bad stock must not stop the study
            logger.warning("Signal events failed | %s | %s", symbol, exc)
    if not rows:
        return pd.DataFrame(columns=[*FEATURES, "label", "label_end", "symbol", "time", "day"])
    data = pd.concat(rows, ignore_index=True)
    return data.dropna(subset=[*FEATURES, "label"]).sort_values(["time", "symbol"]).reset_index(drop=True)


# --- model ---------------------------------------------------------------------------------------


def _purged_folds(rows: pd.DataFrame, chunks: int):
    """(train positions, test positions): chunk k tested, earlier rows whose label was known before it."""

    edges = np.linspace(0, len(rows), chunks + 1).astype(int)
    for k in range(1, chunks):
        test = np.arange(edges[k], edges[k + 1])
        if not len(test):
            continue
        first = rows["time"].iloc[test[0]]
        train = np.flatnonzero((np.arange(len(rows)) < edges[k]) & (rows["label_end"] < first).to_numpy())
        yield train, test


def fit(train: pd.DataFrame, seed: int = 0, trees: int = 300):
    """A RandomForest with max_depth / min_samples_leaf chosen inside `train` only (K-64)."""

    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import GridSearchCV

    # one process: joblib's worker pool opens files without an encoding (EncodingWarning under the test flags)
    base = RandomForestClassifier(n_estimators=trees, class_weight="balanced_subsample", n_jobs=1, random_state=seed)
    x, target = train[list(FEATURES)].to_numpy(), train["label"].to_numpy(dtype=int)
    folds = [(a, b) for a, b in _purged_folds(train.reset_index(drop=True), INNER_CHUNKS)
             if len(a) and len(set(target[a])) == 2]
    if len(folds) < 2:
        model = base.set_params(max_depth=4, min_samples_leaf=25).fit(x, target)
        return model, {"max_depth": 4, "min_samples_leaf": 25}
    search = GridSearchCV(base, GRID, scoring="neg_log_loss", cv=folds, error_score=np.nan).fit(x, target)
    return search.best_estimator_, search.best_params_


def decide(model, row: pd.DataFrame) -> tuple[float, str]:
    """The success probability of a signal and the decision (>= APPROVE confirms it)."""

    p = float(model.predict_proba(row[list(FEATURES)].to_numpy())[0, 1])
    return p, ("onaylandı" if p >= APPROVE else "yalancı sinyal")


# --- live model ----------------------------------------------------------------------------------


def model_file():
    from core.config.paths import LOG_DIR

    return LOG_DIR / "signal_model.joblib"


def report_file(zaman: str = "gunluk"):
    from core.config.paths import LOG_DIR

    return LOG_DIR / f"signal_filter_{zaman}.json"


@dataclass(frozen=True)
class TrackRecord:
    approved: int
    precision: float
    base_rate: float
    source: str


# K-64's out-of-sample result as recorded in RESEARCH_LOG (03.11.2026); the PC usually has no report
# file because the evaluation runs on GitHub Actions
RECORDED = {
    "gunluk": TrackRecord(42, 0.262, 0.336, "BIST 100, örneklem dışı, K-64, Actions 41645852277"),
    "saatlik": TrackRecord(39, 0.410, 0.236, "BIST 30 saatlik, örneklem dışı, K-64, Actions 41645846675"),
}


def track_record(zaman: str = "gunluk") -> TrackRecord | None:
    """The newest out-of-sample figures: this PC's report when it has one, else the recorded K-64 run."""

    try:
        got = json.loads(report_file(zaman).read_text(encoding="utf-8"))
        if isinstance(got, dict) and got.get("approved") and got.get("precision") is not None and got.get("base_rate") is not None:
            return TrackRecord(int(got["approved"]), float(got["precision"]), float(got["base_rate"]),
                               "bu bilgisayardaki son ölçüm")
    except (OSError, ValueError, TypeError):
        pass
    return RECORDED.get(zaman)


def validated(zaman: str = "gunluk") -> bool:
    """True only after the out-of-sample evaluation passed (K-64); a missing or broken report is False."""

    try:
        got = json.loads(report_file(zaman).read_text(encoding="utf-8"))
        return bool(got.get("passed")) if isinstance(got, dict) else False  # M31-9: null or [] crashed
    except (OSError, ValueError):
        return False


def fit_live(frames: dict[str, pd.DataFrame], members, today, path=None, make=fit) -> int:
    """Train on every daily event whose label was known before `today`; returns the rows used."""

    import joblib

    x, y = SPEC["gunluk"]
    rows = events(frames, x, y, members, before=pd.Timestamp(today))
    rows = rows[rows["label_end"] < pd.Timestamp(today)]
    if len(rows) < 100 or rows["label"].nunique() < 2:
        return 0
    model, params = make(rows)
    path = path or model_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "params": params, "rows": len(rows), "trained": str(today)}, path)
    return len(rows)


def load_live(path=None) -> dict | None:
    import joblib

    path = path or model_file()
    try:
        return joblib.load(path) if path.exists() else None
    except Exception as exc:  # noqa: BLE001 - a broken file means "no model", never a crash
        logger.warning("Signal model unreadable | %s", exc)
        return None


# --- evaluation ----------------------------------------------------------------------------------


@dataclass
class Report:
    zaman: str
    events: int = 0
    tested: int = 0
    base_rate: float | None = None
    accuracy: float | None = None
    approved: int = 0
    hits: int = 0
    precision: float | None = None
    interval: tuple[float, float] = (math.nan, math.nan)
    params: list = field(default_factory=list)
    passed: bool = False
    reason: str = ""


def _bootstrap(chosen: pd.DataFrame, seed: int = 0) -> tuple[float, float]:
    by_day = chosen.groupby("day")["label"].agg(["sum", "count"])
    if by_day.empty:
        return (math.nan, math.nan)
    pick = np.random.default_rng(seed).integers(0, len(by_day), size=(BOOTSTRAP, len(by_day)))
    rates = by_day["sum"].to_numpy()[pick].sum(axis=1) / by_day["count"].to_numpy()[pick].sum(axis=1)
    lo, hi = np.percentile(rates, [2.5, 97.5])
    return (float(lo), float(hi))


def evaluate(rows: pd.DataFrame, zaman: str = "", make=fit) -> Report:
    """Expanding-window out-of-sample evaluation (5 outer folds, purged), the 0.60 decision rule."""

    report = Report(zaman, len(rows))
    tested = []
    for train_pos, test_pos in _purged_folds(rows, OUTER_CHUNKS):
        train = rows.iloc[train_pos]
        if len(train) < 100 or train["label"].nunique() < 2:
            continue
        model, params = make(train)
        test = rows.iloc[test_pos].copy()
        test["proba"] = model.predict_proba(test[list(FEATURES)].to_numpy())[:, 1]
        tested.append(test)
        report.params.append(params)
    if not tested:
        report.reason = "değerlendirilecek yeterli olay yok"
        return report
    out = pd.concat(tested)
    approve = out["proba"] >= APPROVE
    report.tested = len(out)
    report.base_rate = float(out["label"].mean())
    report.accuracy = float((approve.astype(int) == out["label"].astype(int)).mean())
    chosen = out[approve]
    report.approved, report.hits = len(chosen), int(chosen["label"].sum())
    if report.approved:
        report.precision = report.hits / report.approved
        report.interval = _bootstrap(chosen)
    if report.approved < MIN_APPROVED:
        report.reason = f"onaylı sinyal az ({report.approved} < {MIN_APPROVED})"
    elif not report.interval[0] > report.base_rate:
        report.reason = "onaylı sinyallerin isabeti, tüm sinyallerin oranından ayırt edilemiyor"
    else:
        report.passed, report.reason = True, "koşullar sağlandı"
    return report


def text(report: Report) -> str:
    def pct(v):
        return "—" if v is None or (isinstance(v, float) and math.isnan(v)) else f"%{v * 100:.1f}".replace(".", ",")

    x, y = SPEC.get(report.zaman, (None, None))
    lines = [f"🤖 Sinyal onay katmanı ({report.zaman}): {'GEÇTİ' if report.passed else 'GEÇMEDİ'} – {report.reason}"]
    if x:
        lines.append(f"Etiket: ertesi açılışta giriş, {x} mum sonra kapanış ≥ +%{y * 100:g}; onay eşiği olasılık ≥ "
                     f"{APPROVE:.2f}".replace(".", ","))
    lines += [
        f"Olay {report.events}, test edilen {report.tested}. Accuracy (doğruluk): {pct(report.accuracy)}",
        f"Taban oran (tüm sinyallerde başarı): {pct(report.base_rate)}",
        f"Onaylanan {report.approved}, isabet {pct(report.precision)} (%95 aralık {pct(report.interval[0])}–"
        f"{pct(report.interval[1])})",
        "Not: doğruluk tek başına ölçüt değildir; taban oran düşükse her şeye 'hayır' diyen model de yüksek "
        "doğruluk alır.",
        DISCLAIMER,
    ]
    return "\n".join(lines)


# --- command line --------------------------------------------------------------------------------


def _daily():
    from core.market.membership import load_changes, load_stable, members_on
    from core.reports.daily import adjusted_bars

    codes = load_stable() | set(load_changes())
    frames = {f"{c}.IS": adjusted_bars(f"{c}.IS") for c in sorted(codes)}
    frames = {s: df for s, df in frames.items() if not df.empty}
    return frames, (lambda t: {f"{c}.IS" for c in members_on(pd.Timestamp(t).date())})


def main(argv: list[str] | None = None) -> int:
    """Print the out-of-sample accuracy and the rest of the report (the test function of K-64)."""

    from core.backtest.run import HOLDOUT_START
    from core.config.paths import LOG_DIR
    from core.infrastructure.console import utf8_output

    utf8_output()
    parser = argparse.ArgumentParser(description="Signal confirmation layer, out-of-sample evaluation")
    parser.add_argument("--zaman", choices=tuple(SPEC), default="gunluk")
    parser.add_argument("--veri", default=None, help="dondurulmuş saatlik veri klasörü (yalnız saatlik)")
    args = parser.parse_args(argv)
    from core.analytics import provenance

    x, y = SPEC[args.zaman]
    if args.zaman == "gunluk":
        if args.veri:
            parser.error("--veri yalnız --zaman saatlik ile kullanılır")
        frames, members = _daily()
        before, source = HOLDOUT_START, "yerel fiyat deposu (market.db)"
    else:
        frames, source = provenance.load_frozen_or_download(args.veri)
        members, before = None, HOLDOUT_START.tz_localize("Europe/Istanbul")
    print(provenance.stamp(frames, before))
    print(f"Kaynak: {source}")
    report = evaluate(events(frames, x, y, members, before), args.zaman)
    if not args.veri:  # a run on a frozen snapshot is a check; it leaves the result file alone
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        (LOG_DIR / f"signal_filter_{args.zaman}.json").write_text(
            json.dumps(asdict(report), ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    out = text(report)
    print(out)
    print(f"Rapor sha256 {provenance.report_digest(out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["APPROVE", "FEATURES", "SPEC", "Report", "decide", "evaluate", "events", "features", "fit", "fit_live",
           "labels", "load_live", "main", "model_file", "text", "validated"]
