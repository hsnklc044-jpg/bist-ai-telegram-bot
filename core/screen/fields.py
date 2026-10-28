"""
QuantBIST
/tara fields. The ones the live technical view shows (ema20, ema50, rsi, macd, volume ratio,
ATR %) are taken from core.strategy.score.score_frame itself, so a screen and the bot's view
can never disagree; the rest use the same library (ta) with the same rounding. Only the fields
a screen asks for are computed. Every value comes from closed candles only (the price store's
open candle is dropped before this point).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Field:
    group: str
    text: str
    unit: str
    param: int | None = None  # default parameter, for fields written as name(n)


FIELDS = {
    # trend
    "ema": Field("Trend", "üssel ortalama, ema(n) ya da ema20/ema100 gibi", "TL", 20),
    "sma": Field("Trend", "basit ortalama, sma(n) ya da sma200 gibi", "TL", 20),
    "ema20": Field("Trend", "20 günlük üssel ortalama (canlı analizle aynı)", "TL"),
    "ema50": Field("Trend", "50 günlük üssel ortalama (canlı analizle aynı)", "TL"),
    "ema200": Field("Trend", "200 günlük üssel ortalama", "TL"),
    "egim": Field("Trend", "egim(alan, n): alanın n seanstaki yüzde değişimi; egim(sma200,21)>0 = 200 günlük "
                           "ortalama 21 seanstır yükseliyor", "%"),
    "uzaklik_ema": Field("Trend", "kapanışın ema(n)'ye uzaklığı", "%", 20),
    "uzaklik_sma": Field("Trend", "kapanışın sma(n)'ye uzaklığı", "%", 20),
    "adx": Field("Trend", "ADX(n), trendin gücü (yönsüz)", "0–100", 14),
    "supertrend": Field("Trend", "Supertrend (10, 3) yönü: 1 yukarı, -1 aşağı", "±1"),
    # momentum
    "rsi": Field("Momentum", "RSI(n) (14: canlı analizle aynı)", "0–100", 14),
    "macd": Field("Momentum", "MACD (12, 26) (canlı analizle aynı)", "TL"),
    "macd_sinyal": Field("Momentum", "MACD sinyal çizgisi (9)", "TL"),
    "macd_hist": Field("Momentum", "MACD − sinyal", "TL"),
    "stok_k": Field("Momentum", "stokastik %K (14)", "0–100"),
    "stok_d": Field("Momentum", "stokastik %D (3)", "0–100"),
    "roc": Field("Momentum", "n günlük değişim oranı", "%", 10),
    "mom": Field("Momentum", "momentum: kapanış − n seans önceki kapanış", "TL", 10),
    "cci": Field("Momentum", "CCI(n), emtia kanal endeksi", "puan", 20),
    "getiri": Field("Momentum", "son n seans getiri (1 ay ≈ 21, 3 ay ≈ 63)", "%", 20),
    "momentum10": Field("Momentum", "kapanış − 10 seans önceki kapanış (TradingView 'Mom, 10')", "TL"),
    "degisim_1h": Field("Momentum", "son 5 seans değişim (TradingView 'Değ, 1H')", "%"),
    "degisim_1a": Field("Momentum", "son 21 seans değişim (TradingView 'Değ/Perf, 1A')", "%"),
    "degisim_3a": Field("Momentum", "son 63 seans değişim (TradingView 'Perf, 3A')", "%"),
    "getiri_6a_1a_haric": Field("Momentum", "6 ay getirisi, son 1 ay hariç: kapanış[t−21] / kapanış[t−126] − 1 "
                                            "(Jegadeesh & Titman 6-1)", "%"),
    "getiri_12a_1a_haric": Field("Momentum", "12 ay getirisi, son 1 ay hariç: kapanış[t−21] / kapanış[t−252] − 1 "
                                             "(12-1 momentum)", "%"),
    "rs_puan": Field("Göreli güç", "ağırlıklı göreli güç puanı: 0,4×getiri(63) + 0,2×(126, 189, 252) "
                                   "(IBD/O'Neil RS yaklaşımı)", "%"),
    "getiri_5g": Field("Momentum", "son 5 seans getiri", "%"),
    "getiri_20g": Field("Momentum", "son 20 seans getiri", "%"),
    "getiri_60g": Field("Momentum", "son 60 seans getiri", "%"),
    # volatility
    "atr": Field("Oynaklık", "ATR(n), ortalama gerçek aralık", "TL", 14),
    "atr_yuzde": Field("Oynaklık", "ATR(14) / kapanış (canlı analizle aynı)", "%"),
    "bb_ust": Field("Oynaklık", "Bollinger üst bandı (20, 2)", "TL"),
    "bb_alt": Field("Oynaklık", "Bollinger alt bandı (20, 2)", "TL"),
    "bb_genislik": Field("Oynaklık", "Bollinger genişliği / orta bant", "%"),
    "bb_yuzde": Field("Oynaklık", "Bollinger %b ×100 (0 alt bant, 100 üst bant)", "%"),
    "bb_genislik_yuzdelik": Field("Oynaklık", "bugünkü genişliğin son 126 seanstaki yüzdelik sırası", "0–100"),
    "oynaklik_20g": Field("Oynaklık", "20 günlük tarihsel oynaklık (yıllık)", "%"),
    "oynaklik_60g": Field("Oynaklık", "60 günlük tarihsel oynaklık (yıllık)", "%"),
    "oynaklik_sira": Field("Oynaklık", "oynaklik_60g'nin taranan evrendeki yüzdelik sırası (100 = en oynak)", "0–100"),
    # volume
    "hacim_oran": Field("Hacim", "bugünkü hacim / önceki n gün ortalaması (20: canlı analizle aynı)", "×", 20),
    "hacim_degisim": Field("Hacim", "bugünkü hacmin dünküne göre değişimi", "%"),
    "ort_hacim": Field("Hacim", "n günlük ortalama hacim (adet)", "milyon adet", 30),
    "vwma": Field("Hacim", "hacim ağırlıklı ortalama fiyat, n gün", "TL", 20),
    "vwma20": Field("Hacim", "hacim ağırlıklı ortalama fiyat, 20 gün (TradingView 'VWMA, 20')", "TL"),
    "goreli_hacim": Field("Hacim", "bugünkü hacim / önceki 10 seans ortalaması (TradingView 'Göreceli hacim'; "
                                   "hacim_oran 20 günlüktür)", "×"),
    "ortalama_hacim_30g": Field("Hacim", "30 günlük ortalama hacim, adet (TradingView 'Ort. hacim, 30G')", "adet"),
    "likidite": Field("Hacim", "20 günlük ortalama işlem hacmi, TL (likidite= seçeneği milyon TL'dir)", "TL"),
    "obv_egim": Field("Hacim", "OBV'nin 20 günlük değişimi / 20 günlük toplam hacim", "%"),
    "islem_tl": Field("Hacim", "20 günlük ortalama işlem hacmi", "milyon TL"),
    # relative strength
    "gg_20": Field("Göreli güç", "son 20 seans getirisi − XU100'ünki", "puan"),
    "gg_60": Field("Göreli güç", "son 60 seans getirisi − XU100'ünki", "puan"),
    "gg_sira": Field("Göreli güç", "gg_60'ın taranan evrendeki yüzdelik sırası", "0–100"),
    "goreli_guc_yuzdelik": Field("Göreli güç", "rs_puan'ın taranan evrendeki yüzdelik sırası (Minervini/IBD "
                                               "'RS rating' yaklaşımı)", "0–100"),
    "momentum_sira": Field("Göreli güç", "getiri_6a_1a_haric'in taranan evrendeki yüzdelik sırası", "0–100"),
    "beta": Field("Göreli güç", "son 252 seansta XU100'e göre beta", "×"),
    # price position
    "destek_uzaklik_atr": Field("Seviye", "en yakın küme desteğine uzaklık, ATR (negatif: altta; K-49, teknik seviye)",
                                "ATR"),
    "direnc_uzaklik_atr": Field("Seviye", "en yakın küme direncine uzaklık, ATR (pozitif: üstte)", "ATR"),
    "seviye_gucu": Field("Seviye", "en yakın küme seviyesinin güç puanı (dokunma, yaş, kırılma; sabit formül)", "0–100"),
    "kirdi_yukari": Field("Seviye", "kirdi_yukari(direnc) ile yazılır: kapanış dünkü en yakın direnci 0,5 ATR'den "
                                    "fazla geçti", "1/0"),
    "kirdi_asagi": Field("Seviye", "kirdi_asagi(destek) ile yazılır: kapanış dünkü en yakın desteğin 0,5 ATR'den "
                                   "fazla altına indi", "1/0"),
    "zirve_52h": Field("Fiyat konumu", "52 hafta (252 seans) en yükseği, bugün dahil", "TL"),
    "dip_52h": Field("Fiyat konumu", "52 hafta (252 seans) en düşüğü, bugün dahil", "TL"),
    "zirve_52h_oran": Field("Fiyat konumu", "kapanış / 52 hafta en yükseği × 100 (95 = zirvenin %95'i)", "%"),
    "dip_52h_oran": Field("Fiyat konumu", "kapanış / 52 hafta en düşüğü × 100 (130 = dibin %30 üstü)", "%"),
    "zirve_uzaklik": Field("Fiyat konumu", "kapanışın 52 hafta (252 seans) zirvesine uzaklığı", "%"),
    "dip_uzaklik": Field("Fiyat konumu", "kapanışın 52 hafta dibine uzaklığı", "%"),
    "yuksek_20g": Field("Fiyat konumu", "önceki 20 seansın en yükseği (bugün hariç)", "TL"),
    "dusuk_20g": Field("Fiyat konumu", "önceki 20 seansın en düşüğü (bugün hariç)", "TL"),
    "zirve_1a": Field("Fiyat konumu", "son 21 seansın en yükseği, bugün dahil (TradingView 'Yüksek, 1A')", "TL"),
    "bosluk": Field("Fiyat konumu", "açılışın önceki kapanışa göre boşluğu", "%"),
    "kapanis": Field("Fiyat konumu", "son kapanış", "TL"),
    "acilis": Field("Fiyat konumu", "son açılış", "TL"),
}
ALIASES = {"hacim": "hacim_oran", "goreli_guc": "gg_20", "stokastik": "stok_k"}
# ranked across the scanned stocks (engine), each day's members (card), the list (/tara_aciklama): rank -> base
RANKED = {"gg_sira": "gg_60", "goreli_guc_yuzdelik": "rs_puan", "momentum_sira": "getiri_6a_1a_haric",
          "oynaklik_sira": "oynaklik_60g"}
CROSS_SECTIONAL = set(RANKED)
LEVEL_SERIES = ("destek_uzaklik_atr", "direnc_uzaklik_atr", "seviye_gucu", "kirdi_yukari", "kirdi_asagi")
SCORE_FRAME = {"ema20": "ema20", "ema50": "ema50", "rsi": "rsi", "macd": "macd", "hacim_oran": "volume_ratio"}
SUPERTREND = (10, 3.0)


def key(name: str, param: int | None = None) -> str:
    """The column name of a field: the default parameter is dropped; ema 20/50/200 use their shortcuts."""

    default = FIELDS[name].param
    if default is None:
        return name
    p = default if param is None else param
    if name == "ema":
        return f"ema{p}" if p in (20, 50, 200) else f"ema({p})"
    return name if p == default else f"{name}({p})"


def split(column: str) -> tuple[str, int | None]:
    if column.startswith("egim("):
        return "egim", None
    if "(" in column:
        name, rest = column.split("(", 1)
        return name, int(rest.rstrip(")"))
    return column, FIELDS[column].param


def _adx(high: pd.Series, low: pd.Series, close: pd.Series, window: int) -> pd.Series:
    """ta's ADXIndicator(...).adx(), bit for bit (same arrays, same recursions, same order), with
    numpy arrays instead of one pandas lookup per row (test_screen_engine.FastAdxTest)."""

    close_shift = close.shift(1)
    pdm = np.amax([np.array(high), np.array(close_shift)], axis=0)
    pdn = np.amin([np.array(low), np.array(close_shift)], axis=0)
    ddm = pd.Series(pdm) - pd.Series(pdn)
    n = len(close) - (window - 1)
    if n < window + 2:
        return pd.Series(np.nan, index=close.index)

    def smooth(values: pd.Series) -> np.ndarray:
        out = np.zeros(n)
        out[0] = values.dropna().iloc[0:window].sum()
        arr = values.reset_index(drop=True).to_numpy()
        for i in range(1, n - 1):
            out[i] = out[i - 1] - (out[i - 1] / float(window)) + arr[window + i]
        return out

    diff_up = high - high.shift(1)
    diff_down = low.shift(1) - low
    trs = smooth(ddm)
    dip = smooth(abs(((diff_up > diff_down) & (diff_up > 0)) * diff_up))
    din = smooth(abs(((diff_down > diff_up) & (diff_down > 0)) * diff_down))
    with np.errstate(divide="ignore", invalid="ignore"):
        plus = np.where(trs != 0, 100 * (dip / trs), 0.0)
        minus = np.where(trs != 0, 100 * (din / trs), 0.0)
        total = plus + minus
        dx = np.where(total != 0, 100 * np.abs((plus - minus) / total), 0.0)
    adx = np.zeros(n)
    adx[window] = dx[0:window].mean()
    for i in range(window + 1, n):
        adx[i] = ((adx[i - 1] * (window - 1)) + dx[i - 1]) / float(window)
    return pd.Series(np.concatenate((np.zeros(window - 1), adx)), index=close.index)


def _supertrend(df: pd.DataFrame, period: int, multiplier: float) -> pd.Series:
    from core.strategy.score import average_true_range

    high, low, close = df["high"].to_numpy(), df["low"].to_numpy(), df["close"].to_numpy()
    atr = average_true_range(df["high"], df["low"], df["close"], window=period).to_numpy()
    mid = (high + low) / 2
    upper, lower = mid + multiplier * atr, mid - multiplier * atr
    out = np.full(len(close), np.nan)
    fu = fl = direction = None
    for i in range(period, len(close)):
        if fu is None:
            fu, fl, direction = upper[i], lower[i], 1.0
        else:
            fu = upper[i] if upper[i] < fu or close[i - 1] > fu else fu
            fl = lower[i] if lower[i] > fl or close[i - 1] < fl else fl
            if direction < 0 and close[i] > fu:
                direction = 1.0
            elif direction > 0 and close[i] < fl:
                direction = -1.0
        out[i] = direction
    return pd.Series(out, index=df.index)


class _Table:
    def __init__(self, df: pd.DataFrame, bench_close: pd.Series, recent: int | None = None):
        self.recent = recent
        self.df, self.close = df, df["close"]
        self.bench = bench_close.reindex(df.index)
        self.memo: dict[str, pd.Series] = {}
        self._score = None
        self._macd = None
        self._bb = None
        self._levels = None

    def score(self):
        if self._score is None:
            from core.strategy.score import score_frame

            self._score = score_frame(self.df)
        return self._score

    def macd(self):
        if self._macd is None:
            from ta.trend import MACD

            self._macd = MACD(self.close)
        return self._macd

    def bb(self):
        if self._bb is None:
            from ta.volatility import BollingerBands

            self._bb = BollingerBands(self.close, window=20, window_dev=2)
        return self._bb

    def get(self, column: str) -> pd.Series:
        if column not in self.memo:
            self.memo[column] = self._compute(column)
        return self.memo[column]

    def _ret(self, n: int) -> pd.Series:
        return (self.close / self.close.shift(n) - 1) * 100

    def _compute(self, column: str) -> pd.Series:  # noqa: C901 - one branch per field, on purpose
        from ta.momentum import ROCIndicator, RSIIndicator, StochasticOscillator
        from ta.trend import EMAIndicator, SMAIndicator
        from ta.volume import OnBalanceVolumeIndicator

        from core.strategy.score import average_true_range

        name, n = split(column)
        df, close = self.df, self.close
        if name in LEVEL_SERIES:  # support / resistance (core.analytics.levels, K-49), computed once per stock
            if self._levels is None:
                from core.analytics.levels import daily_series

                self._levels = daily_series(df, self.recent)
            return self._levels[name]
        if name == "egim":  # egim(<field>,<n>)
            inner, _, days = column[5:-1].rpartition(",")
            base = self.get(inner)
            return (base / base.shift(int(days)) - 1) * 100
        if name in ("getiri_6a_1a_haric", "getiri_12a_1a_haric"):
            back = 126 if name.startswith("getiri_6a") else 252
            return (close.shift(21) / close.shift(back) - 1) * 100
        if name == "rs_puan":
            return 0.4 * self._ret(63) + 0.2 * self._ret(126) + 0.2 * self._ret(189) + 0.2 * self._ret(252)
        if name in ("zirve_52h", "zirve_52h_oran"):
            top = df["high"].rolling(252, min_periods=252).max()
            return top if name == "zirve_52h" else close / top * 100
        if name in ("dip_52h", "dip_52h_oran"):
            bottom = df["low"].rolling(252, min_periods=252).min()
            return bottom if name == "dip_52h" else close / bottom * 100
        if name == "oynaklik_60g":
            return close.pct_change().rolling(60).std() * math.sqrt(252) * 100
        if column in SCORE_FRAME:
            return self.score()[SCORE_FRAME[column]]
        if name == "hacim_oran":
            from core.strategy.score import volume_ratio_series

            return volume_ratio_series(df["volume"], n)
        if name == "goreli_hacim":
            from core.strategy.score import volume_ratio_series

            return volume_ratio_series(df["volume"], 10)
        if name == "momentum10":
            return close - close.shift(10)
        if name in ("degisim_1h", "degisim_1a", "degisim_3a"):
            return self._ret({"1h": 5, "1a": 21, "3a": 63}[name[8:]])
        if name == "vwma20":
            return self.get("vwma")
        if name == "ortalama_hacim_30g":
            return df["volume"].rolling(30).mean()
        if name == "likidite":
            return (close * df["volume"]).rolling(20).mean()
        if name == "zirve_1a":
            return df["high"].rolling(21).max()
        if name == "hacim_degisim":
            return (df["volume"] / df["volume"].shift(1) - 1) * 100
        if name == "ort_hacim":
            return df["volume"].rolling(n).mean() / 1e6
        if name == "vwma":
            return (close * df["volume"]).rolling(n).sum() / df["volume"].rolling(n).sum()
        if name == "mom":
            return close - close.shift(n)
        if name == "cci":
            from ta.trend import CCIIndicator

            return CCIIndicator(df["high"], df["low"], close, window=n).cci()
        if name == "getiri":
            return self._ret(n)
        if name == "beta":
            r, m = close.pct_change(), self.bench.pct_change()
            return r.rolling(252, min_periods=252).cov(m) / m.rolling(252, min_periods=252).var()
        if column == "atr_yuzde":
            return self.score()["volatility"] * 100
        if name in ("ema", "ema200"):
            return EMAIndicator(close, window=200 if name == "ema200" else n).ema_indicator().round(4)
        if name == "sma":
            return SMAIndicator(close, window=n).sma_indicator().round(4)
        if name in ("uzaklik_ema", "uzaklik_sma"):
            average = self.get(key(name.split("_")[1], n))
            return (close / average - 1) * 100
        if name == "adx":  # the first 2n values are the recursion's warm-up (zeros in ta): unknown
            return _adx(df["high"], df["low"], close, n).where(pd.Series(np.arange(len(df)) >= 2 * n, index=df.index))
        if name == "supertrend":
            return _supertrend(df, *SUPERTREND)
        if name == "rsi":
            return RSIIndicator(close, window=n).rsi().round(4)
        if name == "macd_sinyal":
            return self.macd().macd_signal().round(4)
        if name == "macd_hist":
            return self.macd().macd_diff().round(4)
        if name in ("stok_k", "stok_d"):
            stoch = StochasticOscillator(df["high"], df["low"], close, window=14, smooth_window=3)
            return stoch.stoch() if name == "stok_k" else stoch.stoch_signal()
        if name == "roc":
            return ROCIndicator(close, window=n).roc()
        if name.startswith("getiri_"):
            return self._ret(int(name[7:-1]))
        if name == "atr":
            atr = average_true_range(df["high"], df["low"], close, window=n)
            return atr.where(pd.Series(np.arange(len(df)) >= n - 1, index=df.index))
        if name == "bb_ust":
            return self.bb().bollinger_hband()
        if name == "bb_alt":
            return self.bb().bollinger_lband()
        if name == "bb_genislik":
            return self.bb().bollinger_wband()
        if name == "bb_yuzde":
            return self.bb().bollinger_pband() * 100
        if name == "bb_genislik_yuzdelik":
            return self.get("bb_genislik").rolling(126, min_periods=126).rank(pct=True) * 100
        if name == "oynaklik_20g":
            return close.pct_change().rolling(20).std() * math.sqrt(252) * 100
        if name == "obv_egim":
            obv = OnBalanceVolumeIndicator(close, df["volume"]).on_balance_volume()
            return (obv - obv.shift(20)) / df["volume"].rolling(20).sum() * 100
        if name == "islem_tl":
            return (close * df["volume"]).rolling(20).mean() / 1e6
        if name in ("gg_20", "gg_60"):
            days = int(name[3:])
            return self._ret(days) - (self.bench / self.bench.shift(days) - 1) * 100
        if name in RANKED:
            return pd.Series(np.nan, index=df.index)  # filled across stocks (rank_last / rank_panel)
        if name == "zirve_uzaklik":
            return (close / close.rolling(252, min_periods=252).max() - 1) * 100
        if name == "dip_uzaklik":
            return (close / close.rolling(252, min_periods=252).min() - 1) * 100
        if name == "yuksek_20g":
            return df["high"].shift(1).rolling(20).max()
        if name == "dusuk_20g":
            return df["low"].shift(1).rolling(20).min()
        if name == "bosluk":
            return (df["open"] / close.shift(1) - 1) * 100
        if name == "kapanis":
            return close
        if name == "acilis":
            return df["open"]
        raise KeyError(column)


def table(df: pd.DataFrame, bench_close: pd.Series, columns, recent: int | None = None) -> pd.DataFrame:
    """The requested columns (field keys) for every candle of `df`; `recent`: the costly level fields
    only for the last `recent` candles (the live list; the history card needs them all)."""

    t = _Table(df, bench_close, recent)
    wanted = list(dict.fromkeys(columns))
    wanted += [RANKED[c] for c in list(wanted) if c in RANKED and RANKED[c] not in wanted]
    return pd.DataFrame({c: t.get(c) for c in wanted}, index=df.index)


def rank_last(tables: dict[str, pd.DataFrame], ranked) -> None:
    """Fill each ranked column's LAST row: the percentile of its base among the given tables."""

    for column in ranked:
        base = pd.Series({s: t[RANKED[column]].iloc[-1] for s, t in tables.items()}, dtype=float)
        ranks = base.rank(pct=True) * 100
        for s, t in tables.items():
            t.loc[t.index[-1], column] = ranks.get(s)


def rank_panel(tables: dict[str, pd.DataFrame], ranked, eligible: pd.DataFrame | None = None) -> None:
    """Fill each ranked column on EVERY day: the percentile among that day's eligible stocks."""

    for column in ranked:
        panel = pd.DataFrame({s: t[RANKED[column]] for s, t in tables.items()})
        if eligible is not None:
            ok = eligible.reindex(index=panel.index, columns=panel.columns).ffill().fillna(False).astype(bool)
            panel = panel.where(ok)
        ranks = panel.rank(axis=1, pct=True) * 100
        for s, t in tables.items():
            t[column] = ranks[s].reindex(t.index)


__all__ = ["ALIASES", "CROSS_SECTIONAL", "FIELDS", "Field", "key", "split", "table"]
