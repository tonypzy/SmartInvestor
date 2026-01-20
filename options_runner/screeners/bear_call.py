import pandas as pd
import numpy as np
import scipy.stats as si
from options_runner.screeners.base_screener import BaseScreener
from options_runner.utils.option_math import calculate_greeks

class BearCallScreener(BaseScreener):
    def run(self, symbol, spread_widths=[2.5, 5, 10], min_days=30, max_days=60, min_sell_strike=None):
        if isinstance(spread_widths, (int, float)):
            spread_widths = [spread_widths]
        
        self.log_header(f"{symbol} Bear Call Spread (Credit)")
        
        try:
            vol_data = self.market.get_volatility_data(symbol)
        except Exception as e:
            self.log(f"Error fetching data: {e}")
            return

        current_price = vol_data['current_price']
        iv_rank_est = vol_data['iv_rank']
        curr_hv = vol_data['hv_30']
        
        self.log(f"Price: ${current_price:.2f} | IV Rank: {iv_rank_est:.1f}%")

        target_dates = self.market.get_option_dates(symbol, min_days, max_days)
        if not target_dates:
            self.log("No valid dates.")
            return

        results = []
        
        for date_str, days in target_dates:
            try:
                calls, _ = self.market.get_chain(symbol, date_str)
                if calls.empty: continue
                
                # Filter specific to this strategy (min vol/OI)
                calls = calls[(calls['volume'] >= 5) & (calls['openInterest'] >= 50)].copy()
                if calls.empty: continue
                
                calls = calls[(calls['bid'] > 0) & (calls['ask'] > 0)].copy()
                calls['mid'] = (calls['bid'] + calls['ask']) / 2
                calls['time_to_expiry'] = days / 365.0
                
                calls = calculate_greeks(calls, current_price, 'c')
                
                # ATM IV
                atm_row = calls.iloc[(calls['strike'] - current_price).abs().argsort()[:1]]
                atm_iv = atm_row['iv'].iloc[0] if not atm_row.empty else 0
                
                # Short Candidates: Delta 0.15 - 0.45
                short_candidates = calls[(calls['delta'] > 0.15) & (calls['delta'] < 0.45)].copy()
                if min_sell_strike:
                    short_candidates = short_candidates[short_candidates['strike'] >= min_sell_strike]
                    
                for idx, short_row in short_candidates.iterrows():
                    s_spread = short_row['ask'] - short_row['bid']
                    if short_row['bid'] == 0: continue
                    
                    for width in spread_widths:
                        # Long Strike > Short Strike (Credit Call Spread)
                        target_long_strike = short_row['strike'] + width
                        
                        long_rows = calls[calls['strike'] == target_long_strike]
                        if long_rows.empty: continue
                        long_row = long_rows.iloc[0]
                        
                        l_spread = long_row['ask'] - long_row['bid']
                        
                        # Slippage logic
                        SLIPPAGE_PCT = 0.15
                        short_fill = short_row['mid'] - (s_spread * SLIPPAGE_PCT)
                        long_fill = long_row['mid'] + (l_spread * SLIPPAGE_PCT)
                        net_credit = short_fill - long_fill
                        
                        if net_credit <= 0.05: continue
                        
                        max_loss = width - net_credit
                        ror = (net_credit / max_loss) * 100
                        
                        # Real POP calculation (N(-d2))
                        sigma = short_row['iv']
                        break_even = short_row['strike'] + net_credit
                        d2 = (np.log(current_price / break_even) + (0.044 - 0.5 * sigma**2) * calls['time_to_expiry'].iloc[0]) / (sigma * np.sqrt(calls['time_to_expiry'].iloc[0]))
                        real_pop = si.norm.cdf(-d2) * 100
                        
                        # EV
                        ev = (real_pop/100 * net_credit) - ((1 - real_pop/100) * max_loss)
                        
                        skew = short_row['iv'] - atm_iv
                        buffer_pct = ((break_even - current_price) / current_price) * 100
                        
                        gamma_risk = "HIGH" if (days < 21 and short_row['delta'] > 0.35) else "LOW"
                        
                        results.append({
                            'Expiry': date_str,
                            'Width': width,
                            'Short Call': short_row['strike'],
                            'S.Delta': short_row['delta'],
                            'Credit': net_credit,
                            'RoR%': ror,
                            'EV': ev,
                            'Prob%': real_pop,
                            'Buffer%': buffer_pct,
                            'IV_Skew': skew,
                            'Risk': gamma_risk
                        })
            except Exception:
                continue

        if not results:
            self.log("No valid strategies.")
            return

        df = pd.DataFrame(results)
        
        # Term structure
        self.log_separator()
        heatmap = df.groupby('Expiry').agg({
            'EV': 'mean', 'IV_Skew': 'mean', 'Short Call': 'count'
        }).rename(columns={'Short Call': 'Setups'}).sort_values(by='EV', ascending=False)
        print(heatmap)
        
        filtered_df = df[df['RoR%'] >= 10].copy()
        filtered_df = filtered_df.sort_values(by=['EV', 'RoR%'], ascending=[False, False])
        
        self.log_separator()
        cols = ['Expiry', 'Width', 'Short Call', 'S.Delta', 'EV', 'RoR%', 'Prob%', 'Buffer%', 'IV_Skew', 'Risk']
        print(filtered_df[cols].to_string(index=False))
        
        self.log_separator()
        self.log(f"🤖 Recommendations (Bearish/Neutral)")
        
        if not filtered_df.empty:
            best = filtered_df.iloc[0]
            self.log(f"🎯 Sniper: {best['Expiry']} Sell ${best['Short Call']} Call (EV: ${best['EV']:.2f})")
