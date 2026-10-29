"""
QuantBIST
Risk budget (Talimat E, DECISIONS K-56). The user sets limits in data/risk_limits.csv; this
measures the account and says how much of each limit is used. It never says what to buy or sell:
/risk denge is only the arithmetic of the distance to a limit ("hesap sonucu, öneri değil").

Windows are fixed (K-56): 60 sessions for volatility and contributions, 250 for beta and the
1-day loss, the previous 20 sessions for liquidity at 20% participation.
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from core.alerts.rules import Alert
from core.config.paths import RISK_LIMITS_FILE

LIMITS_FILE = RISK_LIMITS_FILE
LIMITS_COLUMNS = ["account", "limit", "value", "note"]
VOL_DAYS = 60
BETA_DAYS = 250
PARTICIPATION = 0.20
YELLOW = 0.80
NAMES = {"tek_hisse": "tek hisse", "tek_sektor": "tek sektör", "oynaklik": "portföy oynaklığı (yıllık)",
         "dusus": "zirveden düşüş", "var_1g": "1 günlük kayıp (%95)"}
ACCOUNTS = {"real": "gercek", "paper": "sanal"}
LABEL = "hesap sonucu, öneri değil"


def _pct(x: float, decimals: int = 1) -> str:
    from core.reports.daily import tr

    return f"%{tr(x * 100, decimals)}"


def _code(symbol: str) -> str:
    return symbol.removesuffix(".IS")


# --- limits --------------------------------------------------------------------------------------


def load_limits(account: str, path: Path | None = None, problems: list | None = None) -> dict[str, float]:
    """The limits for one account ("real" / "paper"); rows for "hepsi" apply to both."""

    path = Path(path or LIMITS_FILE)
    if not path.exists():
        return {}
    out: dict[str, float] = {}
    with open(path, encoding="utf-8-sig", newline="") as fh:
        first = fh.readline()
        fh.seek(0)
        delimiter = ";" if ";" in first and "," not in first else ","  # Excel in Turkish saves with ";" (M28)
        for n, row in enumerate(csv.DictReader(fh, delimiter=delimiter), start=2):
            who, name = (row.get("account") or "").strip().lower(), (row.get("limit") or "").strip().lower()
            if who not in ("hepsi", ACCOUNTS[account], "gerçek"):
                if who not in ("gercek", "sanal", "gerçek") and problems is not None:
                    problems.append(f"{path.name} satır {n}: hesap '{who}' tanınmadı")
                continue
            if who == "gerçek" and account != "real":
                continue
            try:
                value = float((row.get("value") or "").replace(",", ".")) / 100
            except ValueError:
                value = None
            if name not in NAMES or value is None or not math.isfinite(value) or value <= 0:
                if problems is not None:
                    problems.append(f"{path.name} satır {n}: '{name}' sınırı okunamadı")
                continue
            if name in out:  # validation M28: row order must not decide; the stricter one holds
                if problems is not None:
                    problems.append(f"{path.name} satır {n}: '{name}' sınırı iki kez yazılmış; sıkı olanı "
                                    f"({_pct(min(out[name], value))}) kullanılıyor")
                value = min(out[name], value)
            out[name] = value
    return out


def state(value: float | None, limit: float | None) -> str:
    if limit is None:
        return "sınır tanımlı değil"
    if value is None:
        return "hesaplanamadı"
    if value > limit:
        return "kırmızı"
    return "sarı" if value >= YELLOW * limit - 1e-12 else "yeşil"  # 80% exactly is yellow (float-safe)


# --- measures ------------------------------------------------------------------------------------


@dataclass
class Measures:
    total: float
    weights: dict[str, float] = field(default_factory=dict)
    unpriced: list[str] = field(default_factory=list)
    volatility: float | None = None
    contribution: dict[str, float] = field(default_factory=dict)
    beta: float | None = None
    var: float | None = None
    liquidity_days: dict[str, float] = field(default_factory=dict)
    drawdown: float | None = None
    pairs: list = field(default_factory=list)
    effective_n: float | None = None


def drawdown(perf: pd.Series | None) -> float | None:
    if perf is None or len(perf) == 0:
        return None
    return float(1 - perf.iloc[-1] / perf.max())


def measure(values: dict[str, float], frames: dict[str, pd.DataFrame], total: float, bench: pd.Series,
            perf: pd.Series | None = None) -> Measures:
    from core.alerts.portfolio import portfolio_risk

    m = Measures(total)
    priced = {}
    for symbol, value in values.items():
        df = frames.get(symbol)
        if value != value or df is None or df.empty:
            m.unpriced.append(symbol)
        else:
            priced[symbol] = value
    if total > 0:
        m.weights = {s: v / total for s, v in priced.items()}
    m.drawdown = drawdown(perf)
    if not priced or m.unpriced:
        return m

    risk = portfolio_risk(priced, {s: frames[s] for s in priced}, total)
    m.var, m.pairs, m.effective_n = risk.var, risk.pairs, risk.effective_n

    closes = pd.DataFrame({s: frames[s]["close"] for s in priced})
    returns = closes.pct_change().dropna()
    w = np.array([m.weights[s] for s in closes.columns])
    recent = returns.iloc[-VOL_DAYS:]
    if len(recent) >= VOL_DAYS:
        cov = recent.cov().to_numpy()
        var_p = float(w @ cov @ w)
        if var_p > 0:
            m.volatility = math.sqrt(var_p) * math.sqrt(252)
            m.contribution = dict(zip(closes.columns, (w * (cov @ w) / var_p).tolist(), strict=True))
    both = pd.concat([returns @ w, bench.pct_change()], axis=1, join="inner").dropna().iloc[-BETA_DAYS:]
    if len(both) >= VOL_DAYS and both.iloc[:, 1].var() > 0:
        m.beta = float(both.cov().iloc[0, 1] / both.iloc[:, 1].var())
    for s, value in priced.items():
        df = frames[s]
        tl = float((df["close"] * df["volume"]).shift(1).rolling(20).mean().iloc[-1])
        if tl == tl and tl > 0:
            m.liquidity_days[s] = value / (tl * PARTICIPATION)
    return m


@dataclass
class Row:
    name: str
    value: float | None
    limit: float | None
    state: str
    text: str


def rows(m: Measures, limits: dict[str, float]) -> list[Row]:
    out = []
    unknown = f"hesaplanamadı: fiyatı olmayan {', '.join(_code(s) for s in m.unpriced)}" if m.unpriced else None

    def add(name, value, detail):
        limit = limits.get(name)
        st = state(value, limit) if not (unknown and name in ("oynaklik", "var_1g")) else "hesaplanamadı"
        if name in ("oynaklik", "var_1g") and unknown:
            detail = unknown
        out.append(Row(name, value, limit, st, detail))

    if m.weights:
        top = max(m.weights, key=m.weights.get)
        add("tek_hisse", m.weights[top], f"en büyük {_code(top)} {_pct(m.weights[top])}")
    else:
        add("tek_hisse", None, "pozisyon yok" if not m.unpriced else unknown)
    out.append(Row("tek_sektor", None, limits.get("tek_sektor"), "bilinmiyor",
                   "sektör kaynağı yok (DECISIONS K-54, D14)"))
    add("oynaklik", m.volatility, f"{VOL_DAYS} seans" if m.volatility is not None else f"{VOL_DAYS} seans veri yok")
    add("dusus", m.drawdown, "hesabın en yüksek değerinden" if m.drawdown is not None else "kayıt yok")
    add("var_1g", m.var, "250 seans tarihsel" if m.var is not None else "ortak veri yetersiz")
    return out


def table_text(account_name: str, m: Measures, table: list[Row]) -> str:
    from core.reports.daily import tr

    lines = [f"🛡 Risk bütçesi – {account_name} hesap ({tr(m.total)} TL)"]
    marks = {"yeşil": "🟢", "sarı": "🟡", "kırmızı": "🔴"}
    for r in table:
        value = _pct(r.value) if r.value is not None else "—"
        limit = f"sınır {_pct(r.limit)}, kullanım %{r.value / r.limit * 100:.0f}" \
            if r.limit and r.value is not None else ("sınır tanımlı değil" if r.limit is None else f"sınır {_pct(r.limit)}")
        lines.append(f"{marks.get(r.state, '⚪')} {NAMES[r.name]}: {value} · {limit} · {r.state} ({r.text})")
    if m.contribution:
        parts = sorted(m.contribution.items(), key=lambda kv: -kv[1])
        lines.append("Risk katkısı: " + ", ".join(f"{_code(s)} {_pct(v, 0)}" for s, v in parts))
    if m.beta is not None:
        lines.append(f"Beta (XU100'e göre, {BETA_DAYS} seans): {tr(m.beta, 2)}")
    if m.effective_n is not None:
        lines.append(f"Etkin pozisyon sayısı: {tr(m.effective_n, 1)}")
    if m.liquidity_days:
        lines.append("Kapanma süresi (20 seans ortalama hacmin %20'si): " + ", ".join(
            f"{_code(s)} {tr(d, 1)} gün" for s, d in sorted(m.liquidity_days.items())))
    if m.pairs:
        lines.append("Birlikte hareket eden: " + ", ".join(f"{_code(a)}+{_code(b)} ({tr(c, 2)})" for a, b, c in m.pairs))
    lines += ["Stres senaryoları: /stres", "Sınırları data/risk_limits.csv'de siz belirlersiniz (HANDBOOK §13). "
              "Sistem ölçer, öneri vermez."]
    return "\n".join(lines)


def summary_line(table: list[Row]) -> str:
    """One line for the daily report."""

    flagged = [r for r in table if r.state in ("sarı", "kırmızı")]
    # validation M28: a limit that could not be measured is never "within"
    unmeasured = [r for r in table if r.limit and r.state not in ("yeşil", "sarı", "kırmızı")]
    if not any(r.limit for r in table):
        return "🛡 Risk bütçesi: sınır tanımlı değil (/risk)"
    parts = [f"{NAMES[r.name]} {r.state} (kullanım %{r.value / r.limit * 100:.0f})" for r in flagged]
    parts += [f"{NAMES[r.name]} ölçülemedi" for r in unmeasured]
    if not parts:
        return "🛡 Risk bütçesi: tanımlı sınırlar içinde (/risk)"
    return "🛡 Risk bütçesi: " + ", ".join(parts) + " (/risk)"


def what_if(values: dict[str, float], total: float, symbol: str, quantity: float, price: float,
            paper: bool) -> tuple[dict[str, float], float]:
    """The values had `quantity` more shares been bought at `price` (nothing is ordered)."""

    out = dict(values)
    out[symbol] = out.get(symbol, 0.0) + quantity * price
    return out, total if paper else total + quantity * price


def after_cuts(quantities: dict[str, float], prices: dict[str, float], cuts: dict[str, int], total: float,
               paper: bool) -> tuple[dict[str, float], float]:
    """Values and account total after the cuts: the paper account keeps the proceeds as cash, the
    real account's value is its shares only, so it shrinks by the proceeds."""

    values = {s: max(q - cuts.get(s, 0), 0) * prices[s] for s, q in quantities.items()}
    return values, total if paper else sum(values.values())


