import unittest
import pandas as pd
import numpy as np
import os
from mystock.indicators import calculate_typical_price, calculate_avwap, calculate_obv, calculate_indicators
from mystock.divergence import detect_obv_divergence
from mystock.visualizer import create_stock_chart


class TestMyStock(unittest.TestCase):
    def setUp(self):
        # Create synthetic OHLCV DataFrame
        dates = pd.date_range(start="2026-01-01", periods=60, freq="B")
        np.random.seed(42)
        
        # Synthetic price starting at 100
        close = 100 + np.cumsum(np.random.randn(60) * 2)
        high = close + np.random.rand(60) * 2
        low = close - np.random.rand(60) * 2
        open_p = (high + low) / 2
        vol = np.random.randint(1000, 5000, size=60)

        self.df = pd.DataFrame({
            "Open": open_p,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": vol,
        }, index=dates)

    def test_typical_price(self):
        tp = calculate_typical_price(self.df)
        self.assertEqual(len(tp), len(self.df))
        expected_first = (self.df["High"].iloc[0] + self.df["Low"].iloc[0] + self.df["Close"].iloc[0]) / 3
        self.assertAlmostEqual(tp.iloc[0], expected_first)

    def test_avwap(self):
        anchor = "2026-01-15"
        avwap = calculate_avwap(self.df, anchor_date=anchor)
        self.assertEqual(len(avwap), len(self.df))
        # Values before anchor should be NaN
        before_anchor = self.df.index < pd.to_datetime(anchor)
        self.assertTrue(avwap[before_anchor].isna().all())
        # Values after anchor should be valid floats
        after_anchor = self.df.index >= pd.to_datetime(anchor)
        self.assertTrue(avwap[after_anchor].notna().all())

    def test_obv(self):
        obv_df = calculate_obv(self.df)
        self.assertIn("OBV", obv_df.columns)
        self.assertIn("OBV_EMA", obv_df.columns)
        self.assertEqual(len(obv_df), len(self.df))

    def test_indicators_suite(self):
        df_ind = calculate_indicators(self.df, anchor_date="2026-01-10")
        for col in ["Typical_Price", "AVWAP", "OBV", "OBV_EMA", "SMA20", "SMA60"]:
            self.assertIn(col, df_ind.columns)

    def test_divergence_detection(self):
        # Create clear bullish divergence:
        # Price: Low1 at t=10 is 50, Low2 at t=20 is 45 (Lower Low)
        # OBV: OBV at t=10 is 1000, OBV at t=20 is 2000 (Higher Low)
        dates = pd.date_range(start="2026-01-01", periods=30, freq="B")
        low = np.array([60.0] * 30)
        high = np.array([70.0] * 30)
        close = np.array([65.0] * 30)
        vol = np.array([100.0] * 30)
        
        # Trough 1 at index 5
        low[5] = 50.0
        # Trough 2 at index 15
        low[15] = 45.0 # Lower low
        
        test_df = pd.DataFrame({
            "Open": close, "High": high, "Low": low, "Close": close, "Volume": vol
        }, index=dates)
        
        test_df = calculate_indicators(test_df)
        # Manually force OBV at index 15 to be higher than index 5
        test_df.loc[test_df.index[5], "OBV"] = 1000.0
        test_df.loc[test_df.index[15], "OBV"] = 2000.0
        
        signals, low_idx, high_idx = detect_obv_divergence(test_df, order=2)
        self.assertIsInstance(signals, list)

    def test_chart_creation(self):
        df_ind = calculate_indicators(self.df, anchor_date="2026-01-10")
        signals, _, _ = detect_obv_divergence(df_ind, order=3)
        html_file = "test_chart.html"
        path = create_stock_chart(
            df_ind,
            ticker="TEST",
            stock_name="Test Stock",
            signals=signals,
            anchor_date="2026-01-10",
            output_html_path=html_file,
            auto_open=False,
        )
        self.assertTrue(os.path.exists(path))
    def test_watchlist(self):
        from mystock.watchlist import (
            load_watchlist, add_ticker_to_category, remove_ticker_from_category,
            get_category_tickers, get_all_tickers
        )
        test_file = "test_watchlist.json"
        try:
            wl = load_watchlist(test_file)
            self.assertIn("보유종목", wl)
            self.assertIn("초관심종목", wl)
            self.assertIn("관심종목", wl)

            # Test adding a ticker
            add_ticker_to_category("보유종목", "005930", name="삼성전자", anchor="2026-01-02", memo="테스트", file_path=test_file)
            tickers = get_category_tickers("보유종목", file_path=test_file)
            self.assertIn("005930", tickers)

            # Test all tickers list
            all_t = get_all_tickers(file_path=test_file)
            self.assertTrue(any(it["ticker"] == "005930" for it in all_t))

            # Test copy ticker
            from mystock.watchlist import move_ticker_between_categories, copy_ticker_between_categories
            add_ticker_to_category("관심종목", "NVDA", name="엔비디아", file_path=test_file)
            copy_ticker_between_categories("관심종목", "초관심종목", "NVDA", file_path=test_file)
            self.assertIn("NVDA", get_category_tickers("관심종목", file_path=test_file))
            self.assertIn("NVDA", get_category_tickers("초관심종목", file_path=test_file))

            # Test move ticker
            move_ticker_between_categories("관심종목", "보유종목", "NVDA", file_path=test_file)
            self.assertNotIn("NVDA", get_category_tickers("관심종목", file_path=test_file))
            self.assertIn("NVDA", get_category_tickers("보유종목", file_path=test_file))

            # Test removing ticker
            remove_ticker_from_category("보유종목", "005930", file_path=test_file)
            tickers_after = get_category_tickers("보유종목", file_path=test_file)
            self.assertNotIn("005930", tickers_after)
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)


