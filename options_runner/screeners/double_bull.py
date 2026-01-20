import pandas as pd
from options_runner.screeners.base_screener import BaseScreener
from options_runner.utils.option_math import calculate_greeks

class DoubleBullScreener(BaseScreener):
    def run(self, symbol, max_put_strike=None, min_call_strike=None, put_width=5, min_days=45, max_days=90):
        # Default fallback if kwargs missing (though caller should provide)
        if max_put_strike is None or min_call_strike is None:
            self.log("⚠️ Error: max_put_strike and min_call_strike are required for Double Bull.")
            return

        self.log_header(f"{symbol} Double Bull Strategy")
        self.log(f"Params: Put Iron Bottom ${max_put_strike} | Call Top Target ${min_call_strike} | Put Width ${put_width}")

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
                calls, puts = self.market.get_chain(symbol, date_str)
                if calls.empty or puts.empty: continue
                
                # Basic filter & Greeks
                puts = puts[(puts['bid'] > 0) & (puts['ask'] > 0)].copy()
                puts['mid'] = (puts['bid'] + puts['ask']) / 2
                puts['time_to_expiry'] = days / 365.0
                puts = calculate_greeks(puts, current_price, 'p')
                
                calls = calls[(calls['bid'] > 0) & (calls['ask'] > 0)].copy()
                calls['mid'] = (calls['bid'] + calls['ask']) / 2
                
                # --- Strategy Construction ---
                # 1. Bull Put Spread (Credit)
                short_put_candidates = puts[puts['strike'] <= max_put_strike]
                
                for _, sp_row in short_put_candidates.iterrows():
                    short_put_strike = sp_row['strike']
                    target_long_put = short_put_strike - put_width
                    
                    lp_rows = puts[puts['strike'] == target_long_put]
                    if lp_rows.empty: continue
                    lp_row = lp_rows.iloc[0]
                    
                    put_credit = sp_row['mid'] - lp_row['mid']
                    if put_credit <= 0: continue
                    
                    # 2. Bull Call Spread (Debit funded by credit)
                    short_call_candidates = calls[calls['strike'] >= min_call_strike]
                    
                    for _, sc_row in short_call_candidates.iterrows():
                        short_call_strike = sc_row['strike']
                        short_call_price = sc_row['mid']
                        
                        # Total budget = Credit from puts + Premium we get from selling call (Wait??)
                        # Original logic: total_budget = put_spread_credit + short_call_price
                        # Then look for a Long Call such that long_call_price <= total_budget?
                        # If long_call_price <= put_credit + short_call_price
                        # Then Net Credit = (put_credit + short_call_price) - long_call_price
                        # Yes, this funds the Long Call using both the Put Spread credit and the Short Call premium.
                        
                        total_budget = put_credit + short_call_price
                        
                        potential_long_calls = calls[
                            (calls['mid'] <= total_budget) &
                            (calls['strike'] < short_call_strike) &
                            (calls['strike'] > current_price)
                        ].sort_values(by='strike')
                        
                        if potential_long_calls.empty: continue
                        
                        lc_row = potential_long_calls.iloc[0] # Pick the lowest strike we can afford? 
                        # Original code sorted by strike ascending, so lowest strike (Deepest ITM or closest)
                        
                        long_call_strike = lc_row['strike']
                        
                        net_credit = total_budget - lc_row['mid']
                        collateral = put_width * 100
                        
                        call_spread_width = short_call_strike - long_call_strike
                        max_profit = (call_spread_width * 100) + (net_credit * 100)
                        real_max_loss = collateral - (net_credit * 100)
                        
                        results.append({
                            'Expiry': date_str,
                            'BuyPut': int(target_long_put),
                            'SellPut': int(short_put_strike),
                            'BuyCall': int(long_call_strike),
                            'SellCall': int(short_call_strike),
                            'Credit': net_credit,
                            'MaxProfit': max_profit,
                            'MaxLoss': real_max_loss,
                            'Start': long_call_strike
                        })

            except Exception:
                continue

        if not results:
            self.log("No valid strategies.")
            return

        df = pd.DataFrame(results)
        df = df[df['Credit'] >= -0.10].sort_values(by=['Start', 'MaxProfit'], ascending=[True, False])
        
        cols = ['Expiry', 'BuyPut', 'SellPut', 'BuyCall', 'SellCall', 'Credit', 'MaxProfit', 'MaxLoss', 'Start']
        print(df[cols].head(15).to_string(index=False))
        
        # AI logic
        if not df.empty:
            self.log_separator()
            best = df.iloc[0]
            self.log(f"🚀 Best Aggressive: {best['Expiry']} | Start profit > ${best['Start']}")
