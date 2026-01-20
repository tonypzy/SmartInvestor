import pandas as pd
import numpy as np
from options_runner.screeners.base_screener import BaseScreener
from options_runner.utils.option_math import calculate_greeks

class BullPutScreener(BaseScreener):
    def run(self, symbol, spread_widths=[5, 10, 15, 20], min_days=15, max_days=60, max_sell_strike=None, min_buy_strike=None):
        if isinstance(spread_widths, (int, float)):
            spread_widths = [spread_widths]
            
        self.log_header(f"{symbol} Bull Put Spread (Advanced)")
        
        # 1. Context & Data
        try:
            vol_data = self.market.get_volatility_data(symbol)
        except Exception as e:
            self.log(f"Error fetching data: {e}")
            return

        current_price = vol_data['current_price']
        iv_rank_est = vol_data['iv_rank']
        curr_hv = vol_data['hv_30']
        
        self.log(f"Price: ${current_price:.2f}")
        self.log(f"IV Rank: {iv_rank_est:.1f}%")
        
        earnings = self.market.get_earnings_date(symbol)
        if earnings:
            self.log(f"📅 Next Earnings: {earnings}")

        target_dates = self.market.get_option_dates(symbol, min_days, max_days)
        if not target_dates:
            self.log("No option dates found.")
            return

        results = []
        
        for date_str, days in target_dates:
            try:
                _, puts = self.market.get_chain(symbol, date_str)
                if puts.empty: continue
                
                # Filter valid
                puts = puts[(puts['bid'] > 0) & (puts['ask'] > 0)].copy()
                puts['mid'] = (puts['bid'] + puts['ask']) / 2
                puts['time_to_expiry'] = days / 365.0
                
                # Calculate Greeks
                puts = calculate_greeks(puts, current_price, 'p')
                
                # ATM IV for Skew
                atm_row = puts.iloc[(puts['strike'] - current_price).abs().argsort()[:1]]
                atm_iv = atm_row['iv'].iloc[0] if not atm_row.empty else 0
                
                # Short candidates: Delta -0.45 to -0.10
                short_candidates = puts[(puts['delta'] > -0.45) & (puts['delta'] < -0.10)].copy()
                if max_sell_strike:
                    short_candidates = short_candidates[short_candidates['strike'] <= max_sell_strike]
                    
                for idx, short_row in short_candidates.iterrows():
                    s_spread = short_row['ask'] - short_row['bid']
                    if short_row['bid'] == 0 or (s_spread / short_row['bid']) > 0.25: continue
                    
                    short_strike = short_row['strike']
                    
                    for width in spread_widths:
                        target_long_strike = short_strike - width
                        if min_buy_strike and target_long_strike < min_buy_strike: continue
                        
                        long_rows = puts[puts['strike'] == target_long_strike]
                        if long_rows.empty: continue
                        long_row = long_rows.iloc[0]
                        
                        l_spread = long_row['ask'] - long_row['bid']
                        if l_spread > 0.50 and (l_spread / long_row['ask']) > 0.30: continue
                        
                        # Slippage
                        SLIPPAGE_PCT = 0.15
                        short_fill = short_row['mid'] - (s_spread * SLIPPAGE_PCT)
                        long_fill = long_row['mid'] + (l_spread * SLIPPAGE_PCT)
                        net_credit = short_fill - long_fill
                        
                        if net_credit <= 0.05: continue
                        
                        max_loss = width - net_credit
                        ror = (net_credit / max_loss) * 100
                        pop = (1 - abs(short_row['delta'])) * 100
                        
                        # Expected Value
                        ev = (pop/100 * net_credit) - ((1 - pop/100) * max_loss)
                        
                        # IV Skew
                        skew = short_row['iv'] - atm_iv
                        
                        break_even = short_strike - net_credit
                        buffer_pct = ((current_price - break_even) / current_price) * 100
                        
                        gamma_risk = "HIGH" if (days < 45 and abs(short_row['delta']) > 0.30) else "LOW"
                        
                        results.append({
                            'Expiry': date_str,
                            'Days': days,
                            'Width': width,
                            'Short Put': short_strike,
                            'Long Put': target_long_strike,
                            'S.Delta': short_row['delta'],
                            'Credit': net_credit,
                            'RoR%': ror,
                            'EV': ev,
                            'Prob%': pop,
                            'Buffer%': buffer_pct,
                            'IV_Skew': skew,
                            'Risk': gamma_risk
                        })
            except Exception:
                continue

        if not results:
            self.log("No valid strategies found.")
            return

        df = pd.DataFrame(results)
        
        # Heatmap / Term Structure Logic
        self.log_separator()
        self.log("📊 Term Structure Summary (Sorted by EV)")
        heatmap = df.groupby('Expiry').agg({
            'EV': 'mean', 'IV_Skew': 'mean', 'Short Put': 'count'
        }).rename(columns={'Short Put': 'Setups'}).sort_values(by='EV', ascending=False)
        print(heatmap)
        
        # Filter & Sort Result
        filtered_df = df[df['RoR%'] >= 8].copy()
        filtered_df = filtered_df.sort_values(by=['EV', 'IV_Skew'], ascending=[False, False])
        
        self.log_separator()
        cols = ['Expiry', 'Width', 'Short Put', 'S.Delta', 'EV', 'RoR%', 'Prob%', 'Buffer%', 'IV_Skew', 'Risk']
        print(filtered_df[cols].to_string(index=False))
        
        # AI Recommendations
        clean_df = filtered_df.copy() # Simplification: earnings handled contextually
        
        self.log_separator()
        self.log(f"🤖 AI Recommendations (IV Rank: {iv_rank_est:.1f}%)")
        
        if not clean_df.empty:
            best_ev = clean_df.iloc[0]
            self.log(f"📈 Best mathematical edge (EV): {best_ev['Expiry']} ${best_ev['Short Put']}/{best_ev['Long Put']} (EV: ${best_ev['EV']:.2f})")
            
            if iv_rank_est > 50:
                self.log("🌊 IV Crusher mode recommended (Sell high IV).")
            else:
                self.log("🛡️ Defensive mode recommended (IV is low).")
