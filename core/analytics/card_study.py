"""
QuantBIST
The /tara ai card's own rule measured on daily BIST 30 candles (DECISIONS K-68, written before the
measurement). Event: the daily "dip dönüşü" trigger; a new trigger within GAP sessions of the
stock's previous event is not a new event. Result: exactly what the paper book does
(core.signals.store._follow): enter at the next open, 2% trailing stop, 4% target, at most 10
sessions, cost deducted. Baseline: the same rule entered from every session of the same stocks.
The 95% interval of (events - baseline) resamples whole days.

    python -m core.analytics.card_study      # BIST 30, before the holdout
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import pandas as pd

from core.analytics.dip_study import day_bootstrap, events
from core.infrastructure.logger import get_logger

logger = get_logger(__name__)

GAP = 10  # sessions; the card's horizon
MIN_EVENTS = 100
DISCLAIMER = "Kural çıktısıdır, öneri değildir. Geçmiş sonuç geleceği göstermez."


def outcome(df: pd.DataFrame, i: int, symbol: str = "") -> dict:
    """The paper book's result for a signal on row `i` of a daily frame (store._follow, unchanged)."""

    from core.ml.features import HORIZON
    from core.signals.store import Signal, _follow

    window = df.iloc[i: i + 1 + HORIZON]
    s = Signal(0, df.index[i].date(), symbol, "bekliyor", None, None, None, None, None, None, None, None)
    return _follow(s, window)


@dataclass
class Result:
    events: int
    stocks: int
    mean_event: float | None
    mean_base: float | None
    diff: float | None
    interval: tuple[float, float]
    target_share: float | None
    stop_share: float | None
    expiry_share: float | None
    passed: bool
    reason: str


# K-68's run as recorded in RESEARCH_LOG (03.11.2026); the PC has no result file of its own
RECORDED = Result(207, 30, 0.0010, -0.0009, 0.0019, (-0.0025, 0.0061), 0.26, 0.74, 0.0, False,
                  "olaylar, aynı hisselerin rastgele seanslarından ayırt edilemiyor")
RECORDED_SOURCE = "Actions 41716706686"


def _result_file():
    from core.config.paths import LOG_DIR

    return LOG_DIR / "card_study.json"


RESULT_FILE = None  # tests point this elsewhere; None = logs/card_study.json


def latest() -> tuple[Result, str]:
    """The newest measurement: this PC's result file when it has one, else the recorded run."""

    import json
    from pathlib import Path

    try:
        got = json.loads(Path(RESULT_FILE or _result_file()).read_text(encoding="utf-8"))
        got["interval"] = tuple(got["interval"])
        return Result(**got), "bu bilgisayardaki son ölçüm"
    except (OSError, ValueError, TypeError, KeyError):
        return RECORDED, RECORDED_SOURCE


def card_line(result: Result, source: str) -> str:
    """One line for the /tara ai card (HTML)."""

    def pct(x):
        return f"%{x * 100:+.2f}".replace(".", ",")

    if not result.events or result.target_share is None or result.mean_event is None:
        return f"<b>Kartın kuralı geçmişte (K-68):</b> olay yok, ölçülemedi ({source})"
    verdict = "geçti" if result.passed else "rastgele girişten ayırt edilemedi"
    return (f"<b>Kartın kuralı geçmişte (K-68):</b> {result.events} tetikte hedef %{result.target_share * 100:.0f}, "
            f"stop %{result.stop_share * 100:.0f}; ortalama net {pct(result.mean_event)}, rastgele seanslar "
            f"{pct(result.mean_base)} (fark aralığı {pct(result.interval[0])} – {pct(result.interval[1])}; "
            f"{verdict}; günlük BIST 30, {source})")