def _single_reachable(m: Measures, limit: float, paper: bool) -> bool:
    # the real account is all shares: with n stocks the largest is at least 1/n of it
    return paper or len(m.weights) * limit >= 1 - 1e-12


def rebalance(m: Measures, limits: dict[str, float], prices: dict[str, float],
              quantities: dict[str, float], paper: bool = True) -> dict[str, int]:
    """
    Shares to reduce per position to return within the limits (arithmetic only). Validation M28:
    the real account's total falls with each sale, so the single-stock cut is solved on the shrinking
    total and repeated until every weight is within; an equal cut cannot change its volatility or
    1-day loss (no cash), so nothing is computed for those there (rebalance_notes says why).
    """

    cuts: dict[str, int] = {}
    single = limits.get("tek_hisse")
    if single and m.weights and _single_reachable(m, single, paper):
        held = {s: q for s, q in quantities.items() if s in m.weights}
        for _ in range(4 * len(held) + 4):
            values, total = after_cuts(held, prices, cuts, m.total, paper)
            over = [(s, v) for s, v in values.items() if total > 0 and v / total > single + 1e-12]
            if not over:
                break
            s, v = max(over, key=lambda kv: kv[1])
            # paper: (v − x) / T ≤ L; real: (v − x) / (T − x) ≤ L
            x = v - single * total if paper else (v - single * total) / (1 - single)
            cuts[s] = cuts.get(s, 0) + max(1, math.ceil(x / prices[s] - 1e-9))
    factors = [limits[n] / v for n, v in (("oynaklik", m.volatility), ("var_1g", m.var))
               if limits.get(n) and v and v > limits[n]]
    if factors and paper:
        keep = min(factors)
        for s, q in quantities.items():
            cuts[s] = max(cuts.get(s, 0), math.ceil(q * (1 - keep)))
    return cuts


