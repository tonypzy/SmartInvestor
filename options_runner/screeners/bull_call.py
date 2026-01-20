import pandas as pd
import numpy as np
from options_runner.screeners.base_screener import BaseScreener
from options_runner.utils.option_math import calculate_greeks

class BullCallScreener(BaseScreener):
    def run(self, symbol, spread_widths=[2.5, 5, 10], min_days=1, max_days=15, min_volume=30):
        if isinstance(spread_widths, (int, float)):
            spread_widths = [spread_widths]
            
        self.log_header(f"{symbol} Bull Call Spread")
        
        try:
            vol_data = self.market.get_volatility_data(symbol)
        except Exception as e:
            self.log(f"Error: {e}")
            return

        current_price = vol_data['current_price']
        curr_hv = vol_data['hv_30']
        
        self.log(f"Price: ${current_price:.2f} | 30D HV: {curr_hv:.1%}")

        target_dates = self.market.get_option_dates(symbol, min_days, max_days)
        if not target_dates:
            self.log("No dates.")
            return

        results = []
        
        for date_str, days in target_dates:
            try:
                calls, _ = self.market.get_chain(symbol, date_str)
                if calls.empty: continue
                
                # Check liquidity
                # Note: original script filtered by openInterest < min_open_interest, but set default to 0
                # We retain min_volume check if provided
                
                # Fill na OI
                calls['openInterest'] = calls['openInterest'].fillna(0)
                
                # Price estimation (mid)
                calls['mid'] = (calls['bid'] + calls['ask']) / 2
                calls['time_to_expiry'] = days / 365.0
                
                # Greeks
                calls = calculate_greeks(calls, current_price, 'c')
                
                # VRP Logic
                atm_idx = (calls['strike'] - current_price).abs().idxmin()
                atm_iv = calls.loc[atm_idx, 'iv']
                vrp_ratio = atm_iv / curr_hv if curr_hv > 0 else 0
                
                # Iterate Long Legs
                for _, long_row in calls.iterrows():
                    if long_row['volume'] < min_volume: continue
                    if long_row['mid'] <= 0.01: continue
                    
                    # Target 0.50 - 0.85 delta
                    if not (0.50 <= long_row['delta'] <= 0.85): continue
                    
                    for width in spread_widths:
                        short_strike = long_row['strike'] + width
                        short_candidates = calls[calls['strike'] == short_strike]
                        if short_candidates.empty: continue
                        short_row = short_candidates.iloc[0]
                        
                        debit = long_row['ask'] - short_row['bid']
                        if debit >= width or debit <= 0: continue
                        
                        # EV
                        pop_est = (long_row['delta'] + (1 - short_row['delta'])) / 2 * 100
                        max_profit = width - debit
                        ev = (pop_est/100 * max_profit) - ((1 - pop_est/100) * debit)
                        
                        if ev <= 0: continue
                        
                        # IV Skew
                        iv_skew = short_row['iv'] - long_row['iv']
                        if iv_skew < -0.02: continue
                        
                        results.append({
                            'Expiry': date_str,
                            'Width': width,
                            'Long': long_row['strike'],
                            'Short': short_strike,
                            'Debit': debit,
                            'RoR%': (max_profit / debit) * 100,
                            'PoP%': pop_est,
                            'EV': ev,
                            'IV_Skew': iv_skew * 100
                        })
            
            except Exception:
                continue

        if not results:
            self.log("No valid strategies.")
            return

        df = pd.DataFrame(results)
        df_sorted = df.sort_values(by='EV', ascending=False)
        
        self.log_separator()
        cols = ['Expiry', 'Width', 'Long', 'Short', 'Debit', 'RoR%', 'PoP%', 'EV', 'IV_Skew']
        print(df_sorted[cols].head(20).to_string(index=False))
        
        self.log_separator()
        self.log("🤖 Analysis")
        agg = df_sorted[(df_sorted['RoR%'] > 120)].head(1)
        if not agg.empty:
            r = agg.iloc[0]
            self.log(f"🚀 Aggressive Pick: {r['Expiry']} ${r['Long']}/{r['Short']} (RoR: {r['RoR%']:.0f}%)")
