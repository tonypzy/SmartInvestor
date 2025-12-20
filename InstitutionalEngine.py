import yfinance as yf
import pandas as pd
import numpy as np
from scipy.stats import norm
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import pytz

class InstitutionalEngine:
    def __init__(self, ticker, r=0.045):
        self.ticker = ticker.upper()
        self.r = r
        self.stock = yf.Ticker(self.ticker)
        self.spot = self._get_spot()
        self.is_open = self._check_market_open()

    def _get_spot(self):
        hist = self.stock.history(period='1d')
        if hist.empty: raise ValueError(f"无法获取 {self.ticker} 的价格。")
        return hist['Close'].iloc[-1]
    
    def _check_market_open(self):
        tz = pytz.timezone('US/Eastern')
        now = datetime.now(tz)
        if now.weekday() > 4: return False
        market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
        return market_open <= now <= market_close

    def black_scholes_delta(self, S, K, T, sigma, option_type='call'):
        if T <= 0 or sigma <= 0: return 0
        d1 = (np.log(S / K) + (self.r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        return norm.cdf(d1) if option_type == 'call' else norm.cdf(d1) - 1

    def get_market_data(self, expiration):
        chain = self.stock.option_chain(expiration)
        today = pd.Timestamp.now().normalize()
        exp_date = pd.to_datetime(expiration).normalize()
        T = max((exp_date - today).days, 1) / 365.0
        
        def process(df, opt_type):
            df = df[df['openInterest'] > -1].copy()
            if df.empty: return df
            df['delta'] = df.apply(lambda x: self.black_scholes_delta(self.spot, x['strike'], T, x['impliedVolatility'], opt_type), axis=1)
            return df
        return process(chain.calls, 'call'), process(chain.puts, 'put'), T

    def select_seagull_pro(self, expiration, k2_delta=0.45, k3_delta=0.20, k1_delta=-0.15):
        """标准版逻辑：包含 IV 修正和 ROMR"""
        calls, puts, T = self.get_market_data(expiration)
        if calls.empty or puts.empty: raise ValueError("数据不足")

        # 1. 寻找行权价
        k2_row = calls.iloc[(calls['delta'] - k2_delta).abs().argsort()[:1]]
        k2_strike = k2_row['strike'].values[0]

        higher_calls = calls[calls['strike'] > k2_strike]
        if higher_calls.empty: raise ValueError("K3 匹配失败")
        k3_row = higher_calls.iloc[(higher_calls['delta'] - k3_delta).abs().argsort()[:1]]
        k3_strike = k3_row['strike'].values[0]

        lower_puts = puts[puts['strike'] < k2_strike]
        if lower_puts.empty: raise ValueError("K1 匹配失败")
        k1_row = lower_puts.iloc[(lower_puts['delta'] - k1_delta).abs().argsort()[:1]]
        k1_strike = k1_row['strike'].values[0]

        # 2. 定价逻辑 (Mid Price)
        def get_pricing(row):
            bid, ask, last = row['bid'].values[0], row['ask'].values[0], row['lastPrice'].values[0]
            return (bid + ask) / 2 if (bid > 0 and ask > 0) else last

        # 3. 胜率修正 (处理盘后 IV=0 问题)
        ref_iv = calls['impliedVolatility'].replace(0, np.nan).mean()
        iv_k1 = k1_row['impliedVolatility'].values[0]
        if iv_k1 < 0.01: iv_k1 = ref_iv if not np.isnan(ref_iv) else 0.3
        cal_k1_delta = self.black_scholes_delta(self.spot, k1_strike, T, iv_k1, 'put')

        res = {
            'K1_Put': [k1_strike, get_pricing(k1_row), cal_k1_delta],
            'K2_Call': [k2_strike, get_pricing(k2_row), k2_row['delta'].values[0]],
            'K3_Call': [k3_strike, get_pricing(k3_row), k3_row['delta'].values[0]],
        }

        # 4. 指标计算
        net_prem = res['K1_Put'][1] + res['K3_Call'][1] - res['K2_Call'][1]
        margin = k1_strike * 0.20 # 裸卖 Put 保证金
        max_profit = (k3_strike - k2_strike + net_prem)
        max_risk = (k1_strike - net_prem) # 标准版最大风险
        
        metrics = {
            "Expiration": expiration, "Net_Premium": net_prem, "Annual_Return": (max_profit/margin)/T if margin>0 else 0,
            "Max_Profit_USD": max_profit, "Max_Risk_USD": max_risk, "ROMR": max_profit/max_risk if max_risk>0 else 0,
            "T": T, "Buffer": (self.spot - k1_strike)/self.spot, "Win_Rate": min(1-abs(cal_k1_delta), 0.999), "Is_Protected": False
        }
        return res, metrics

    def select_protected_seagull(self, expiration, k2_delta=0.45, k3_delta=0.20, k1_delta=-0.15, k0_delta=-0.05):
        """保护版逻辑：买入 K0 锁定风险"""
        res, metrics = self.select_seagull_pro(expiration, k2_delta, k3_delta, k1_delta)
        _, puts, _ = self.get_market_data(expiration)
        
        k1_strike = res['K1_Put'][0]
        lower_puts = puts[puts['strike'] < k1_strike]
        if lower_puts.empty: raise ValueError("找不到 K0")
        k0_row = lower_puts.iloc[(lower_puts['delta'] - k0_delta).abs().argsort()[:1]]
        k0_strike = k0_row['strike'].values[0]
        k0_price = (k0_row['bid'].values[0] + k0_row['ask'].values[0])/2 if k0_row['bid'].values[0]>0 else k0_row['lastPrice'].values[0]

        # 更新指标
        new_net_prem = metrics['Net_Premium'] - k0_price
        new_margin = (k1_strike - k0_strike) # 保证金大幅下降
        new_max_profit = (res['K3_Call'][0] - res['K2_Call'][0] + new_net_prem)
        new_max_risk = new_margin - new_net_prem

        res['K0_Put'] = [k0_strike, k0_price, k0_row['delta'].values[0]]
        metrics.update({
            "Net_Premium": new_net_prem, "Annual_Return": (new_max_profit/new_margin)/metrics['T'],
            "Max_Profit_USD": new_max_profit, "Max_Risk_USD": new_max_risk,
            "ROMR": new_max_profit/new_max_risk if new_max_risk>0 else 10, "Is_Protected": True
        })
        return res, metrics

    def scan_seagull_range(self, min_dte=30, max_dte=70, force_zero_cost=False, min_buffer=0.05, protected=False):
        all_exp = self.stock.options
        today = datetime.now()
        valid_strategies = []

        parameter_sets = [
            {'k2': 0.45, 'k3': 0.20, 'k1': -0.15},
            {'k2': 0.45, 'k3': 0.25, 'k1': -0.15},
            {'k2': 0.45, 'k3': 0.20, 'k1': -0.20}
        ]

        print(f"--- 正在扫描 {self.ticker} ({'保护模式' if protected else '标准模式'}) ---")

        for exp_str in all_exp:
            dte = (datetime.strptime(exp_str, '%Y-%m-%d') - today).days
            if not (min_dte <= dte <= max_dte): continue

            date_candidates = []
            for p in parameter_sets:
                try:
                    func = self.select_protected_seagull if protected else self.select_seagull_pro
                    res, metrics = func(exp_str, p['k2'], p['k3'], p['k1'])
                    
                    if force_zero_cost and metrics['Net_Premium'] < 0: continue
                    if metrics['Buffer'] < min_buffer: continue

                    date_candidates.append({
                        **metrics, "DTE": dte,
                        "K1_Strike": res['K1_Put'][0], "K2_Strike": res['K2_Call'][0],
                        "K3_Strike": res['K3_Call'][0], "K0_Strike": res.get('K0_Put', [None])[0]
                    })
                except: continue
            
            # 每个日期按 ROMR 排序，取前 3 个
            date_candidates = sorted(date_candidates, key=lambda x: x['ROMR'], reverse=True)
            valid_strategies.extend(date_candidates[:3])

        df = pd.DataFrame(valid_strategies)
        if df.empty: return df
        norm = lambda x: (x - x.min()) / (x.max() - x.min() + 1e-5)
        df['Score'] = (norm(df['Annual_Return']) * 0.4 + norm(df['Buffer']) * 0.4 + norm(df['ROMR']) * 0.2) * 100
        return df.sort_values(by="Score", ascending=False)

    def plot_payoff(self, res, metrics):
        net_prem = metrics['Net_Premium']
        k1, k2, k3 = res['K1_Put'][0], res['K2_Call'][0], res['K3_Call'][0]
        k0 = res.get('K0_Put', [0])[0]
        
        s_range = np.linspace((k0 if k0>0 else k1)*0.7, k3*1.2, 100)
        pnl_y = []
        for s in s_range:
            v = max(0, s - k2) - max(0, s - k3) # Call Spread
            if k0 > 0: v -= (max(0, k1 - s) - max(0, k0 - s)) # Protected Put Spread
            else: v -= max(0, k1 - s) # Naked Put
            pnl_y.append(v + net_prem)

        plt.figure(figsize=(10, 5))
        plt.plot(s_range, pnl_y, color='royalblue', lw=2.5)
        plt.axhline(0, color='black', lw=1)
        plt.fill_between(s_range, pnl_y, 0, where=(np.array(pnl_y)>0), color='green', alpha=0.1)
        plt.fill_between(s_range, pnl_y, 0, where=(np.array(pnl_y)<0), color='red', alpha=0.1)
        plt.title(f"{'Protected' if k0>0 else 'Standard'} Seagull {self.ticker} | ROMR: {metrics['ROMR']:.2f}")
        plt.grid(True, alpha=0.2); plt.show()