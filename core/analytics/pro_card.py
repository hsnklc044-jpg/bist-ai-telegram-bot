"""/karne HİSSE (D and I madde 3, the user's 11.11.2026 decision): the professional score (K-88) and the user's
scorecard side by side, six 10-box bars, price / support / resistance, and the stock's own past in the same class.

"Geçmiş": the research-period days (the screen card's data, cut before the holdout) on which the stock's
professional score was in the same class as today, and what happened 20 sessions later: the stock's mean return,
XU100's mean return over the same days, and the share of those days on which the stock rose ("İsabet"). A day counts
only when its 20 sessions are inside the data (no look-ahead); fewer than 30 days: "Geçmiş örnek az". Relative
strength is ranked each day among that day's BIST 100 members, as in the screen card. Description, not a
recommendation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from core.analytics import pro_score as P
from core.reports import style

HORIZON = 20
MIN_DAYS = 30
BOXES = 10
SHORT = {"Uzun vadeli trend": "Uzun trend", "Orta vadeli momentum": "Momentum", "Göreli güç": "Göreli güç",
         "52 hafta zirvesine yakınlık": "Zirveye yak.", "Kısa vadeli teyit": "Kısa teyit", "Hacim teyidi": "Hacim"}
RANGES = {"Güçlü": (80, 100), "Olumlu": (60, 79), "Karışık": (40, 59), "Zayıf": (20, 39), "Çok zayıf": (0, 19)}


def bar(points: int, maximum: int) -> str:
    filled = round(points / maximum * BOXES)
    return "█" * filled + "░" * (BOXES - filled)


@dataclass(frozen=True)
class Past:
    label: str
    low: int
    high: int
    days: int
    mean: float
    bench_mean: float
    hit: float


def past(totals: pd.Series, close: pd.Series, bench: pd.Series, current: float, horizon: int = HORIZON) -> Past:
    """The days whose score was in `current`'s class and whose `horizon` sessions are inside the data."""

    label = style.score_class(current)[1]
    low, high = RANGES[label]
    index = close.index
    totals = totals.reindex(index)
    ahead = close.shift(-horizon) / close - 1
    bench = bench.reindex(index).ffill()
    bench_ahead = bench.shift(-horizon) / bench - 1
    same = totals.between(low, high) & ahead.notna()
    if not same.any():
        return Past(label, low, high, 0, 0.0, 0.0, 0.0)
    return Past(label, low, high, int(same.sum()), float(ahead[same].mean()), float(bench_ahead[same].mean()),
                float((ahead[same] > 0).mean()))


def _distance(level: float | None, close: float) -> str:
    return "" if level is None else style.percent(level / close - 1)


def text(symbol: str, day: date, score: P.ProScore, card_total: int | None, close: float,
         support: float | None, resistance: float | None, past: Past | None) -> str:
    code = symbol.removesuffix(".IS")
    colour = score.colour()
    first = style.header(f"{code} · Teknik karne", day)
    second = f"{colour[0]} {score.label()} · {colour[1]}" if colour else score.label()
    lines = [first, second]
    if card_total is not None:
        lines.append(f"Betik karnesi: {card_total}/100")
    lines.append("")
    rows = []
    for d in P.DIMENSIONS:
        got = score.parts.get(d.name)
        name = f"{SHORT[d.name]:<12} "
        rows.append(f"{name}veri yok" if got is None else f"{name}{bar(got, d.maximum)} {got}/{d.maximum}")
    lines.append("<pre>" + "\n".join(rows) + "</pre>")
    lines.append("")
    levels = [f"{'Fiyat':<7}{style.price(close).removesuffix(' TL'):>10}"]
    for name, value in (("Destek", support), ("Direnç", resistance)):
        shown = "—" if value is None else style.price(value).removesuffix(" TL")
        levels.append(f"{name:<7}{shown:>10} {_distance(value, close):>7}".rstrip())
    lines.append("<pre>" + "\n".join(levels) + "</pre>")
    if past is not None:
        lines.append("")
        lines.append(f"Geçmiş · {past.label} {past.low}–{past.high} puan · {HORIZON} gün")
        if past.days < MIN_DAYS:
            lines.append(f"Geçmiş örnek az ({past.days} gün)")
        else:
            lines.append(f"Ort. {style.percent(past.mean)} · XU100 {style.percent(past.bench_mean)} · "
                         f"İsabet {round(past.hit * 100)}%")
    if score.warning:
        lines.append("⚠️ Oynaklık yüksek (son 60 gün, evrenin en oynak %10'u)")
    lines += ["", f"Ayrıntı: /karne {code} detay"]
    return "\n".join(lines)


