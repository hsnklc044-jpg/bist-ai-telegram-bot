"""
QuantBIST
ML filter (BIST 30 hedefi, adım 2): a RandomForest that judges whether "enter at the next open,
2% stop, 4% target" reaches its target first. Rule output, not advice.

Measured only out of sample: expanding-window walk forward by calendar year; a training row is
used only if its label was known before the test year began (purged), and rows on or after
HOLDOUT_START (02.11.2026) are never touched unless asked for. The filter counts as passed only if
its precision on all test years is at least THRESHOLD (60%) with at least MIN_SIGNALS signals AND
the lower end of its 95% interval is above the base rate (the share of all entries that reach the
target anyway): a model that is "right 60%" in a market where 60% of entries win adds nothing.

    python -m core.ml.ml_filter                    # BIST 30 approximation, writes logs/ml_report.json
    python -m core.ml.ml_filter --universe bist100
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from core.config.paths import LOG_DIR
from core.ml.features import FEATURES, HORIZON, STOP, TARGET

THRESHOLD = 0.60
MIN_SIGNALS = 100
PROBA = 0.5
FIRST_TEST_YEAR = 2020
REPORT_FILE = LOG_DIR / "ml_report.json"
DISCLAIMER = "Kural çıktısıdır, öneri değildir. Karar ve sorumluluk kullanıcıdadır."


def holdout_start() -> pd.Timestamp:
    from core.backtest.run import HOLDOUT_START

    return HOLDOUT_START


def model(seed: int = 0):
    from sklearn.ensemble import RandomForestClassifier

    # fixed before any result was seen; shallow trees and large leaves against overfitting
    return RandomForestClassifier(n_estimators=300, max_depth=6, min_samples_leaf=100, max_features="sqrt",
                                  class_weight="balanced_subsample", n_jobs=-1, random_state=seed)


def wilson(hits: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (math.nan, math.nan)
    p = hits / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (centre - half, centre + half)


@dataclass
class Fold:
    year: int
    train_rows: int
    test_rows: int
    signals: int
    hits: int
    base_rate: float
    mean_r_signals: float | None
    mean_r_all: float


@dataclass
class Report:
    universe: str
    rows: int
    folds: list[Fold] = field(default_factory=list)
    signals: int = 0
    hits: int = 0
    precision: float | None = None
    interval: tuple[float, float] = (math.nan, math.nan)
    base_rate: float | None = None
    mean_r_signals: float | None = None
    mean_r_all: float | None = None
    passed: bool = False
    reason: str = ""
    importances: dict[str, float] = field(default_factory=dict)
    holdout_used: bool = False
    settings: dict = field(default_factory=lambda: {"stop": STOP, "target": TARGET, "horizon": HORIZON,
                                                    "threshold": THRESHOLD, "min_signals": MIN_SIGNALS,
                                                    "proba": PROBA})


def train_rows(data: pd.DataFrame, before: pd.Timestamp) -> pd.DataFrame:
    """Rows whose label was known before `before` (purging: no label reaches into the test period)."""

    return data[data["label_end"] < before]


def walk_forward(data: pd.DataFrame, universe: str = "", first_year: int = FIRST_TEST_YEAR, holdout: bool = False,
                 make_model=model) -> Report:
    cut = holdout_start()
    data = data if holdout else data[(data["date"] < cut)]
    report = Report(universe, len(data), holdout_used=holdout)
    years = sorted(y for y in data["date"].dt.year.unique() if y >= first_year)
    picked, outcomes = [], []
    importances = np.zeros(len(FEATURES))
    for year in years:
        start = pd.Timestamp(year=year, month=1, day=1)
        train = train_rows(data, start)
        if not holdout:
            train = train[train["label_end"] < cut]
        test = data[data["date"].dt.year == year]
        if len(train) < 1000 or train["label"].nunique() < 2 or test.empty:
            continue
        m = make_model()
        m.fit(train[list(FEATURES)].to_numpy(), train["label"].to_numpy(dtype=int))
        proba = m.predict_proba(test[list(FEATURES)].to_numpy())[:, 1]
        chosen = test[proba >= PROBA]
        importances += getattr(m, "feature_importances_", np.zeros(len(FEATURES)))
        report.folds.append(Fold(year, len(train), len(test), len(chosen), int(chosen["label"].sum()),
                                 float(test["label"].mean()),
                                 float(chosen["r"].mean()) if len(chosen) else None, float(test["r"].mean())))
        picked.append(chosen)
        outcomes.append(test)
    if not report.folds:
        report.reason = "değerlendirilecek yeterli veri yok"
        return report
    chosen, every = pd.concat(picked), pd.concat(outcomes)
    report.signals, report.hits = len(chosen), int(chosen["label"].sum())
    report.base_rate = float(every["label"].mean())
    report.mean_r_all = float(every["r"].mean())
    report.importances = dict(sorted(zip(FEATURES, (importances / len(report.folds)).round(4).tolist(),
                                         strict=True), key=lambda kv: -kv[1]))
    if report.signals:
        report.precision = report.hits / report.signals
        report.interval = wilson(report.hits, report.signals)
        report.mean_r_signals = float(chosen["r"].mean())
    if report.signals < MIN_SIGNALS:
        report.reason = f"sinyal sayısı az ({report.signals} < {MIN_SIGNALS})"
    elif report.precision < THRESHOLD:
        report.reason = f"isabet %{report.precision * 100:.1f} < eşik %{THRESHOLD * 100:.0f}".replace(".", ",")
    elif not report.interval[0] > report.base_rate:
        report.reason = (f"isabet, hedefe zaten ulaşan girişlerin oranından (%{report.base_rate * 100:.1f}) "
                         "ayırt edilemiyor").replace(".", ",")
    else:
        report.passed = True
        report.reason = "eşik geçildi"
    return report


def text(report: Report) -> str:
    def pct(x):
        return "—" if x is None or (isinstance(x, float) and math.isnan(x)) else f"%{x * 100:.1f}".replace(".", ",")

    lines = [f"🤖 ML filtresi ({report.universe}): {'AÇIK' if report.passed else 'KAPALI'} – {report.reason}",
             f"Kural: ertesi açılışta giriş, %{STOP * 100:.0f} stop, %{TARGET * 100:.0f} hedef, en çok {HORIZON} "
             "seans; ölçüm yalnız eğitimde görülmemiş yıllarda.",
             f"Sinyal {report.signals}, isabet {pct(report.precision)} (%95 aralık {pct(report.interval[0])}–"
             f"{pct(report.interval[1])}); tüm girişlerde hedefe ulaşma {pct(report.base_rate)}.",
             f"Ortalama net sonuç: sinyallerde {pct(report.mean_r_signals)}, tüm girişlerde {pct(report.mean_r_all)} "
             "(maliyet dahil)."]
    for f in report.folds:
        lines.append(f"  {f.year}: {f.signals} sinyal, isabet "
                     f"{pct(f.hits / f.signals) if f.signals else '—'}, taban {pct(f.base_rate)}")
    lines.append(DISCLAIMER)
    return "\n".join(lines)


def save(report: Report, path: Path | None = None) -> None:
    path = Path(path or REPORT_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(report), ensure_ascii=False, indent=1, default=str), encoding="utf-8")


def load(path: Path | None = None) -> dict | None:
    path = Path(path or REPORT_FILE)
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    except (OSError, ValueError):
        return None


def enabled(path: Path | None = None) -> bool:
    """The live filter may be used only after an out-of-sample pass."""

    report = load(path)
    return bool(report and report.get("passed"))


# --- universe ------------------------------------------------------------------------------------


def liquid_members(frames: dict[str, pd.DataFrame], size: int = 30):
    """BIST 30 approximation until the official list has a source: on each day, the `size` most
    liquid BIST 100 members of that day by the previous 20 sessions' TL volume (point in time)."""

    from core.market.membership import members_on

    tl = pd.DataFrame({s: (df["close"] * df["volume"]).shift(1).rolling(20).mean() for s, df in frames.items()})
    cache: dict = {}

    def members(day) -> set[str]:
        day = pd.Timestamp(day)
        if day not in cache:
            index = {f"{c}.IS" for c in members_on(day.date())}
            row = tl.loc[day, [s for s in tl.columns if s in index]] if day in tl.index else pd.Series(dtype=float)
            cache[day] = set(row.dropna().nlargest(size).index)
        return cache[day]

    return members


