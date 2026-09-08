import unittest
import pandas as pd
import numpy as np
from mystock.universe import get_universe_items, KOREA_LEADERS, US_LEADERS
from mystock.scanner import evaluate_stock_leader, get_default_benchmark_ticker


class TestScanner(unittest.TestCase):
    def setUp(self):
        dates = pd.date_range(start="2026-01-01", periods=30, freq="B")
        
        # Benchmark dataframe (e.g. KOSPI falls -2.0% on the last day)
        bench_close = [2000.0] * 29 + [1960.0]  # -2.0% on last day
        self.df_bench = pd.DataFrame({
            "Open": bench_close,
            "High": bench_close,
            "Low": bench_close,
            "Close": bench_close,
            "Volume": [100000] * 30,
        }, index=dates)

        # Outperforming Stock dataframe:
        # Stock rises +3.0% on last day with huge volume and bullish candle (Close > Open)
        stock_close = [100.0] * 28 + [100.0, 103.0]
        stock_open = [100.0] * 28 + [100.0, 100.5]
        stock_vol = [10000] * 29 + [30000]  # 3x volume surge

        self.df_stock = pd.DataFrame({
            "Open": stock_open,
            "High": [p + 1.0 for p in stock_close],
            "Low": [p - 1.0 for p in stock_close],
            "Close": stock_close,
            "Volume": stock_vol,
        }, index=dates)

    def test_universe_items(self):
        kr = get_universe_items("korea")
        self.assertGreater(len(kr), 10)
        self.assertEqual(kr[0]["ticker"], "005930")

        us = get_universe_items("us")
        self.assertGreater(len(us), 10)
        self.assertEqual(us[0]["ticker"], "NVDA")

    def test_default_benchmark_ticker(self):
        self.assertEqual(get_default_benchmark_ticker("005930"), "^KS11")
        self.assertEqual(get_default_benchmark_ticker("NVDA"), "SPY")

    def test_evaluate_stock_leader_counter_trend(self):
        res = evaluate_stock_leader(
            df_stock=self.df_stock,
            df_bench=self.df_bench,
            anchor_date="2026-01-02",
        )
        self.assertIsNotNone(res)
        # Benchmark change is -2.0%
        self.assertAlmostEqual(res["bench_change_pct"], -2.0, places=1)
        # Stock change is +3.0%
        self.assertAlmostEqual(res["stock_change_pct"], 3.0, places=1)
        # Relative Strength spread is 3.0 - (-2.0) = +5.0%p
        self.assertGreater(res["rs_spread"], 4.5)
        # Counter-trend flag should be True
        self.assertTrue(res["is_counter_trend"])
        self.assertTrue(res["is_yangbong"])
        # High composite score expected (S or A grade)
        self.assertGreaterEqual(res["score"], 75.0)
        # Check stop loss is -10% of close (103 * 0.9 = 92.7)
        self.assertAlmostEqual(res["stop_loss_price"], 92.7, delta=1.0)


if __name__ == "__main__":
    unittest.main()
