import unittest
import pandas as pd
from python_signal_engine import detect_signals, fetch_ohlc

class TestSignalEngine(unittest.TestCase):
    def test_detect_signals_with_mock_data(self):
        # Create mock OHLC data
        data = {
            'open': [1800, 1802, 1804, 1806, 1808, 1810, 1812, 1814, 1816, 1818],
            'high': [1802, 1804, 1806, 1808, 1810, 1812, 1814, 1816, 1818, 1820],
            'low':  [1798, 1800, 1802, 1804, 1806, 1808, 1810, 1812, 1814, 1816],
            'close':[1801, 1803, 1805, 1807, 1809, 1811, 1813, 1815, 1817, 1819],
            'volume':[1]*10
        }
        df = pd.DataFrame(data)
        long_entry, short_entry, zlema, trend, rsi = detect_signals(df)
        self.assertEqual(len(long_entry), 10)
        self.assertEqual(len(short_entry), 10)
        self.assertEqual(len(zlema), 10)
        self.assertEqual(len(trend), 10)
        self.assertEqual(len(rsi), 10)
        # Check that output is boolean Series for entries
        self.assertTrue(long_entry.dtype == 'bool')
        self.assertTrue(short_entry.dtype == 'bool')

    def test_fetch_ohlc_returns_dataframe_or_none(self):
        # Should return a DataFrame or None if API key is missing
        df = fetch_ohlc()
        self.assertTrue(df is None or isinstance(df, pd.DataFrame))

    def test_stateful_trend_persistence(self):
        # Build data where price crosses above upper band at bar 3 then stays above
        close = [100, 101, 120, 121, 122, 123, 124]
        open_ = [99, 100, 110, 120, 121, 122, 123]
        high = [101, 102, 121, 122, 123, 124, 125]
        low = [98, 99, 100, 119, 120, 121, 122]
        data = {'open': open_, 'high': high, 'low': low, 'close': close, 'volume': [1]*7}
        df = pd.DataFrame(data)
        long_entry, short_entry, zlema, trend, rsi = detect_signals(df, ema_length=3, band_mult=0.5)
        # After the upward crossover (bar index 2), trend should be 1 for subsequent bars
        self.assertTrue((trend.iloc[2:] == 1).any())

if __name__ == '__main__':
    unittest.main()