def collect(frames: dict[str, pd.DataFrame], before: pd.Timestamp | None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(event rows, baseline rows): day, symbol, net result r and how the trade ended."""

    from core.market.extended import add_indicators, trigger_mask

    picked, base = [], []
    for symbol, df in frames.items():
        if df is None or len(df) < 250:
            continue
        if before is not None:
            df = df[df.index < before]
        ind = add_indicators(df)
        ready = ind["ema200"].notna().to_numpy()
        mask = events(trigger_mask(ind).where(ready, False).astype(bool), GAP).to_numpy()
        rows = []
        for i in range(len(df) - 1):
            if not ready[i]:
                continue
            got = outcome(df, i, symbol)
            if got.get("r") is None:  # not filled, or still open at the end of the data
                continue
            rows.append({"day": df.index[i].normalize(), "symbol": symbol, "r": got["r"], "how": got["status"],
                         "event": bool(mask[i])})
        if rows:
            table = pd.DataFrame(rows)
            picked.append(table[table["event"]])
            base.append(table)
    empty = pd.DataFrame(columns=["day", "symbol", "r", "how", "event"])
    return (pd.concat(picked) if picked else empty), (pd.concat(base) if base else empty)


def study(frames: dict[str, pd.DataFrame], before: pd.Timestamp | None = None) -> Result:
    if before is None:
        from core.backtest.run import HOLDOUT_START

        before = HOLDOUT_START
    picked, base = collect(frames, before)
    if picked.empty or base.empty:
        return Result(0, 0, None, None, None, (math.nan, math.nan), None, None, None, False, "olay yok")
    mean_event, mean_base = float(picked["r"].mean()), float(base["r"].mean())
    share = picked["how"].value_counts(normalize=True)
    result = Result(len(picked), picked["symbol"].nunique(), mean_event, mean_base, mean_event - mean_base,
                    day_bootstrap(picked, mean_base), float(share.get("hedef", 0.0)), float(share.get("stop", 0.0)),
                    float(share.get("sure", 0.0)), False, "")
    if result.events < MIN_EVENTS:
        result.reason = f"olay sayısı az ({result.events} < {MIN_EVENTS})"
    elif not result.interval[0] > 0:
        result.reason = "olaylar, aynı hisselerin rastgele seanslarından ayırt edilemiyor"
    elif not mean_event > 0:
        result.reason = "olayların maliyet sonrası ortalaması pozitif değil"
    else:
        result.passed, result.reason = True, "koşullar sağlandı"
    return result


def text(result: Result) -> str:
    def pct(x, sign=True):
        if x is None or (isinstance(x, float) and math.isnan(x)):
            return "—"
        return (f"%{x * 100:+.2f}" if sign else f"%{x * 100:.0f}").replace(".", ",")

    return "\n".join([
        f"🔬 Kartın kuralı (günlük BIST 30, K-68): {'GEÇTİ' if result.passed else 'GEÇMEDİ'} – {result.reason}",
        f"{result.events} olay, {result.stocks} hisse. Ortalama net {pct(result.mean_event)}, "
        f"rastgele seanslar {pct(result.mean_base)}; fark {pct(result.diff)} "
        f"(%95 aralık {pct(result.interval[0])} – {pct(result.interval[1])}).",
        f"Çıkış: hedef {pct(result.target_share, False)}, stop {pct(result.stop_share, False)}, "
        f"süre dolumu {pct(result.expiry_share, False)}.",
        "Not: bugünkü BIST 30 listesi geçmişe uygulandı (hayatta kalma yanlılığı).",
        DISCLAIMER,
    ])


def main() -> int:
    import json

    from core.config.bist30 import BIST30_TICKERS
    from core.config.paths import LOG_DIR
    from core.infrastructure.console import utf8_output
    from core.reports.daily import adjusted_bars

    utf8_output()
    frames = {s: adjusted_bars(s) for s in BIST30_TICKERS}
    result = study({s: df for s, df in frames.items() if not df.empty})
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    (LOG_DIR / "card_study.json").write_text(json.dumps(asdict(result), ensure_ascii=False, indent=1, default=str),
                                             encoding="utf-8")
    print(text(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["GAP", "RECORDED", "Result", "card_line", "collect", "latest", "outcome", "study", "text"]