def criteria(row: pd.Series) -> list[str]:
    """Each dimension's points and its criteria, ✓ / ✗ (the /karne ... detay lines)."""

    def mark(ok) -> str:
        return "✓" if ok else "✗"

    r = row
    parts = P.score(r).parts
    checks = {
        "Uzun vadeli trend": [(r["close"] > r["sma(200)"], "kapanış SMA200'ün üstünde"),
                              (r["sma(50)"] > r["sma(200)"], "SMA50 SMA200'ün üstünde")],
        "Orta vadeli momentum": [(r["getiri_12a_1a_haric"] > 0, "12 ay getirisi (son ay hariç) artıda"),
                                 (r["getiri_6a_1a_haric"] > 0, "6 ay getirisi (son ay hariç) artıda")],
        "Göreli güç": [(r["goreli_guc_yuzdelik"] >= 70, f"BIST 100 içinde göreli güç sırası "
                                                       f"{style.number(r['goreli_guc_yuzdelik'], 0)} (70 ve üstü)")],
        "52 hafta zirvesine yakınlık": [(-r["zirve_uzaklik"] <= 10,
                                         f"zirveye uzaklık %{style.number(-r['zirve_uzaklik'], 1)} (en fazla %10)")],
        "Kısa vadeli teyit": [(r["macd"] > r["macd_sinyal"], "MACD sinyal çizgisinin üstünde"),
                              (50 <= r["rsi"] <= 70, f"RSI {style.number(r['rsi'], 1)} (50–70)"),
                              (r["close"] > r["ema20"], "kapanış EMA20'nin üstünde")],
        "Hacim teyidi": [(r["obv_egim"] > 0, "OBV eğimi artıda"), (r["cmf"] > 0, "para akışı (CMF) artıda")],
    }
    lines = []
    for d in P.DIMENSIONS:
        got = parts[d.name]
        if got is None:
            lines.append(f"{d.name}: veri yok")
            continue
        lines.append(f"{d.name} {got}/{d.maximum}")
        lines += [f"  {mark(ok)} {what}" for ok, what in checks[d.name]]
    return lines


def detail(symbol: str, row: pd.Series, script_text: str) -> str:
    code = symbol.removesuffix(".IS")
    score = P.score(row)
    head = [f"{code} · profesyonel teknik puan {score.label()}", *criteria(row)]
    if score.warning:
        head.append("⚠️ Oynaklık yüksek (oynaklık sırası 90 ve üstü; puana girmez)")
    return "\n".join([*head, "", script_text])


_HISTORY: dict = {}


def history_totals() -> tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    """(scores, closes, XU100 close): every research-period member's professional score on every day, once a day."""

    from core.market.calendar import now_istanbul
    from core.screen import fields as F
    from core.screen.command import _history_data

    key = now_istanbul().date()
    if key not in _HISTORY:
        frames, bench, members = _history_data()
        cols = list(dict.fromkeys([*P.COLUMNS, *(F.RANKED[c] for c in P.COLUMNS if c in F.RANKED)]))
        tables = {s: F.table(df, bench["close"], cols) for s, df in frames.items()}
        F.rank_panel(tables, [c for c in P.COLUMNS if c in F.RANKED], members)
        scores = {}
        for s, t in tables.items():
            t = t.copy()
            t["close"] = frames[s]["close"]
            scores[s] = P.totals(t)
        _HISTORY.clear()
        _HISTORY[key] = (pd.DataFrame(scores), pd.DataFrame({s: df["close"] for s, df in frames.items()}),
                         bench["close"])
    return _HISTORY[key]


__all__ = ["HORIZON", "MIN_DAYS", "Past", "bar", "criteria", "detail", "history_totals", "past", "text"]