def rebalance_notes(m: Measures, limits: dict[str, float], paper: bool) -> list[str]:
    """Limits that selling cannot reach, said instead of computed (validation M28)."""

    notes = []
    single = limits.get("tek_hisse")
    if single and m.weights and max(m.weights.values()) > single and not _single_reachable(m, single, paper):
        n = len(m.weights)
        notes.append(f"tek hisse: gerçek hesabın değeri yalnız hisselerden oluşur; {n} hisseyle en büyük pay en az "
                     f"{_pct(1 / n, 0)}. Satışla {_pct(single, 0)} sınırına inilemez.")
    if not paper:
        for name, value in (("oynaklik", m.volatility), ("var_1g", m.var)):
            if limits.get(name) and value and value > limits[name]:
                notes.append(f"{NAMES[name]}: gerçek hesapta nakit sayılmadığı için eşit azaltma oranı değiştirmez; "
                             "hangi hissenin azaltılacağı bir seçimdir, sistem seçmez.")
    for name, value in (("oynaklik", m.volatility), ("var_1g", m.var)):
        if limits.get(name) and value is None:
            notes.append(f"{NAMES[name]}: ölçülemedi; azaltma hesaplanmadı.")
    if limits.get("dusus") and m.drawdown is not None and m.drawdown > limits["dusus"]:
        notes.append(f"zirveden düşüş {_pct(m.drawdown)}: gerçekleşmiş kayıptır, satışla geri alınmaz.")
    return notes


