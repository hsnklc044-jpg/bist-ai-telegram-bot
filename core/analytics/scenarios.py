"""
QuantBIST
Özellik B: scenario templates (DECISIONS K-55). A calculator, not advice: for a fixed rule it
computes where entry, invalidation and target would be, R after costs, the size a given risk
budget allows, and later how the scenario actually ended.

Levels are K-49's cluster levels; a day's levels use candles up to that day only. Entry is the
NEXT open; a next open at a limit move (±9,5%) is "dolmadı". The outcome is the first of
invalidation / target / HORIZON sessions; a session reaching both counts as invalidation.

Every output ends with DISCLAIMER. Parameters never change after the card is seen (K-55).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from core.analytics import levels as L

COST = 0.0010 + 0.0005  # per side: commission + slippage
MIN_R = 1.5
STRENGTH_MIN = 50
NEAR_ATR = 0.5
VOLUME_X = 1.5
HORIZON = 20
LIMIT_MOVE = 0.095
DEFAULT_RISK = 0.01
LIQUIDITY_SHARE = 0.05  # of the previous 20 sessions' mean TL volume
TEMPLATES = ("destek_tepkisi", "direnc_kirilimi", "trend_geri_cekilme")
TITLES = {"destek_tepkisi": "Destek tepkisi", "direnc_kirilimi": "Direnç kırılımı",
          "trend_geri_cekilme": "Trend içi geri çekilme"}
DISCLAIMER = "Kural çıktısıdır, öneri değildir. Karar ve sorumluluk kullanıcıdadır."
COLUMNS = ["ok", "level", "strength", "invalidation", "target"]


def num(x: float, decimals: int = 2) -> str:
    from core.reports.daily import tr

    return tr(x, decimals)


def r_value(entry: float, invalidation: float, target: float) -> float | None:
    """Reward ÷ risk after costs on both sides; None when the levels cannot form a scenario."""

    if not invalidation < entry < target:
        return None
    gain = target * (1 - COST) - entry * (1 + COST)
    loss = entry * (1 + COST) - invalidation * (1 - COST)
    return gain / loss if loss > 0 else None


def unfavourable(r: float | None) -> bool:
    return r is None or r < MIN_R


def levels_atr(df: pd.DataFrame) -> pd.Series:
    return L.atr(df)


# --- the templates, day by day ------------------------------------------------------------------


def _day_levels(df: pd.DataFrame, recent: int | None = None) -> pd.DataFrame:
    """Per day: nearest cluster support below the close (price, strength), nearest resistance above."""

    n = len(df)
    out = {c: np.full(n, np.nan) for c in ("support", "support_strength", "resistance")}
    close = df["close"].to_numpy(dtype=float)
    a_all = L.atr(df).to_numpy(dtype=float) if n >= L.MIN_CANDLES else None
    for d, _a, groups in L.cluster_days(df, recent):
        if not groups:
            continue
        last = close[d]
        below = [(p, ts) for p, ts in groups if p < last]
        above = [p for p, _ in groups if p > last]
        if below:
            price, ts = max(below, key=lambda g: g[0])
            breaks = L._breaks(close[int(ts.min()):d + 1], a_all[int(ts.min()):d + 1], price)
            out["support"][d] = price
            out["support_strength"][d] = L.strength(int(len(ts)), d - int(ts.max()), breaks)
        if above:
            out["resistance"][d] = min(above)
    return pd.DataFrame(out, index=df.index)


def signals(df: pd.DataFrame, recent: int | None = None) -> dict[str, pd.DataFrame]:
    """For every template: per day ok / level / strength / invalidation / target (NaN when not ok)."""

    close, volume = df["close"], df["volume"]
    a = L.atr(df)
    lv = _day_levels(df, recent)
    sma20, sma50, sma200 = (close.rolling(n).mean() for n in (20, 50, 200))
    prior_volume = volume.shift(1).rolling(20).mean()
    out = {}

    def frame(ok, level, strength, invalidation, target) -> pd.DataFrame:
        ok = ok & (invalidation < close) & (target > close)
        ok = ok.fillna(False).astype(bool)
        t = pd.DataFrame({"ok": ok, "level": level, "strength": strength, "invalidation": invalidation,
                          "target": target}, index=df.index)
        t.loc[~ok, ["level", "strength", "invalidation", "target"]] = np.nan
        return t[COLUMNS]

    s, r = lv["support"], lv["resistance"]
    out["destek_tepkisi"] = frame((lv["support_strength"] >= STRENGTH_MIN) & (close - s <= NEAR_ATR * a),
                                  s, lv["support_strength"], s - a, r)

    prev_r = r.shift(1)
    broke = (close > prev_r + L.BREAK_ATR * a) & (volume >= VOLUME_X * prior_volume)
    inv = prev_r - a
    target = r.where(r.notna(), close + 2 * (close - inv))
    out["direnc_kirilimi"] = frame(broke, prev_r, pd.Series(np.nan, index=df.index), inv, target)

    trend = (sma50 > sma200) & (close > sma50) & ((close - sma20).abs() <= NEAR_ATR * a)
    inv = (s - a).where(s.notna(), sma50 - a)
    target = r.where(r.notna(), close + 2 * (close - inv))
    out["trend_geri_cekilme"] = frame(trend, s, lv["support_strength"], inv, target)
    return out


# --- the outcome --------------------------------------------------------------------------------


@dataclass(frozen=True)
class Outcome:
    result: str  # hedef / geçersizlik / süre doldu / dolmadı
    entry: float | None = None
    exit: float | None = None
    sessions: int = 0
    r: float | None = None
    exit_day: pd.Timestamp | None = None


def outcome(df: pd.DataFrame, t: int, invalidation: float, target: float, horizon: int = HORIZON) -> Outcome | None:
    """How a scenario signalled on row t ended; None while it is still open (or t+1 is unknown)."""

    if t + 1 >= len(df):
        return None
    o, h, lo, c = (df[k].to_numpy(dtype=float) for k in ("open", "high", "low", "close"))
    entry = o[t + 1]
    if abs(entry / c[t] - 1) > LIMIT_MOVE:
        return Outcome("dolmadı")
    risk = entry * (1 + COST) - invalidation * (1 - COST)

    def done(kind, price, i):
        r = (price * (1 - COST) - entry * (1 + COST)) / risk if risk > 0 else None
        return Outcome(kind, entry, price, i - t, r, df.index[i])

    for i in range(t + 1, min(t + 1 + horizon, len(df))):
        first = i == t + 1
        if not first and o[i] <= invalidation:
            return done("geçersizlik", o[i], i)
        if not first and o[i] >= target:
            return done("hedef", o[i], i)
        if lo[i] <= invalidation:
            return done("geçersizlik", invalidation, i)
        if h[i] >= target:
            return done("hedef", target, i)
    if t + horizon < len(df):
        return done("süre doldu", c[t + horizon], t + horizon)
    return None


# --- sizing and texts ---------------------------------------------------------------------------


def size(entry: float, invalidation: float, account: float | None, risk: float, df: pd.DataFrame) -> str:
    if not account or account <= 0:
        return "adet: hesap değeri yok"
    by_risk = math.floor(account * risk / (entry - invalidation))
    liquidity = float((df["close"] * df["volume"]).shift(1).rolling(20).mean().iloc[-1])
    by_liquidity = math.floor(liquidity * LIQUIDITY_SHARE / entry) if liquidity == liquidity else by_risk
    shares = max(min(by_risk, by_liquidity), 0)
    why = "likidite sınırı (20 seans ortalama TL hacminin %5'i)" if by_liquidity < by_risk else \
        f"risk bütçesi %{num(risk * 100, 1)}"
    return (f"{shares} adet ({why}; risk {num(shares * (entry - invalidation), 0)} TL, "
            f"tutar {num(shares * entry, 0)} TL; yalnız hesap, emir değil)")


def _limit_line(df: pd.DataFrame, entry: float, invalidation: float) -> str:
    moves = (df["close"] / df["close"].shift(1) - 1).abs().iloc[-10:]
    gap = (entry - invalidation) / entry * 100
    extra = "; son 10 seansta limit hareketi oldu" if (moves > LIMIT_MOVE).any() else ""
    return (f"     tavan/taban riski: geçersizlik %{num(gap, 1)} uzakta; tek seansta ±%10 limit hareketi "
            f"geçersizliği atlayabilir{extra}")


def _scenario_lines(name: str, df: pd.DataFrame, row: pd.Series, account, risk) -> list[str]:
    close = float(df["close"].iloc[-1])
    r = r_value(close, row["invalidation"], row["target"])
    mark = " · elverişsiz (R < 1,5)" if unfavourable(r) else ""
    level = f"seviye {num(row['level'])}" + (f" (güç {int(row['strength'])})" if row["strength"] == row["strength"] else "") \
        if row["level"] == row["level"] else "seviye: sma50"
    return [f"✅ {TITLES[name]}: {level}",
            f"     giriş varsayımı ertesi açılış (≈ kapanış {num(close)}) · geçersizlik {num(row['invalidation'])} · "
            f"hedef {num(row['target'])} · R {num(r, 2) if r is not None else '—'} (maliyet sonrası){mark}",
            f"     {size(close, row['invalidation'], account, risk, df)}",
            _limit_line(df, close, row["invalidation"])]


def scenario_text(symbol: str, df: pd.DataFrame, account: float | None = None, risk: float = DEFAULT_RISK,
                  cards: dict | None = None) -> str:
    code = symbol.removesuffix(".IS")
    if df is None or df.empty or len(df) < L.MIN_CANDLES:
        return f"{code}: senaryo için yeterli veri yok.\n{DISCLAIMER}"
    table = signals(df, recent=2)
    lines = [f"🧭 {code} senaryoları – {df.index[-1]:%d.%m.%Y} kapanışı (şablonlar K-55; hesap aracı)"]
    for name in TEMPLATES:
        row = table[name].iloc[-1]
        if bool(row["ok"]):
            lines += _scenario_lines(name, df, row, account, risk)
        else:
            lines.append(f"— {TITLES[name]}: koşul bugün yok")
        card = (cards or {}).get(name)
        if card:
            lines.append(f"     karne (tarama dönemi): {card}")
    lines += ["Destek/direnç seviyeleri tarihsel olarak rastgele seviyelerden ayırt edilemedi (K-49).", DISCLAIMER]
    return "\n".join(lines)


def custom_text(symbol: str, df: pd.DataFrame, entry: float, invalidation: float, target: float,
                account: float | None = None, risk: float = DEFAULT_RISK) -> str:
    code = symbol.removesuffix(".IS")
    if not invalidation < entry:
        return f"{code}: geçersizlik girişin altında olmalı.\n{DISCLAIMER}"
    if not target > entry:
        return f"{code}: hedef girişin üstünde olmalı.\n{DISCLAIMER}"
    r = r_value(entry, invalidation, target)
    mark = " · elverişsiz (R < 1,5)" if unfavourable(r) else ""
    lines = [f"🧭 {code} – senin seviyelerin: giriş {num(entry)} · geçersizlik {num(invalidation)} · hedef {num(target)}",
             f"     R {num(r, 2)} (maliyet sonrası; her yön %0,10 komisyon + %0,05 kayma){mark}",
             f"     {size(entry, invalidation, account, risk, df) if df is not None and not df.empty else 'adet: veri yok'}"]
    if df is not None and not df.empty:
        lines.append(_limit_line(df, entry, invalidation))
    lines.append(DISCLAIMER)
    return "\n".join(lines)


def _number(text: str) -> float:
    return float(text.replace(".", "").replace(",", ".") if "," in text else text)


USAGE = ("Kullanım:\n/senaryo THYAO – şablonların bugünkü seviyeleri\n"
         "/senaryo THYAO giris 240 gecersiz 232 hedef 262 – kendi seviyelerinle R ve adet\n"
         "isteğe bağlı risk=%0,5 (varsayılan %1, en çok %5)")


def parse_args(words: list[str]) -> tuple[str, tuple[float, float, float] | None, float]:
    """(code, (entry, invalidation, target) or None, risk share). ValueError with the usage text."""

    import unicodedata

    if not words:
        raise ValueError(USAGE)
    code = words[0].upper().removesuffix(".IS")
    risk, values, rest = DEFAULT_RISK, {}, words[1:]
    names = {"giris": "entry", "destek": "entry", "gecersiz": "invalidation", "hedef": "target"}
    i = 0
    while i < len(rest):
        word = unicodedata.normalize("NFKD", rest[i].lower()).encode("ascii", "ignore").decode()
        if word.startswith("risk="):
            risk = _number(word.removeprefix("risk=").lstrip("%")) / 100
            if not 0 < risk <= 0.05:
                raise ValueError("risk %0,1 ile %5 arasında olmalı.\n" + USAGE)
            i += 1
        elif word in names and i + 1 < len(rest):
            values[names[word]] = _number(rest[i + 1])
            i += 2
        else:
            raise ValueError(USAGE)
    if values and set(values) != {"entry", "invalidation", "target"}:
        raise ValueError("Giriş, geçersizlik ve hedefin üçü birlikte yazılmalı.\n" + USAGE)
    levels = (values["entry"], values["invalidation"], values["target"]) if values else None
    return code, levels, risk


def account_value() -> float | None:
    """The paper account's last recorded value (the sizing base; the real account is never used)."""

    from core.config.paths import EQUITY_LOG_FILE
    from core.reports.daily import read_equity

    equity = read_equity(EQUITY_LOG_FILE, "paper")
    return float(equity.iloc[-1]) if len(equity) else None


def command_text(words: list[str]) -> str:
    from core.reports.daily import adjusted_bars

    try:
        code, levels, risk = parse_args(words)
    except ValueError as exc:
        return str(exc)
    df = adjusted_bars(f"{code}.IS")
    account = account_value()
    if levels:
        return custom_text(f"{code}.IS", df, *levels, account=account, risk=risk)
    return scenario_text(f"{code}.IS", df, account=account, risk=risk)


__all__ = ["COST", "DISCLAIMER", "HORIZON", "MIN_R", "Outcome", "TEMPLATES", "TITLES", "command_text", "custom_text", "outcome", "parse_args",
           "r_value", "scenario_text", "signals", "size", "unfavourable"]