class TestStockCache(unittest.TestCase):
    """Tests for the incremental Parquet cache module."""

    def setUp(self):
        import tempfile
        import mystock.stock_cache as sc
        self.sc = sc
        # Redirect cache to a temp directory
        self._orig_cache_dir = sc.CACHE_DIR
        self._tmpdir = tempfile.mkdtemp(prefix="mystock_cache_test_")
        sc.CACHE_DIR = __import__("pathlib").Path(self._tmpdir)

        # Synthetic OHLCV data
        dates = pd.date_range(start="2026-06-01", periods=30, freq="B")
        np.random.seed(99)
        close = 100 + np.cumsum(np.random.randn(30) * 2)
        self.sample_df = pd.DataFrame({
            "Open": close + 0.5,
            "High": close + 1.5,
            "Low": close - 1.0,
            "Close": close,
            "Volume": np.random.randint(1000, 5000, size=30),
        }, index=dates)

    def tearDown(self):
        import shutil
        self.sc.CACHE_DIR = self._orig_cache_dir
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_save_and_load(self):
        """save_cache then get_cached_data should return identical data."""
        self.sc.save_cache("TEST001", self.sample_df)
        loaded = self.sc.get_cached_data("TEST001")
        self.assertIsNotNone(loaded)
        self.assertEqual(len(loaded), len(self.sample_df))
        pd.testing.assert_frame_equal(loaded, self.sample_df, check_names=False, check_freq=False)

    def test_load_nonexistent_returns_none(self):
        self.assertIsNone(self.sc.get_cached_data("NONEXIST"))

    def test_invalidate_single(self):
        self.sc.save_cache("A", self.sample_df)
        self.sc.save_cache("B", self.sample_df)
        deleted = self.sc.invalidate_cache("A")
        self.assertEqual(deleted, 1)
        self.assertIsNone(self.sc.get_cached_data("A"))
        self.assertIsNotNone(self.sc.get_cached_data("B"))

    def test_invalidate_all(self):
        self.sc.save_cache("X", self.sample_df)
        self.sc.save_cache("Y", self.sample_df)
        deleted = self.sc.invalidate_cache()
        self.assertEqual(deleted, 2)
        self.assertIsNone(self.sc.get_cached_data("X"))
        self.assertIsNone(self.sc.get_cached_data("Y"))

    def test_cache_info(self):
        self.sc.save_cache("INFO_TEST", self.sample_df)
        info = self.sc.get_cache_info()
        self.assertEqual(info["ticker_count"], 1)
        self.assertGreater(info["total_size_kb"], 0)
        self.assertEqual(info["tickers"][0]["ticker"], "INFO_TEST")
        self.assertEqual(info["tickers"][0]["rows"], 30)

    def test_get_or_fetch_full(self):
        """get_or_fetch with no cache should call fetch_fn and save cache."""
        call_count = {"n": 0}

        def mock_fetch(ticker, start_date, end_date, days):
            call_count["n"] += 1
            return self.sample_df.copy()

        result = self.sc.get_or_fetch("MOCK", days=365, fetch_fn=mock_fetch)
        self.assertEqual(call_count["n"], 1)
        self.assertFalse(result.empty)
        # Cache should now exist
        cached = self.sc.get_cached_data("MOCK")
        self.assertIsNotNone(cached)

    def test_get_or_fetch_uses_cache(self):
        """Second call to get_or_fetch should use cache (fresh data)."""
        # Pre-populate cache with data that includes today
        import datetime
        dates = pd.bdate_range(
            end=datetime.datetime.now().date(), periods=30
        )
        fresh_df = self.sample_df.copy()
        fresh_df.index = dates
        self.sc.save_cache("FRESH", fresh_df)

        call_count = {"n": 0}

        def mock_fetch(ticker, start_date, end_date, days):
            call_count["n"] += 1
            return fresh_df.copy()

        result = self.sc.get_or_fetch("FRESH", days=30, fetch_fn=mock_fetch)
        # Should NOT have called the API since cache is fresh
        self.assertEqual(call_count["n"], 0)
        self.assertFalse(result.empty)

    def test_deduplication_on_merge(self):
        """Merging overlapping data should not produce duplicate rows."""
        df1 = self.sample_df.iloc[:20].copy()
        df2 = self.sample_df.iloc[15:].copy()  # 5 rows overlap
        self.sc.save_cache("DUP", df1)
        merged = pd.concat([df1, df2])
        merged = merged[~merged.index.duplicated(keep="last")].sort_index()
        self.sc.save_cache("DUP", merged)
        loaded = self.sc.get_cached_data("DUP")
        self.assertEqual(len(loaded), len(self.sample_df))


if __name__ == "__main__":
    unittest.main()