def rebalance_text(account_name: str, cuts: dict[str, int], prices: dict[str, float],
                   notes: list[str] | None = None, after: list[Row] | None = None) -> str:
    from core.reports.daily import tr

    notes = notes or []
    if not cuts and notes:
        return "\n".join([f"⚖️ {account_name} hesap: azaltma hesabı yok ({LABEL})"] + [f"  • {n}" for n in notes])
    if not cuts:
        return f"⚖️ {account_name} hesap tanımlı sınırların içinde; azaltma hesabı yok ({LABEL})."
    lines = [f"⚖️ Sınırlara dönmek için gereken azaltma – {account_name} hesap ({LABEL})"]
    lines += [f"  {_code(s)}: {n} adet (~{tr(n * prices[s])} TL)" for s, n in sorted(cuts.items())]
    if after:
        lines.append("Azaltma sonrası yeniden ölçüldü: " + ", ".join(
            f"{NAMES[r.name]} {_pct(r.value)} ({r.state})" for r in after if r.limit and r.value is not None))
    lines += [f"  • {n}" for n in notes]
    lines.append("Yalnız matematik; işlem ya da emir oluşturulmaz.")
    return "\n".join(lines)


def evaluate_limits(account: str, table: list[Row], day: date) -> list[Alert]:
    out = []
    for r in table:
        if r.state not in ("sarı", "kırmızı"):
            continue
        severity = 3 if r.state == "kırmızı" else 2
        out.append(Alert(account, "HESAP", f"risk_siniri:{r.name}", severity, r.value, r.limit, day,
                         f"{NAMES[r.name]} {_pct(r.value)}, sınır {_pct(r.limit)} ({r.state}; {r.text})"))
    return out


# --- accounts and commands -----------------------------------------------------------------------


@dataclass
class AccountState:
    account: str
    values: dict[str, float]
    frames: dict[str, pd.DataFrame]
    total: float
    bench: pd.Series
    perf: pd.Series | None
    prices: dict[str, float]
    quantities: dict[str, float]


def account_state(account: str) -> AccountState:
    """The account as the daily report values it (real and paper never mix)."""

    from core.ledger.book import cash_balance, load_ledger
    from core.market.universe import BENCHMARK
    from core.reports.daily import (
        EQUITY_LOG_FILE,
        adjusted_bars,
        performance_index,
        read_equity,
        value_holdings,
    )

    entries = load_ledger()
    holdings, invested = value_holdings(entries, account)
    cash = cash_balance(entries, account) if account == "paper" else 0.0
    frames = {h.position.symbol: adjusted_bars(h.position.symbol) for h in holdings}
    equity = read_equity(EQUITY_LOG_FILE, account)
    perf = performance_index(equity, entries, account) if len(equity) >= 2 else None
    return AccountState(account, {h.position.symbol: h.value for h in holdings}, frames, cash + invested,
                        adjusted_bars(BENCHMARK)["close"], perf, {h.position.symbol: h.price for h in holdings},
                        {h.position.symbol: h.position.quantity for h in holdings})


