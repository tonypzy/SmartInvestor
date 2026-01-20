import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
from options_runner.utils.option_math import calculate_greeks

class MarketDataService:
    def __init__(self):
        self._tickers = {} # Cache tickers

    def get_ticker(self, symbol):
        if symbol not in self._tickers:
            self._tickers[symbol] = yf.Ticker(symbol)
        return self._tickers[symbol]

    def get_current_price(self, symbol):
        tk = self.get_ticker(symbol)
        hist = tk.history(period="1d")
        if hist.empty:
            raise ValueError(f"Could not fetch history for {symbol}")
        return hist['Close'].iloc[-1]

    def get_volatility_data(self, symbol):
        """
        Returns a dict with current_price, hv_30, iv_rank, etc.
        """
        tk = self.get_ticker(symbol)
        hist = tk.history(period="1y")
        if hist.empty:
            raise ValueError(f"No history for {symbol}")
            
        current_price = hist['Close'].iloc[-1]
        
        # Calculate HV
        log_return = np.log(hist['Close'] / hist['Close'].shift(1))
        vol_hist = log_return.rolling(window=30).std() * np.sqrt(252)
        curr_hv = vol_hist.iloc[-1]
        
        # Calculate IV Rank (Estimated from HV range for now as per original script logic)
        # Note: Original script used simple HV range to estimate "rank". 
        # Ideally IV Rank comes from IV data, but we stick to original logic unless asked.
        min_hv = vol_hist.min()
        max_hv = vol_hist.max()
        iv_rank_est = (curr_hv - min_hv) / (max_hv - min_hv) * 100 if (max_hv - min_hv) != 0 else 50
        
        return {
            "current_price": current_price,
            "hv_30": curr_hv,
            "iv_rank": iv_rank_est,
            "min_hv": min_hv,
            "max_hv": max_hv
        }

    def get_earnings_date(self, symbol):
        tk = self.get_ticker(symbol)
        try:
            cal = tk.calendar
            if isinstance(cal, pd.DataFrame) and not cal.empty:
                return cal.iloc[0, 0]
            elif isinstance(cal, dict) and 'Earnings Date' in cal:
                return cal['Earnings Date'][0]
        except:
            pass
        return None

    def get_option_dates(self, symbol, min_days=0, max_days=365):
        tk = self.get_ticker(symbol)
        all_dates = tk.options
        target_dates = []
        now = datetime.now()
        
        for d_str in all_dates:
            d_date = datetime.strptime(d_str, "%Y-%m-%d")
            days = (d_date - now).days
            if min_days <= days <= max_days:
                target_dates.append((d_str, days))
        return target_dates

    def get_chain(self, symbol, date_str):
        tk = self.get_ticker(symbol)
        opts = tk.option_chain(date_str)
        calls = opts.calls.copy()
        puts = opts.puts.copy()
        return calls, puts
