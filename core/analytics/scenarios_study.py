"""
QuantBIST
The scenario templates' card (Özellik B §4.1, DECISIONS K-55): what each fixed template did in
the screening period (HISTORY_START → SCREEN_END; the holdout is never read). BIST 100 members on
each day only, the default /tara eliminations of that day applied. Whatever comes out is shown as
it is; a card is not evidence (a5, RESEARCH_PROGRAM).

    python -m core.analytics.scenarios_study      # the GitHub Actions run prints it
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from core.analytics import scenarios as S
from core.config.paths import LOG_DIR

CARDS_FILE = LOG_DIR / "scenario_cards.json"
BLOCK = 20
SAMPLES = 2000


@dataclass
class Card:
    events: int = 0
    stocks: int = 0
    target: float = float("nan")
    invalidation: float = float("nan")
    timeout: float = float("nan")
    unfilled: int = 0
    mean_r: float = float("nan")
    low: float = float("nan")
    high: float = float("nan")
    worst_streak: int = 0
    excess: float = float("nan")  # vs XU100 over the same holding, after costs

    def line(self) -> str:
        if not self.events:
            return "olay yok"
        pct = lambda x: f"%{x * 100:.0f}"  # noqa: E731
        interval = f" [{S.num(self.low, 2)}, {S.num(self.high, 2)}]" if self.low == self.low else ""
        return (f"{self.events} olay ({self.stocks} hisse) · hedef {pct(self.target)}, geçersizlik "
                f"{pct(self.invalidation)}, süre doldu {pct(self.timeout)} · ortalama R {S.num(self.mean_r, 2)}"
                f"{interval} · en kötü seri {self.worst_streak} · XU100'e göre {S.num(self.excess * 100, 1)} puan"
                f" · dolmadı {self.unfilled}")


def stock_events(df: pd.DataFrame, bench: pd.DataFrame, allowed: np.ndarray | None, first: int = 0) -> dict[str, list]:
    """Every decided scenario of one stock: (signal day, result, r, excess)."""

    out = {name: [] for name in S.TEMPLATES}
    table = S.signals(df)
    b_open, b_close = bench["open"].reindex(df.index), bench["close"].reindex(df.index)
    for name in S.TEMPLATES:
        part = table[name]
        for t in np.flatnonzero(part["ok"].to_numpy()):
            if t < first or (allowed is not None and not allowed[t]):
                continue
            o = S.outcome(df, t, part["invalidation"].iloc[t], part["target"].iloc[t])
            if o is None:
                continue
            if o.result == "dolmadı":
                out[name].append((df.index[t], o.result, None, None))
                continue
            own = o.exit * (1 - S.COST) / (o.entry * (1 + S.COST)) - 1
            market = b_close.loc[o.exit_day] / b_open.iloc[t + 1] - 1
            out[name].append((df.index[t], o.result, o.r, float(own - market)))
    return out


def _interval(days: pd.Series, seed: int = 0) -> tuple[float, float]:
    values = days.to_numpy(dtype=float)
    n = len(values)
    if n < 2 * BLOCK:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    blocks = int(np.ceil(n / BLOCK))
    starts = rng.integers(0, n, size=(SAMPLES, blocks))
    index = ((starts[:, :, None] + np.arange(BLOCK)) % n).reshape(SAMPLES, -1)[:, :n]
    means = values[index].mean(axis=1)
    low, high = np.quantile(means, [0.025, 0.975])
    return float(low), float(high)


def summarize(events: list) -> Card:
    if not events:
        return Card()
    df = pd.DataFrame(events, columns=["symbol", "day", "result", "r", "excess"]).sort_values("day")
    decided = df[df["result"] != "dolmadı"]
    card = Card(events=len(decided), stocks=int(decided["symbol"].nunique()),
                unfilled=int((df["result"] == "dolmadı").sum()))
    if decided.empty:
        return card
    card.target = float((decided["result"] == "hedef").mean())
    card.invalidation = float((decided["result"] == "geçersizlik").mean())
    card.timeout = float((decided["result"] == "süre doldu").mean())
    card.mean_r = float(decided["r"].mean())
    card.excess = float(decided["excess"].mean())
    card.low, card.high = _interval(decided.groupby("day")["r"].mean().dropna())
    streak = best = 0
    for result in decided["result"]:
        streak = streak + 1 if result == "geçersizlik" else 0
        best = max(best, streak)
    card.worst_streak = best
    return card


def study(data) -> dict[str, Card]:
    from core.backtest.run import SCREEN_END
    from core.screen import elimination as E
    from core.screen.card import HISTORY_START
    from core.screen.elimination import Settings

    frames, bench, eligible = data
    bench = bench.loc[:SCREEN_END]
    events = {name: [] for name in S.TEMPLATES}
    actions = E.corporate_actions()
    for symbol, df in sorted(frames.items()):
        df = df.loc[:SCREEN_END]  # outcomes after the screening period are never read
        if df.empty:
            continue
        ok = np.ones(len(df), dtype=bool)
        if eligible is not None and symbol in eligible.columns:
            ok &= eligible[symbol].reindex(df.index).ffill().fillna(False).astype(bool).to_numpy()
        ok &= ~E.mask(E.frame(df, symbol, bench.index, actions), Settings(), None)
        first = int(df.index.searchsorted(pd.Timestamp(HISTORY_START)))
        for name, rows in stock_events(df, bench, ok, first).items():
            events[name] += [(symbol, *row) for row in rows]
    return {name: summarize(rows) for name, rows in events.items()}


def study_text(cards: dict[str, Card]) -> str:
    from core.backtest.run import SCREEN_END
    from core.screen.card import HISTORY_START

    lines = [f"Senaryo şablonlarının karnesi (K-55; tarama dönemi {HISTORY_START} → {SCREEN_END:%Y-%m-%d}, holdout yok, "
             "BIST 100 geçmiş üyeliği, varsayılan eleme; maliyet sonrası; kanıt değildir)"]
    for name in S.TEMPLATES:
        lines.append(f"  {S.TITLES[name]}: {cards[name].line()}")
    lines.append("  R aralığı: %95, 20 seanslık blok bootstrap (olay günleri). Hipotez sınaması yalnız a5 döngüsüyle.")
    return "\n".join(lines)


def save(cards: dict[str, Card], path: Path | None = None) -> None:
    path = Path(path or CARDS_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({k: asdict(v) for k, v in cards.items()}), encoding="utf-8")


def load_lines(path: Path | None = None) -> dict[str, str]:
    """Each template's card line from the cache, for /senaryo (empty when never computed)."""

    path = Path(path or CARDS_FILE)
    try:
        raw = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except (OSError, ValueError):
        return {}
    return {k: Card(**v).line() for k, v in raw.items() if k in S.TEMPLATES}


def main(argv: list[str] | None = None) -> int:
    from core.infrastructure.console import utf8_output
    from core.screen import command

    utf8_output()
    cards = study(command._history_data())
    save(cards)
    print(study_text(cards))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["Card", "load_lines", "save", "stock_events", "study", "study_text", "summarize"]