USAGE = ("Kullanım:\n/risk [gercek|sanal] – risk bütçesi tablosu (varsayılan sanal)\n"
         "/risk ekle THYAO 100 [gercek|sanal] – bu alım yapılsaydı sınırlar nasıl değişirdi (emir değil)\n"
         "/risk denge [gercek|sanal] – sınırlara dönmek için gereken azaltma (hesap sonucu, öneri değil)")


def parse_args(words: list[str]) -> tuple[str, str, tuple[str, float] | None]:
    words = [w.lower().replace("ç", "c").replace("ğ", "g") for w in words]
    account = "real" if any(w in ("gercek", "gerçek") for w in words) else "paper"
    words = [w for w in words if w not in ("gercek", "gerçek", "sanal")]
    if not words:
        return "table", account, None
    if words[0] == "denge" and len(words) == 1:
        return "rebalance", account, None
    if words[0] == "ekle" and len(words) == 3:
        try:
            quantity = float(words[2].replace(",", "."))
        except ValueError:
            raise ValueError(USAGE) from None
        if quantity <= 0:
            raise ValueError("Adet pozitif olmalı.\n" + USAGE)
        return "add", account, (f"{words[1].upper().removesuffix('.IS')}.IS", quantity)
    raise ValueError(USAGE)


def command_text(words: list[str]) -> str:
    try:
        action, account, extra = parse_args(words)
    except ValueError as exc:
        return str(exc)
    st = account_state(account)
    name = ACCOUNTS[account].replace("gercek", "gerçek")
    problems: list[str] = []
    limits = load_limits(account, problems=problems)
    warn = "".join(f"\n⚠️ {p}" for p in problems)
    m = measure(st.values, st.frames, st.total, st.bench, st.perf)
    table = rows(m, limits)
    if action == "table":
        return table_text(name, m, table) + warn
    if action == "rebalance":
        paper = account == "paper"
        cuts = rebalance(m, limits, st.prices, st.quantities, paper=paper)
        after = None
        if cuts:  # validation M28: every cut is re-measured, so the claim "back within" is checked
            values, total = after_cuts(st.quantities, st.prices, cuts, st.total, paper)
            after = rows(measure(values, st.frames, total, st.bench, st.perf), limits)
        return rebalance_text(name, cuts, st.prices, rebalance_notes(m, limits, paper), after) + warn
    symbol, quantity = extra
    from core.reports.daily import adjusted_bars

    frames = dict(st.frames)
    frames.setdefault(symbol, adjusted_bars(symbol))
    if frames[symbol] is None or frames[symbol].empty:
        return f"{_code(symbol)} için fiyat yok; hesap yapılamadı."
    price = float(frames[symbol]["close"].iloc[-1])
    values, total = what_if(st.values, st.total, symbol, quantity, price, paper=account == "paper")
    after = rows(measure(values, frames, total, st.bench, st.perf), limits)
    lines = [f"🧮 Ya şöyle olsaydı: {name} hesaba {_code(symbol)} {quantity:g} adet × {price:.2f} (son kapanış) "
             f"eklenseydi – emir oluşturulmadı, {LABEL}"]
    for before, now in zip(table, after, strict=True):
        b = _pct(before.value) if before.value is not None else "—"
        a = _pct(now.value) if now.value is not None else "—"
        lines.append(f"  {NAMES[now.name]}: {b} → {a} · {now.state}")
    return "\n".join(lines)


def web_rows(account: str) -> dict:
    st = account_state(account)
    table = rows(measure(st.values, st.frames, st.total, st.bench, st.perf), load_limits(account))
    return {"account": ACCOUNTS[account], "total": st.total, "label": LABEL,
            "rows": [{"name": r.name, "value": r.value, "limit": r.limit, "state": r.state, "detail": r.text}
                     for r in table]}


__all__ = ["AccountState", "account_state", "command_text", "parse_args", "web_rows", "LABEL", "LIMITS_FILE", "Measures", "Row", "drawdown", "evaluate_limits", "load_limits", "measure",
           "after_cuts", "rebalance", "rebalance_notes", "rebalance_text", "rows", "state", "summary_line", "table_text", "what_if"]
