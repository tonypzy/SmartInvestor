import pandas as pd
from options_runner.screeners.base_screener import BaseScreener
from options_runner.utils.option_math import calculate_greeks

class DeepITMScreener(BaseScreener):
    def run(self, symbol, min_long_delta=0.75, min_days=10, max_days=20, target_otm_pct=1.05):
        self.log_header(f"{symbol} Deep ITM Bull Call Spread (Stock Substitute)")
        
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
                
                calls = calls[(calls['bid']>0) & (calls['ask']>0)].copy()
                calls['mid'] = (calls['bid']+calls['ask'])/2
                calls['time_to_expiry'] = days/365.0
                
                calls = calculate_greeks(calls, current_price, 'c')
                
                # Long Legs: Deep ITM
                limit_delta = min(0.99, min_long_delta) # Cap at 0.99
                long_candidates = calls[calls['delta'] >= limit_delta]
                
                # Short Legs: OTM >= 5% above price
                min_short_strike = current_price * target_otm_pct
                short_candidates = calls[calls['strike'] >= min_short_strike]
                
                for _, long_row in long_candidates.iterrows():
                    for _, short_row in short_candidates.iterrows():
                        if short_row['strike'] <= long_row['strike']: continue
                        
                        debit = long_row['mid'] - short_row['mid']
                        break_even = long_row['strike'] + debit
                        
                        safety_pct = (break_even - current_price) / current_price * 100
                        
                        # Filter: We want safety < 1.5% (meaning current price is near or above BE)
                        if safety_pct > 1.5: continue
                        
                        width = short_row['strike'] - long_row['strike']
                        max_profit = width - debit
                        ror = (max_profit / debit) * 100 if debit > 0 else 0
                        
                        net_vega = long_row['vega'] - short_row['vega']
                        
                        results.append({
                            'Expiry': date_str,
                            'Long Strike': long_row['strike'],
                            'Short Strike': short_row['strike'],
                            'Debit': debit,
                            'BreakEven': break_even,
                            'Safety%': safety_pct,
                            'RoR%': ror,
                            'Net Vega': net_vega
                        })

            except Exception:
                continue

        if not results:
            self.log("No valid strategies.")
            return

        df = pd.DataFrame(results)
        df = df.sort_values(by=['Safety%', 'RoR%'], ascending=[True, False])
        
        cols = ['Expiry', 'Long Strike', 'Short Strike', 'Debit', 'BreakEven', 'Safety%', 'RoR%', 'Net Vega']
        print(df[cols].head(20).to_string(index=False))
        
        self.log_separator()
        if not df.empty:
            best = df.iloc[0]
            self.log(f"🛡️ Best Defensive Pick: {best['Expiry']} Buy ${best['Long Strike']} / Sell ${best['Short Strike']}")
            self.log(f"   Break Even: ${best['BreakEven']:.2f} (Safety: {best['Safety%']:.2f}%)")
