import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, time
import pytz 
from py_vollib_vectorized import vectorized_implied_volatility, get_all_greeks

# ==========================================
# 🕒 市场状态检测模块
# ==========================================
def is_market_open():
    """
    检查当前是否为美股交易时间 (周一至周五 09:30 - 16:00 EST)
    """
    est = pytz.timezone('US/Eastern')
    now = datetime.now(est)
    
    # 检查是否是周末 (5=Sat, 6=Sun)
    if now.weekday() >= 5:
        return False, "Weekend"
    
    # 检查具体时间
    market_start = time(9, 30)
    market_end = time(16, 0)
    current_time = now.time()
    
    if market_start <= current_time <= market_end:
        return True, "Market Open"
    else:
        return False, "After Hours / Pre-Market"

# ==========================================
# 📊 终极筛选器 (OI 限制已放宽)
# ==========================================
def institutional_screener_robust(
    symbol, 
    spread_widths=[5, 7.5, 10, 12.5, 15, 17.5, 20, 22.5, 25], 
    min_days=25, 
    max_days=60,
    min_volume=10,        
    min_open_interest=0  # <--- 修改点：默认为 0，不再因为 OI 缺失而过滤
):
    pd.set_option('display.max_rows', None)
    pd.set_option('display.width', 1000)
    pd.set_option('display.float_format', '{:.2f}'.format)

    # 1. 检测市场状态
    market_active, status_msg = is_market_open()
    
    print(f"📊 INSTITUTIONAL SCREENER: {symbol}")
    print(f"   Time Status: {status_msg} (Est. Time)")
    
    if not market_active:
        print("   ⚠️  WARNING: Market is CLOSED. Using Last/Close prices for estimation.")
        print("      Bid/Ask data might be zero or stale. Switched to 'Mark Price' logic.")
        # 休市期间，适当放宽流动性检查
        min_volume = 0 
    
    print(f"   Target: {min_days}-{max_days} DTE | Widths: {spread_widths}")

    # 初始化诊断计数器
    rejection_stats = {
        "1. Low Liquidity (OI/Vol)": 0,
        "2. Data Integrity (Zero Price)": 0, 
        "3. Long Delta Out of Range": 0,
        "4. No Matching Short Leg": 0,
        "5. Invalid Debit (Math Error)": 0,
        "6. Negative Expected Value": 0,
        "7. Negative Skew": 0,
        "8. Passed": 0
    }

    tk = yf.Ticker(symbol)
    try:
            current_price = None
            
            # 1. 优先尝试 fast_info (最快，由 yfinance 提供)
            try:
                # 注意: 不同版本的 yfinance key 可能不同，这里多做几个尝试
                current_price = tk.fast_info.get('last_price')
                if not current_price:
                    current_price = tk.fast_info.get('regularMarketPrice')
            except:
                pass

            # 2. 如果 fast_info 失败 (也就是 current_price 还是 None)，强行读取 history
            # 即使是盘中，history(period='1d') 也能拿到最新的 tick 或前收盘
            if not current_price:
                print("   ⚠️ fast_info failed, attempting to fetch history...")
                hist = tk.history(period="1d")
                if not hist.empty:
                    # 使用最新的 Close 价格
                    current_price = hist['Close'].iloc[-1]
            
            # 3. 最终检查
            if not current_price:
                print("❌ Error: Could not determine underlying price.")
                return
            
            print(f"   Ref Price: ${current_price:.2f}")

    except Exception as e:
        print(f"❌ Data Error: {e}")
        return

    target_dates = []
    try:
        all_dates = tk.options
    except:
        print("❌ No options chain found.")
        return

    now = datetime.now()
    for d_str in all_dates:
        d_date = datetime.strptime(d_str, "%Y-%m-%d")
        days = (d_date - now).days
        if min_days <= days <= max_days:
            target_dates.append((d_str, days))

    results = []
    risk_free_rate = 0.044
    
    print(f"\n🔍 Scanning {len(target_dates)} expirations...\n")

    for date_str, days in target_dates:
        try:
            chain = tk.option_chain(date_str).calls
            
            # 数据预处理：填充缺失的 OI 为 0
            if 'openInterest' not in chain.columns:
                chain['openInterest'] = 0
            chain['openInterest'] = chain['openInterest'].fillna(0)
            
            # 价格估算逻辑
            def get_price_estimate(row):
                if row['bid'] > 0 and row['ask'] > 0:
                    return (row['bid'] + row['ask']) / 2
                else:
                    return row['lastPrice']

            chain['est_price'] = chain.apply(get_price_estimate, axis=1)
            
            if market_active:
                chain['spread_pct'] = (chain['ask'] - chain['bid']) / chain['est_price']
            else:
                chain['spread_pct'] = 0.0 
                
            time_to_expiry = days / 365.0
            
            chain['iv_calc'] = vectorized_implied_volatility(
                chain['est_price'], current_price, chain['strike'], time_to_expiry, 
                risk_free_rate, 'c', q=0, return_as='numpy'
            )
            greeks = get_all_greeks(
                'c', current_price, chain['strike'], time_to_expiry, 
                risk_free_rate, chain['iv_calc'], q=0, model='black_scholes', return_as='dict'
            )
            chain['delta'] = greeks['delta']
            
            # 遍历
            for idx, long_row in chain.iterrows():
                
                # [Filter 1] 流动性检查 (宽松版)
                # 只有当 volume 小于阈值 且 OI 小于阈值时才过滤
                # 既然 min_open_interest 设为了 0，这里实际上只看 min_volume
                if long_row['volume'] < min_volume or long_row['openInterest'] < min_open_interest:
                    rejection_stats["1. Low Liquidity (OI/Vol)"] += 1
                    continue
                
                # [Filter 2] 数据完整性
                if long_row['est_price'] <= 0.01:
                    rejection_stats["2. Data Integrity (Zero Price)"] += 1
                    continue

                # [Filter 3] Delta
                if not (0.50 <= long_row['delta'] <= 0.85):
                    rejection_stats["3. Long Delta Out of Range"] += 1
                    continue
                
                for width in spread_widths:
                    short_strike = long_row['strike'] + width
                    short_candidates = chain[chain['strike'] == short_strike]
                    
                    if short_candidates.empty: continue     
                    short_row = short_candidates.iloc[0]

                    # 卖出腿检查 (同样应用宽松的 OI 限制)
                    if short_row['openInterest'] < min_open_interest: 
                         rejection_stats["1. Low Liquidity (OI/Vol)"] += 1 
                         continue

                    # [Filter 5] 计算 Debit
                    if market_active:
                        debit = long_row['ask'] - short_row['bid'] 
                    else:
                        debit = long_row['est_price'] - short_row['est_price'] 
                    
                    if debit >= width or debit <= 0:
                        rejection_stats["5. Invalid Debit (Math Error)"] += 1
                        continue

                    # [Filter 6] EV 计算
                    pop_est = (long_row['delta'] + (1 - short_row['delta'])) / 2 * 100
                    max_profit = width - debit
                    ev = (pop_est/100 * max_profit) - ((1 - pop_est/100) * debit)
                    
                    if ev <= 0:
                        rejection_stats["6. Negative Expected Value"] += 1
                        continue

                    # [Filter 7] Skew
                    iv_skew = short_row['iv_calc'] - long_row['iv_calc']
                    if iv_skew < -0.02: 
                        rejection_stats["7. Negative Skew"] += 1
                        continue
                    
                    # Passed
                    rejection_stats["8. Passed"] += 1
                    
                    break_even = long_row['strike'] + debit
                    be_dist_pct = (break_even - current_price) / current_price * 100
                    
                    results.append({
                        'Expiry': date_str,
                        'Width': width,
                        'Long': long_row['strike'],
                        'Short': short_strike,
                        'Debit': debit, 
                        'MaxProfit': max_profit,
                        'RoR%': (max_profit / debit) * 100,
                        'PoP%': pop_est,
                        'EV': ev,
                        'IV Skew': iv_skew * 100,
                        'BE Dist%': be_dist_pct,
                        'DataSrc': 'Realtime' if market_active else 'Last/Est'
                    })

        except Exception as e:
            continue

    # ==========================================
    # 输出诊断与结果
    # ==========================================
    print("\n" + "="*60)
    print("📉 FILTRATION DIAGNOSTICS")
    print("="*60)
    total = sum(rejection_stats.values())
    if total > 0:
        for r, c in rejection_stats.items():
            if c > 0: print(f"{r:<35} : {c:5d} ({c/total*100:5.1f}%)")
    else:
        print("No chains processed.")

    if not results:
        print("\n❌ No valid strategies found.")
        return

    df = pd.DataFrame(results)
    df_sorted = df.sort_values(by='EV', ascending=False).head(10)

    print("\n" + "="*120)
    print("🏆 TOP INSTITUTIONAL PICKS (OI Limit Relaxed)")
    print("="*120)
    cols = ['Expiry', 'Width', 'Long', 'Short', 'Debit', 'RoR%', 'PoP%', 'EV', 'IV Skew', 'BE Dist%', 'DataSrc']
    print(df_sorted[cols].to_string(index=False))

    # 策略推荐模块
    print("\n" + "-"*60)
    print("🤖 AI STRATEGY CLASSIFICATION")
    print("-" * 60)
    
    # 查找稳健型
    safe = df[(df['PoP%'] > 60) & (df['BE Dist%'] <= 0.5)].sort_values(by='PoP%', ascending=False).head(1)
    if not safe.empty:
        r = safe.iloc[0]
        print(f"🛡️  [Conservative] {r['Expiry']} ${r['Long']}/{r['Short']} | Cost: ${r['Debit']:.2f} | PoP: {r['PoP%']:.1f}%")
    else:
        print("🛡️  [Conservative] No high-prob setups.")

    # 查找激进型
    agg = df[(df['RoR%'] > 120) & (df['BE Dist%'] > 1.0)].sort_values(by='EV', ascending=False).head(1)
    if not agg.empty:
        r = agg.iloc[0]
        print(f"🚀  [Aggressive]   {r['Expiry']} ${r['Long']}/{r['Short']} | RoR: {r['RoR%']:.0f}% | Target: +{r['BE Dist%']:.1f}%")
    else:
        print("🚀  [Aggressive] No high-reward setups.")

if __name__ == "__main__":
    # 使用 min_open_interest=0 来应对数据缺失
    institutional_screener_robust("META", min_open_interest=0)