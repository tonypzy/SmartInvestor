import pandas as pd
from options_runner.screeners.base_screener import BaseScreener
from options_runner.utils.option_math import calculate_greeks

class LongStrangleScreener(BaseScreener):
    def run(self, symbol, min_days=14, max_days=60, target_deltas=[0.15, 0.20, 0.25]):
        if isinstance(target_deltas, (int, float)):
             target_deltas = [target_deltas]

        self.log_header(f"{symbol} Long Strangle (Volatility Buying)")
        
        try:
            vol_data = self.market.get_volatility_data(symbol)
            current_price = vol_data['current_price']
            curr_hv = vol_data['hv_30']
            self.log(f"Price: ${current_price:.2f} | 30D HV: {curr_hv*100:.2f}% | IV Rank: {vol_data['iv_rank']:.1f}%")
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
                
                # Filter & Greeks
                calls = calls[(calls['bid']>0) & (calls['ask']>0)].copy()
                puts = puts[(puts['bid']>0) & (puts['ask']>0)].copy()
                
                calls['mid'] = (calls['bid']+calls['ask'])/2
                puts['mid'] = (puts['bid']+puts['ask'])/2
                
                calls['time_to_expiry'] = days/365.0
                puts['time_to_expiry'] = days/365.0
                
                calls = calculate_greeks(calls, current_price, 'c')
                puts = calculate_greeks(puts, current_price, 'p')
                
                for t_delta in target_deltas:
                    # Find Call ~ t_delta
                    call_leg = calls.iloc[(calls['delta'] - t_delta).abs().argsort()[:1]]
                    # Find Put ~ -t_delta
                    put_leg = puts.iloc[(puts['delta'] - (-t_delta)).abs().argsort()[:1]]
                    
                    if call_leg.empty or put_leg.empty: continue
                    
                    c_row = call_leg.iloc[0]
                    p_row = put_leg.iloc[0]
                    
                    if abs(c_row['delta'] - t_delta) > 0.10: continue
                    
                    # Total Cost (Debit)
                    total_debit = c_row['mid'] + p_row['mid']
                    
                    # Implied Move
                    implied_move_pct = (total_debit / current_price) * 100
                    
                    # Net Greeks
                    net_gamma = c_row['gamma'] + p_row['gamma']
                    net_theta = c_row['theta'] + p_row['theta'] # Negative
                    net_vega = c_row['vega'] + p_row['vega'] # Positive
                    
                    if net_theta == 0: continue
                    
                    gt_ratio = abs(net_gamma / net_theta) * 100
                    
                    results.append({
                        'Expiry': date_str,
                        'Target Delta': t_delta,
                        'Call Strike': c_row['strike'],
                        'Put Strike': p_row['strike'],
                        'Debit': total_debit,
                        'Imp_Move%': implied_move_pct,
                        'G/T Ratio': gt_ratio,
                        'Theta_Daily': net_theta
                    })
                    
            except Exception:
                continue

        if not results:
            self.log("No valid strategies.")
            return

        df = pd.DataFrame(results)
        df_sorted = df.sort_values(by='G/T Ratio', ascending=False)
        
        cols = ['Expiry', 'Target Delta', 'Call Strike', 'Put Strike', 'Debit', 'Imp_Move%', 'G/T Ratio', 'Theta_Daily']
        print(df_sorted[cols].to_string(index=False))
        
        self.log_separator()
        if not df_sorted.empty:
            best = df_sorted.iloc[0]
            self.log(f"⚔️ Best Gamma Scalp: {best['Expiry']} (G/T: {best['G/T Ratio']:.1f})")
            
            # Value check
            cheap_vol = df_sorted[df_sorted['Imp_Move%'] < (curr_hv * 100 * (days/365)**0.5)]
            if not cheap_vol.empty:
                val = cheap_vol.iloc[0]
                self.log(f"💎 Undervalued Volatility found: {val['Expiry']} (Implied Move {val['Imp_Move%']:.2f}%)")
