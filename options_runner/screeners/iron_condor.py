import pandas as pd
from options_runner.screeners.base_screener import BaseScreener
from options_runner.utils.option_math import calculate_greeks

class IronCondorScreener(BaseScreener):
    def run(self, symbol, short_delta=0.20, wing_width_target=2.5, min_days=25, max_days=60):
        self.log_header(f"{symbol} Iron Condor Strategy")
        
        # 1. Market Data & Context
        try:
            vol_data = self.market.get_volatility_data(symbol)
        except Exception as e:
            self.log(f"Error fetching data: {e}")
            return

        current_price = vol_data['current_price']
        iv_rank = vol_data['iv_rank']
        
        self.log(f"Price: ${current_price:.2f}")
        self.log(f"IV Rank: {iv_rank:.1f}%")
        
        if iv_rank < 30:
            self.log("⚠️ Low Volatility Warning (IV Rank < 30)")
        elif iv_rank > 50:
            self.log("✅ High Volatility Environment (Good for Selling)")
            
        # Earnings check
        earnings = self.market.get_earnings_date(symbol)
        if earnings:
            self.log(f"📅 Next Earnings: {earnings}")

        # 2. Iterate Dates
        target_dates = self.market.get_option_dates(symbol, min_days, max_days)
        if not target_dates:
            self.log("No suitable expiration dates found.")
            return

        results = []
        
        for date_str, days in target_dates:
            try:
                calls, puts = self.market.get_chain(symbol, date_str)
                
                # Filter liquidity
                calls = calls[(calls['bid'] > 0) & (calls['ask'] > 0)].copy()
                puts = puts[(puts['bid'] > 0) & (puts['ask'] > 0)].copy()
                
                calls['mid'] = (calls['bid'] + calls['ask']) / 2
                puts['mid'] = (puts['bid'] + puts['ask']) / 2
                
                calls['time_to_expiry'] = days / 365.0
                puts['time_to_expiry'] = days / 365.0
                
                # Calculate Greeks
                calls = calculate_greeks(calls, current_price, 'c')
                puts = calculate_greeks(puts, current_price, 'p')
                
                # Logic: Find Short Legs (~short_delta)
                short_call = calls.iloc[(calls['delta'] - short_delta).abs().argsort()[:1]]
                # Put delta is usually negative, so we look for distance from -short_delta
                short_put = puts.iloc[(puts['delta'] - (-short_delta)).abs().argsort()[:1]]
                
                if short_call.empty or short_put.empty: continue
                
                s_call_row = short_call.iloc[0]
                s_put_row = short_put.iloc[0]
                
                # Logic: Find Long Legs (Wings)
                target_long_call_strike = s_call_row['strike'] + wing_width_target
                target_long_put_strike = s_put_row['strike'] - wing_width_target
                
                long_call = calls.iloc[(calls['strike'] - target_long_call_strike).abs().argsort()[:1]]
                long_put = puts.iloc[(puts['strike'] - target_long_put_strike).abs().argsort()[:1]]
                
                if long_call.empty or long_put.empty: continue
                
                l_call_row = long_call.iloc[0]
                l_put_row = long_put.iloc[0]
                
                # Validate width
                actual_width_call = l_call_row['strike'] - s_call_row['strike']
                actual_width_put = s_put_row['strike'] - l_put_row['strike']
                
                if abs(actual_width_call - wing_width_target) > (wing_width_target * 0.3): continue
                
                # Metrics
                credit = (s_call_row['mid'] - l_call_row['mid']) + (s_put_row['mid'] - l_put_row['mid'])
                max_width = max(actual_width_call, actual_width_put)
                max_loss = max_width - credit
                
                if max_loss <= 0: continue
                
                ror = (credit / max_loss) * 100
                pop = 1 - (s_call_row['delta'] + abs(s_put_row['delta']))
                
                results.append({
                    'Expiry': date_str,
                    'Days': days,
                    'Short Put': s_put_row['strike'],
                    'Short Call': s_call_row['strike'],
                    'Width': max_width,
                    'Credit': credit,
                    'Max Loss': max_loss,
                    'RoR%': ror,
                    'POP%': pop * 100,
                    'Credit/Width': credit / max_width,
                    'BE_Low': s_put_row['strike'] - credit,
                    'BE_High': s_call_row['strike'] + credit
                })

            except Exception:
                continue

        if not results:
            self.log("No valid strategies found.")
            return

        df = pd.DataFrame(results)
        df = df[df['Credit'] > 0].sort_values(by='RoR%', ascending=False)
        
        # Display
        cols = ['Expiry', 'Days', 'Short Put', 'Short Call', 'Width', 'Credit', 'Max Loss', 'RoR%', 'POP%', 'Credit/Width']
        print(df[cols].to_string(index=False))
        
        self.log_separator()
        self.log("🤖 Tastytrade / Market Maker Analysis")
        
        golden = df[df['Credit/Width'] >= 0.30].sort_values(by='POP%', ascending=False)
        if not golden.empty:
            best = golden.iloc[0]
            self.log(f"🏆 Gold Standard: {best['Expiry']} (Width ${best['Width']})")
            self.log(f"   Credit/Width: {best['Credit/Width']:.2f}")
        else:
             self.log("⚠️ No strategies meet the 30% credit/width Golden Rule.")