def main(argv: list[str] | None = None) -> int:
    from core.infrastructure.console import utf8_output
    from core.market.membership import load_changes, load_stable
    from core.ml.features import dataset
    from core.reports.daily import adjusted_bars

    utf8_output()
    parser = argparse.ArgumentParser(description="ML filter, out-of-sample evaluation")
    parser.add_argument("--universe", choices=("bist30", "bist100"), default="bist30")
    args = parser.parse_args(argv)
    events, stable = load_changes(), load_stable()
    codes = stable | {c for c in events}
    frames = {f"{c}.IS": adjusted_bars(f"{c}.IS") for c in sorted(codes)}
    frames = {s: df for s, df in frames.items() if df is not None and not df.empty}
    if args.universe == "bist30":
        members, name = liquid_members(frames), "BIST 30 yaklaşığı (günün en likit 30 BIST 100 üyesi)"
    else:
        from core.market.membership import members_on

        members, name = (lambda d: {f"{c}.IS" for c in members_on(pd.Timestamp(d).date())}), "BIST 100"
    report = walk_forward(dataset(frames, members), name)
    save(report)
    print(text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["DISCLAIMER", "MIN_SIGNALS", "REPORT_FILE", "Report", "THRESHOLD", "enabled", "liquid_members", "load",
           "main", "model", "save", "text", "walk_forward", "wilson"]
