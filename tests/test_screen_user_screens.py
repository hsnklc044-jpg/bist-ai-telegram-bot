"""
The user's own TradingView screens (screenshots, 28.10.2026) are the yardstick for /tara: every
price-based condition in them must be writable, and an empty answer must say which condition
emptied it. What the system has no data for (market value, FSO, market segment) and what it will
not carry (a "Güçlü al" rating: buy/sell wording, CHARTER §9) is listed, not imitated.
"""

import unittest

import numpy as np
import pandas as pd

from core.screen import engine, fields
from core.screen.language import MAX_CONDITIONS, MAX_LENGTH, parse
from tests.test_screen_engine import walk

# TradingView filter -> /tara (docs/HANDBOOK.md §8 "TradingView karşılıkları")
USER_SCREENS = {
    "guclu_trend": ("GÜÇLÜ TREND FİLTRESİ (GÜVENLİ PORTFÖY)",
                    "kapanis>ema50 ema50>ema200 rsi 63..68 adx 25..40 ort_hacim(30)>20 getiri(21) 7..22 "
                    "getiri(63) 15..55 ema20>ema50 beta 0,9..1,3",
                    ["Pys değ > 20 milyar TL (piyasa değeri verisi yok)"]),
    "trend_sahibi": ("11. Trend Sahibi Şişmemiş Hisseler",
                     "kapanis>ema50 kapanis>ema200 rsi<65 hacim_degisim>10 hacim_oran(10)>2",
                     ["HO derecelendirmesi 'Güçlü al' (al/sat etiketi, eklenmez)"]),
    "duseni_kiran": ("10. Düşeni Kıran Hisse ve Harekete Hazır EMA",
                     "kapanis<yuksek_20g rsi 50..70 hacim_oran(10)>1,5 ema(5)>ema(10) ema(10)>ema20 ema20>ema(40) "
                     "ema50>ema(100) ema(100)>ema200 vwma(20)<kapanis getiri_5g<15 getiri(21)<20 cci(20)>-100 "
                     "kapanis>acilis hacim_oran(10)>1",
                     ["Borsa piyasası (pazar bilgisi yok)"]),
    "bebek_hisse": ("8. Bebek hisse taraması",
                    "hacim_oran(10)>1 mom(10)>0",
                    ["Pys değ 1–2 milyar TL (piyasa değeri verisi yok)", "FSO < 1 (temel veri yok)"]),
    "trend_baslayan": ("Trend başlayan + formasyon tamamlamak üzere hisseler",
                       "kapanis>ema50 ema50>ema200 rsi 55..70 hacim_oran(10)>1,8 adx>20 getiri(21) 5..25 "
                       "kapanis>ema20 getiri_5g<10 kapanis>ema200",
                       []),
    "goldencross": ("GOLDENCROSS",
                    "kesti_yukari(ema50,ema200) kapanis>ema200 rsi>50 hacim_oran(10)>1,5 macd>0 adx>20",
                    ["kesişim yalnız o günkü mumda aranır; son 5 seans için son(5, kesti_yukari(ema50,ema200))"]),
    "tek_tus_trend": ("BIST TEK TUŞ TREND",
                      "kapanis>ema50 ema50>ema200 rsi 60..70 adx>20 ort_hacim(30)>10 getiri(21)<30 beta 0,8..1,5 "
                      "kapanis>ema20 getiri(63)<60",
                      ["Pys değ > 10 milyar TL (piyasa değeri verisi yok)"]),
    "erken_trend": ("ERKEN TREND",
                    "kapanis>ema20 kapanis<ema50 rsi 45..55 adx 15..22 hacim_oran(10)>1 ort_hacim(10)>10",
                    []),
}


def market(n=30):
    frames = {f"S{i:02d}.IS": walk(320, 0.001, 300 + i, volume=3e7) for i in range(n)}
    return frames, walk(320, 0.0, 9)


class UserScreensTest(unittest.TestCase):
    def test_every_screen_is_writable_and_runs(self):
        frames, bench = market()
        for name, (title, text, missing) in USER_SCREENS.items():
            with self.subTest(name):
                query = parse(text)
                self.assertLessEqual(len(text), MAX_LENGTH)
                self.assertLessEqual(len(query.leaves()), MAX_CONDITIONS)
                result = engine.run(query, frames, bench)
                self.assertEqual(result.scanned, len(frames))

    def test_the_tightest_one_needs_fourteen_conditions(self):
        self.assertEqual(len(parse(USER_SCREENS["duseni_kiran"][1]).leaves()), 14)
        self.assertGreaterEqual(MAX_CONDITIONS, 14)

    def test_new_fields(self):
        df, bench = walk(320, 0.0005, 11, volume=3e7), walk(320, 0.0, 12)
        t = fields.table(df, bench["close"], ["cci", "vwma", "mom", "beta", "getiri(21)", "ort_hacim(30)",
                                              "hacim_degisim", "hacim_oran(10)"])
        c, v, last = df["close"], df["volume"], t.iloc[-1]
        self.assertAlmostEqual(last["vwma"], (c * v).iloc[-20:].sum() / v.iloc[-20:].sum())
        self.assertAlmostEqual(last["mom"], c.iloc[-1] - c.iloc[-11])
        self.assertAlmostEqual(last["getiri(21)"], (c.iloc[-1] / c.iloc[-22] - 1) * 100)
        self.assertAlmostEqual(last["ort_hacim(30)"], v.iloc[-30:].mean() / 1e6)
        self.assertAlmostEqual(last["hacim_degisim"], (v.iloc[-1] / v.iloc[-2] - 1) * 100)
        r, m = c.pct_change().iloc[-252:], bench["close"].pct_change().iloc[-252:]
        self.assertAlmostEqual(last["beta"], r.cov(m) / m.var(), places=6)
        from core.strategy.score import volume_ratio_series

        pd.testing.assert_series_equal(t["hacim_oran(10)"], volume_ratio_series(v, 10), check_names=False)
        self.assertFalse(np.isnan(last["cci"]))


class FunnelTest(unittest.TestCase):
    def test_an_empty_answer_names_the_condition_that_emptied_it(self):
        from core.screen import command

        frames, bench = market()
        result = engine.run(parse("rsi>0 ve kapanis>0 ve rsi>99 ele=hayir"), frames, bench)
        self.assertEqual(result.matches, [])
        alone = {text: n for text, n, _ in result.funnel}
        self.assertEqual(alone["rsi>0"], 30)
        self.assertEqual(alone["rsi>99"], 0)
        self.assertEqual([cum for _, _, cum in result.funnel], [30, 30, 0])
        text = command.format_result(result, None)
        self.assertIn("Koşul hunisi", text)
        self.assertIn("rsi>99: tek başına 0", text)
        self.assertIn("en çok eleyen: rsi>99", text)

    def test_no_funnel_when_something_matched(self):
        from core.screen import command

        frames, bench = market()
        result = engine.run(parse("rsi>0"), frames, bench)
        self.assertNotIn("Koşul hunisi", command.format_result(result, None))


if __name__ == "__main__":
    unittest.main()
