import pandas as pd
from options_runner.screeners.base_screener import BaseScreener
from options_runner.utils.option_math import calculate_greeks

class ZebraScreener(BaseScreener):
    def run(self, symbol, min_days=60, max_days=180, threshold_pct=1.0):
        self.log_header(f"{symbol} ZEBRA Strategy (Zero Extrinsic Bullish Risk Adjustment)")
        
        # 1. Market Data
        try:
            vol_data = self.market.get_volatility_data(symbol)
        except Exception as e:
            self.log(f"Error fetching data: {e}")
            return

        current_price = vol_data['current_price']
        self.log(f"Price: ${current_price:.2f}")
        
        dynamic_threshold = current_price * (threshold_pct / 100.0)
        self.log(f"Dynamic Threshold: Only accept Net Extrinsic < ${dynamic_threshold:.2f} ({threshold_pct}%)")

        # 2. Iterate Dates
        target_dates = self.market.get_option_dates(symbol, min_days, max_days)
        if not target_dates:
            self.log("No suitable expiration dates found.")
            return

        results = []

        def calculate_extrinsic(price, strike, spot):
            intrinsic = max(0, spot - strike)
            return price - intrinsic

        for date_str, days in target_dates:
            try:
                calls, _ = self.market.get_chain(symbol, date_str)
                if calls.empty: continue
                
                calls = calls[(calls['bid'] > 0) & (calls['ask'] > 0)].copy()
                calls['mid'] = (calls['bid'] + calls['ask']) / 2
                calls['time_to_expiry'] = days / 365.0
                
                # Calculate Greeks
                calls = calculate_greeks(calls, current_price, 'c')
                
                # Filter candidates for ZEBRA (2x ITM Long, 1x ATM Short)
                # Long: ~0.75 delta (0.65-0.85)
                # Short: ~0.50 delta (0.40-0.60)
                long_candidates = calls[(calls['delta'] >= 0.65) & (calls['delta'] <= 0.85)]
                short_candidates = calls[(calls['delta'] >= 0.40) & (calls['delta'] <= 0.60)]
                
                for _, long_row in long_candidates.iterrows():
                    l_ext = calculate_extrinsic(long_row['mid'], long_row['strike'], current_price)
                    
                    for _, short_row in short_candidates.iterrows():
                        if short_row['strike'] <= long_row['strike']: continue
                        
                        s_ext = calculate_extrinsic(short_row['mid'], short_row['strike'], current_price)
                        
                        # ZEBRA formula: Net Ext = 2*Long_Ext - 1*Short_Ext
                        net_extrinsic = (2 * l_ext) - s_ext
                        
                        if abs(net_extrinsic) > dynamic_threshold: continue
                        
                        # Metrics
                        total_debit = (2 * long_row['mid']) - short_row['mid']
                        net_delta = (2 * long_row['delta']) - short_row['delta']
                        
                        # ZEBRA theta should be near 0
                        net_theta = (2 * long_row['theta']) - short_row['theta'] 
                        
                        results.append({
                            'Expiry': date_str,
                            'Days': days,
                            'Long_Strike': long_row['strike'],
                            'Short_Strike': short_row['strike'],
                            'Debit': total_debit,
                            'Net_Delta': net_delta,
                            'Net_Theta': net_theta,
                            'Net_Extrinsic': net_extrinsic,
                            'Leverage': (net_delta * current_price) / total_debit
                        })
            
            except Exception:
                continue

        if not results:
            self.log(f"No ZEBRA combinations found within {threshold_pct}% extrinsic limit.")
            return

        df = pd.DataFrame(results)
        # Sort by Net Extrinsic closest to 0
        df = df.sort_values(by='Net_Extrinsic', key=lambda x: x.abs())
        
        self.log_separator()
        print(df.head(20).to_string(index=False))
        
        self.log_separator()
        best = df.iloc[0]
        self.log(f"🌟 Best Pick: {best['Expiry']} | Buy 2x {best['Long_Strike']}C / Sell 1x {best['Short_Strike']}C")
        self.log(f"   Net Extrinsic: ${best['Net_Extrinsic']:.2f}")
        self.log(f"   Net Theta: {best['Net_Theta']:.4f} (Time decay eliminated!)")
