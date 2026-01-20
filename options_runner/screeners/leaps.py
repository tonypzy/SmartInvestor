import pandas as pd
from options_runner.screeners.base_screener import BaseScreener
from options_runner.utils.option_math import calculate_greeks

class LeapsScreener(BaseScreener):
    def run(self, symbol, min_days=250, max_days=530):
        self.log_header(f"{symbol} LEAPS Screener (Deep Value)")
        
        try:
            vol_data = self.market.get_volatility_data(symbol)
            current_price = vol_data['current_price']
            self.log(f"Price: ${current_price:.2f}")
        except Exception as e:
            self.log(f"Error: {e}")
            return

        target_dates = self.market.get_option_dates(symbol, min_days, max_days)
        if not target_dates:
            self.log("No dates.")
            return

        results = []
        
        for date_str, days in target_dates:
            try:
                calls, _ = self.market.get_chain(symbol, date_str)
                if calls.empty: continue
                
                # Filter Deep ITM
                # Typically LEAPS look for 0.65 to 0.95 Delta
                # But to filter delta we need to calculate it first
                
                calls['mid'] = (calls['bid']+calls['ask'])/2
                # Use lastPrice if mid is stale/zero?
                # Original script used lastPrice if mid is 0. 
                # Our greeks calc needs a price.
                
                # Filter valid trades
                calls = calls[(calls['bid']>0) & (calls['ask']>0)].copy()
                calls['time_to_expiry'] = days/365.0
                
                calls = calculate_greeks(calls, current_price, 'c')
                
                # Filter Delta
                calls = calls[(calls['delta'] >= 0.65) & (calls['delta'] <= 0.95)]
                
                calls['break_even'] = calls['strike'] + calls['mid']
                calls['premium_pct'] = (calls['break_even'] - current_price) / current_price * 100
                calls['leverage'] = (calls['delta'] * current_price) / calls['mid']
                calls['IV%'] = calls['iv'] * 100
                
                for _, row in calls.iterrows():
                    results.append({
                        'Expiry': date_str,
                        'Strike': row['strike'],
                        'Price': row['mid'],
                        'Delta': row['delta'],
                        'IV%': row['IV%'],
                        'Prem%': row['premium_pct'],
                        'Lev': row['leverage']
                    })

            except Exception:
                continue

        if not results:
            self.log("No valid strategies.")
            return

        df = pd.DataFrame(results)
        # Sort by Delta (highest first) then IV (lowest first) ??
        # Original: Sort by Delta Desc, IV Asc.
        # But we want to find "Sweet Spot" (Delta ~ 0.80, low IV)
        
        df = df.sort_values(by=['Delta', 'IV%'], ascending=[False, True])
        
        cols = ['Expiry', 'Strike', 'Price', 'Delta', 'IV%', 'Prem%', 'Lev']
        print(df[cols].to_string(index=False))
        
        self.log_separator()
        
        # Sweet spot
        df['delta_dist'] = (df['Delta'] - 0.80).abs()
        sweet = df.sort_values(by=['delta_dist', 'IV%']).iloc[0]
        self.log(f"★ Sweet Spot: {sweet['Expiry']} ${sweet['Strike']} (Delta {sweet['Delta']:.2f}, IV {sweet['IV%']:.1f}%)")
