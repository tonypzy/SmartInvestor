import pandas as pd
from options_runner.screeners.base_screener import BaseScreener
from options_runner.utils.option_math import calculate_greeks

class ShortStrangleScreener(BaseScreener):
    def run(self, symbol, min_days=30, max_days=60, target_deltas=[0.16, 0.20, 0.30]):
        if isinstance(target_deltas, (int, float)):
             target_deltas = [target_deltas]

        self.log_header(f"{symbol} Short Strangle (premium Selling)")
        
        try:
            vol_data = self.market.get_volatility_data(symbol)
            current_price = vol_data['current_price']
            self.log(f"Price: ${current_price:.2f} | IV Rank: {vol_data['iv_rank']:.1f}%")
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
                calls, puts = self.market.get_chain(symbol, date_str)
                if calls.empty or puts.empty: continue
                
                calls = calls[(calls['bid'] > 0) & (calls['ask'] > 0)].copy()
                puts = puts[(puts['bid'] > 0) & (puts['ask'] > 0)].copy()
                
                calls['mid'] = (calls['bid'] + calls['ask']) / 2
                puts['mid'] = (puts['bid'] + puts['ask']) / 2
                
                calls['time_to_expiry'] = days / 365.0
                puts['time_to_expiry'] = days / 365.0
                
                calls = calculate_greeks(calls, current_price, 'c')
                puts = calculate_greeks(puts, current_price, 'p')
                
                for t_delta in target_deltas:
                    # Closest Call to t_delta
                    call_leg = calls.iloc[(calls['delta'] - t_delta).abs().argsort()[:1]]
                    # Closest Put to -t_delta
                    put_leg = puts.iloc[(puts['delta'] - (-t_delta)).abs().argsort()[:1]]
                    
                    if call_leg.empty or put_leg.empty: continue
                    
                    c_row = call_leg.iloc[0]
                    p_row = put_leg.iloc[0]
                    
                    if abs(c_row['delta'] - t_delta) > 0.10: continue
                    
                    total_credit = c_row['mid'] + p_row['mid']
                    
                    # Safety
                    upper_be = c_row['strike'] + total_credit
                    lower_be = p_row['strike'] - total_credit
                    safety_pct = ((upper_be - current_price)/current_price + (current_price - lower_be)/current_price)/2 * 100
                    
                    # Net Greeks (Short Strangle = Short Call + Short Put)
                    # Theta is positive (we collect time)
                    net_theta = -(c_row['theta'] + p_row['theta'])
                    net_vega = -(c_row['vega'] + p_row['vega']) # We lose money if IV goes up
                    
                    pop = 1 - (abs(c_row['delta']) + abs(p_row['delta']))
                    
                    results.append({
                        'Expiry': date_str,
                        'Target Delta': t_delta,
                        'Short Call': c_row['strike'],
                        'Short Put': p_row['strike'],
                        'Credit': total_credit,
                        'Safety%': safety_pct,
                        'POP%': pop * 100,
                        'Theta_Daily': net_theta
                    })

            except Exception:
                continue

        if not results:
            self.log("No valid strategies.")
            return

        df = pd.DataFrame(results)
        df = df.sort_values(by='Theta_Daily', ascending=False)
        
        cols = ['Expiry', 'Target Delta', 'Short Call', 'Short Put', 'Credit', 'Safety%', 'POP%', 'Theta_Daily']
        print(df[cols].to_string(index=False))
        
        self.log_separator()
        if not df.empty:
            best = df.iloc[0]
            self.log(f"🛡️ Top Pick: {best['Expiry']} (Delta {best['Target Delta']}) | Daily Theta: ${best['Theta_Daily']:.2f}")
