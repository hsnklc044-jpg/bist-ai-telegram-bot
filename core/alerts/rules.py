"""
QuantBIST
Alert rules. Every rule sees only candles up to `as_of` (final sessions).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from core.config import alerts as cfg

SEVERITY = {1: "düşük", 2: "orta", 3: "yüksek"}


@dataclass(frozen=True)
class Alert:
    account: str
    symbol: str  # "HESAP" for account-level alerts
    rule: str
    severity: int
    value: float
    threshold: float
    data_date: date
    message: str

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.account, self.symbol, self.rule)

    @property
    def severity_name(self) -> str:
        return SEVERITY[self.severity]

    def line(self) -> str:
        code = self.symbol.removesuffix(".IS")
        return f"[{self.severity_name}] {code}: {self.message}"


def _n(x: float, decimals: int = 2) -> str:
    """Turkish decimal format."""

    return f"{x:,.{decimals}f}".replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def _atr(df: pd.DataFrame, window: int) -> pd.Series:
    prev = df["close"].shift(1)
    tr = pd.concat(
        [df["high"] - df["low"], (df["high"] - prev).abs(), (df["low"] - prev).abs()], axis=1
    ).max(axis=1)
    return tr.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()


def _locked_down_streak(df: pd.DataFrame) -> int:
    change = df["close"].pct_change()
    locked = (df["high"] <= df["low"]) & (change <= -cfg.LIMIT_MOVE)
    streak = 0
    for flag in reversed(locked.tolist()):
        if not flag:
            break
        streak += 1
    return streak


def evaluate_position(
    account: str,
    symbol: str,
    quantity: float,
    opened: date,
    candles: pd.DataFrame,
    as_of: date | None = None,
    account_value: float | None = None,
    liquidity_rank: int | None = None,
    unconfirmed_action: str | None = None,
    reference_day: date | None = None,
    unrecorded_actions: list[str] | None = None,
) -> list[Alert]:
    """
    candles: split-adjusted FINAL daily candles of the symbol.
    account_value: total value of the account (for concentration).
    liquidity_rank: turnover rank of the symbol in the universe (1 = most liquid).
    unconfirmed_action: note of a corporate action that is not yet confirmed.
    reference_day: the session the report is for (stale-data check).
    unrecorded_actions: corporate actions after the entry with no bonus/rights
        row in the ledger (quantity and profit are then wrong).
    """

    df = candles if as_of is None else candles[candles.index <= pd.Timestamp(as_of)]
    if df.empty:
        return [
            Alert(account, symbol, "veri", 1, 0, 0, as_of or date.today(), "fiyat verisi yok; uyarılar hesaplanamadı")
        ]

    day = df.index[-1].date()
    close = float(df["close"].iloc[-1])
    out: list[Alert] = []

    def add(rule, severity, value, threshold, message):
        out.append(Alert(account, symbol, rule, severity, float(value), float(threshold), day, message))

    # 1. Stop level (same measure as the backtest's ATR stop, trailing from the entry)
    atr = _atr(df, cfg.ATR_WINDOW).iloc[-1]
    since = df[df.index >= pd.Timestamp(opened)]
    if not pd.isna(atr) and not since.empty:
        stop = float(since["close"].max()) - cfg.STOP_ATR_MULTIPLE * float(atr)
        if close < stop:
            add("stop", 3, close, stop,
                f"kapanış {_n(close)}, iz süren stop seviyesinin ({_n(stop)}) altında "
                f"(alıştan beri en yüksek kapanış − {cfg.STOP_ATR_MULTIPLE:g} × ATR)")
        elif close - stop < cfg.STOP_NEAR_ATR * float(atr):
            add("stop_yakin", 2, close, stop,
                f"kapanış {_n(close)}, stop seviyesine ({_n(stop)}) {cfg.STOP_NEAR_ATR:g} ATR'den yakın")

    # 2. Locked limit-down
    streak = _locked_down_streak(df)
    if streak:
        add("taban_kilit", 3, streak, 1,
            f"{streak} gündür tabanda kilitli; bu günlerde satış yapılamamış olabilir")

    # 3. Parabolic run-up
    closes = df["close"]
    if len(closes) > cfg.RUN_UP_LONG_DAYS:
        r_long = close / float(closes.iloc[-cfg.RUN_UP_LONG_DAYS - 1]) - 1
        if r_long > cfg.RUN_UP_LONG:
            add("parabolik", 2, r_long, cfg.RUN_UP_LONG,
                f"son {cfg.RUN_UP_LONG_DAYS} seansta %{r_long * 100:.0f} yükseldi; testlerde en büyük "
                "kayıplar bu tür yükselişlerin ardından geldi")
    if len(closes) > cfg.RUN_UP_SHORT_DAYS and not any(a.rule == "parabolik" for a in out):
        r_short = close / float(closes.iloc[-cfg.RUN_UP_SHORT_DAYS - 1]) - 1
        if r_short > cfg.RUN_UP_SHORT:
            add("parabolik", 2, r_short, cfg.RUN_UP_SHORT,
                f"son {cfg.RUN_UP_SHORT_DAYS} seansta %{r_short * 100:.0f} yükseldi")

    # 4. Liquidity
    turnover = (df["close"] * df["volume"].where(df["volume"] > 0)).tail(cfg.TURNOVER_DAYS).mean()
    value = quantity * close
    if not pd.isna(turnover) and turnover > 0 and value / turnover > cfg.POSITION_TO_TURNOVER:
        add("likidite", 2, value / turnover, cfg.POSITION_TO_TURNOVER,
            f"pozisyon, günlük ortalama işlem hacminin %{_n(value / turnover * 100, 1)}'i; çıkışta fiyatı bozabilir")
    if liquidity_rank is not None and liquidity_rank > cfg.LIQUIDITY_TOP:
        add("likidite_sira", 2, liquidity_rank, cfg.LIQUIDITY_TOP,
            f"likidite sırası {liquidity_rank}; ilk {cfg.LIQUIDITY_TOP}'nin dışında")

    # 5. Concentration
    if account_value and account_value > 0 and value / account_value > cfg.CONCENTRATION:
        add("yogunlasma", 2, value / account_value, cfg.CONCENTRATION,
            f"bu hissenin hesaptaki payı %{value / account_value * 100:.0f}")

    # 6. Data
    ref = reference_day or day
    if (pd.Timestamp(ref) - pd.Timestamp(day)).days > cfg.STALE_DAYS:
        add("veri", 1, (pd.Timestamp(ref) - pd.Timestamp(day)).days, cfg.STALE_DAYS,
            f"son fiyat {day}; veri güncel değil, uyarılar eski veriye dayanıyor")
    for note in unrecorded_actions or []:
        add("defter_islem", 2, 0, 0,
            f"alıştan sonra şirket işlemi var ({note}); defterde bedelsiz/bedelli satırı yok, "
            "adet ve kâr/zarar yanlış görünebilir")
    if unconfirmed_action:
        add("veri_islem", 1, 0, 0, f"doğrulanmamış şirket işlemi: {unconfirmed_action}")

    return out


def evaluate_account(account: str, equity: pd.Series, as_of: date | None = None) -> list[Alert]:
    """
    Account-level alerts. `equity`: the account's growth with buys and sales left out
    (core.reports.daily.performance_index); for the paper account that is its value.
    """

    if as_of is not None:
        equity = equity[equity.index <= pd.Timestamp(as_of)]
    if len(equity) < 2:
        return []
    dd = float(equity.iloc[-1] / equity.max() - 1)
    if dd < -cfg.ACCOUNT_DRAWDOWN:
        return [
            Alert(account, "HESAP", "hesap_dusus", 3, dd, -cfg.ACCOUNT_DRAWDOWN, equity.index[-1].date(),
                  f"hesap zirvesinden %{_n(-dd * 100, 1)} aşağıda (alım ve satışlar kâr/zarar sayılmadan)")
        ]
    return []


__all__ = ["Alert", "SEVERITY", "evaluate_position", "evaluate_account"]
