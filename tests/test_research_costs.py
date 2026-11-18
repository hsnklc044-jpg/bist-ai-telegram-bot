"""QB-ARS-1 C-1..C-3: cost and capacity functions (Faz C preparation, 18.11.2026).

No parameter has a default in the code: every value (tick table, rates, slippage coefficients, capacity
share) is the caller's and comes from a pre-registration. The numbers in these tests are made-up test
inputs, not proposals; the proposals are in docs/MALIYET_ONERI.md for the owner to decide.
Limit locks reuse core.market.limits (K-75); nothing is duplicated here.
"""

import inspect
import unittest

from core.research import costs

TABLE = [(0.0, 0.01), (20.0, 0.02), (50.0, 0.05), (100.0, 0.10)]  # made-up test table


class TickTest(unittest.TestCase):
    def test_rounds_to_the_band_tick(self):
        self.assertAlmostEqual(costs.round_to_tick(12.346, TABLE), 12.35)
        self.assertAlmostEqual(costs.round_to_tick(25.03, TABLE), 25.04)
        self.assertAlmostEqual(costs.round_to_tick(77.77, TABLE), 77.75)
        self.assertAlmostEqual(costs.round_to_tick(123.44, TABLE), 123.40)

    def test_buy_rounds_up_and_sell_rounds_down(self):
        self.assertAlmostEqual(costs.round_to_tick(12.341, TABLE, side="buy"), 12.35)
        self.assertAlmostEqual(costs.round_to_tick(12.349, TABLE, side="sell"), 12.34)

    def test_a_bad_table_is_refused(self):
        for bad in ([], [(5.0, 0.01)], [(0.0, 0.01), (0.0, 0.02)], [(0.0, 0.0)], [(0.0, 0.02), (10.0, 0.01), (5.0, 0.05)]):
            with self.assertRaises(ValueError, msg=bad):
                costs.round_to_tick(10.0, bad)
        with self.assertRaises(ValueError):
            costs.round_to_tick(-1.0, TABLE)


class CostTest(unittest.TestCase):
    def test_one_way_cost_adds_bsmv_on_the_commission(self):
        c = costs.one_way_cost(commission=0.001, bsmv_on_commission=0.05, exchange_fee=0.00003,
                               half_spread=0.0005, slippage=0.0002)
        self.assertAlmostEqual(c, 0.001 * 1.05 + 0.00003 + 0.0005 + 0.0002)

    def test_slippage_grows_with_the_order_share_of_daily_volume(self):
        small = costs.slippage(order_tl=10_000, adv_tl=10_000_000, base=0.0002, impact=0.1)
        large = costs.slippage(order_tl=1_000_000, adv_tl=10_000_000, base=0.0002, impact=0.1)
        self.assertAlmostEqual(small, 0.0002 + 0.1 * (0.001 ** 0.5))
        self.assertGreater(large, small)

    def test_capacity(self):
        self.assertTrue(costs.within_capacity(order_tl=50_000, adv_tl=10_000_000, max_share=0.01))
        self.assertFalse(costs.within_capacity(order_tl=150_000, adv_tl=10_000_000, max_share=0.01))
        self.assertFalse(costs.within_capacity(order_tl=1, adv_tl=0, max_share=0.01))

    def test_negative_or_missing_inputs_are_refused(self):
        with self.assertRaises(ValueError):
            costs.one_way_cost(commission=-0.1, bsmv_on_commission=0.05, exchange_fee=0, half_spread=0, slippage=0)
        with self.assertRaises(ValueError):
            costs.slippage(order_tl=1, adv_tl=-5, base=0, impact=0)

    def test_no_parameter_has_a_default(self):
        for fn in (costs.one_way_cost, costs.slippage, costs.within_capacity):
            for p in inspect.signature(fn).parameters.values():
                self.assertIs(p.default, inspect.Parameter.empty, f"{fn.__name__}.{p.name}")
        params = inspect.signature(costs.round_to_tick).parameters
        self.assertIs(params["table"].default, inspect.Parameter.empty)


if __name__ == "__main__":
    unittest.main()
