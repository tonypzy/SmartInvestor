import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
from py_vollib_vectorized import vectorized_implied_volatility, get_all_greeks

def screen_leaps_with_iv(symbol, min_days=300, max_days=530):
    """
    机构级 LEAP 筛选器 (IV 可视化版)
    1. 新增 'IV%' 列：显示期权的隐含波动率。
    2. 依然包含 BreakEven 和 AI 推荐。
    """
    
    # 设置显示格式
    pd.set_option('display.max_rows', None)
    pd.set_option('display.width', 1000)
    pd.set_option('display.float_format', '{:.2f}'.format)

    print(f"=== 启动 {symbol} LEAP 筛选 (含 IV 数据) ===")
    
    tk = yf.Ticker(symbol)
    
    # 1. 获取标的价格
    try:
        current_price = tk.fast_info.get('last_price', None)
        if not current_price:
            current_price = tk.history(period="1d")['Close'].iloc[-1]
        print(f"标的参考价格: ${current_price:.2f}")
    except:
        print("错误：无法获取股价，脚本终止。")
        return

    # 2. 寻找符合 LEAP 定义的日期
    all_dates = tk.options
    target_dates = []
    now = datetime.now()
    
    for d_str in all_dates:
        d_date = datetime.strptime(d_str, "%Y-%m-%d")
        days = (d_date - now).days
        if min_days <= days <= max_days:
            target_dates.append((d_str, days))
            
    if not target_dates:
        print(f"未找到符合天数的期权链。")
        return

    # 3. 批量处理
    results = []
    risk_free_rate = 0.044 

    print(f"正在扫描 {len(target_dates)} 个到期日...\n")

    for date_str, days in target_dates:
        try:
            chain = tk.option_chain(date_str).calls
            if chain.empty: continue
                
            # === 数据处理 ===
            chain['is_stale'] = (chain['bid'] == 0) & (chain['ask'] == 0)
            
            # 价格确定
            chain['mid_price'] = (chain['bid'] + chain['ask']) / 2
            chain['calc_price'] = np.where(chain['mid_price'] > 0, chain['mid_price'], chain['lastPrice'])
            
            # BreakEven
            chain['break_even_price'] = chain['strike'] + chain['calc_price']

            # 计算 Greeks (含 IV)
            time_to_expiry = days / 365.0
            
            # 1. 计算 IV (小数形式，如 0.45)
            chain['iv_raw'] = vectorized_implied_volatility(
                chain['calc_price'], current_price, chain['strike'], time_to_expiry, 
                risk_free_rate, 'c', q=0, return_as='numpy'
            )
            
            # 2. 转换为百分比用于显示 (如 45.00)
            chain['iv_pct'] = chain['iv_raw'] * 100

            # 3. 计算其他 Greeks
            greeks = get_all_greeks(
                'c', current_price, chain['strike'], time_to_expiry, 
                risk_free_rate, chain['iv_raw'], q=0, model='black_scholes', return_as='dict'
            )
            for key, val in greeks.items():
                chain[key] = val

            # 计算机构指标
            chain['leverage'] = (chain['delta'] * current_price) / chain['calc_price']
            chain['premium_pct'] = ((chain['break_even_price'] - current_price) / current_price) * 100
            
            # Spread
            chain['spread_pct'] = np.where(
                chain['ask'] > 0, 
                ((chain['ask'] - chain['bid']) / chain['ask']) * 100, 
                np.nan 
            )

            chain['expiry'] = date_str
            chain['days_left'] = days
            results.append(chain)
            
        except Exception:
            continue

    if not results:
        print("无有效数据。")
        return

    df = pd.concat(results)

    # ==========================================
    # 4. 筛选与排序
    # ==========================================
    
    # 筛选 Delta
    filtered_df = df[(df['delta'] >= 0.65) & (df['delta'] <= 0.92)].copy()

    # 二级排序修复
    filtered_df['delta_rounded'] = filtered_df['delta'].round(2)

    # 排序：Delta(降序) -> IV%(升序) 
    # 注意：这里改成了 IV% 升序。因为在 Delta 相同的情况下，IV 越低越好（越便宜）
    filtered_df = filtered_df.sort_values(
        by=['delta_rounded', 'iv_pct'], 
        ascending=[False, True]
    )

    # ==========================================
    # 5. 展示结果
    # ==========================================
    
    cols = [
        'expiry', 'strike', 
        'calc_price', 'break_even_price', 
        'is_stale', 'delta', 
        'iv_pct',      # <--- 加上了 IV
        'premium_pct', 'leverage',    
        'spread_pct', 'volume', 'openInterest' 
    ]
    
    display_df = filtered_df[cols].rename(columns={
        'calc_price': 'Price',
        'break_even_price': 'BreakEven', 
        'is_stale': 'AfterHrs?',
        'iv_pct': 'IV%',        # 显示为 IV%
        'premium_pct': 'Prem%',
        'leverage': 'Lev(x)',
        'spread_pct': 'Spread%'
    })

    print("\n" + "="*120)
    print(f"=== {symbol} LEAP 筛选报告 (含隐含波动率 IV) ===")
    print(f"标的价格: ${current_price:.2f}")
    print("IV% 越低越好 (代表期权便宜)")
    print("="*120)

    if display_df.empty:
        print("没有符合条件的期权。")
    else:
        print(display_df.to_string(index=False))

    # ==========================================
    # 6. AI 智能推荐 (修复版)
    # ==========================================
    print("\n" + "-"*40)
    print("🤖 AI 策略推荐 (加入 IV 分析)")
    print("-" * 40)

    # 1. 寻找最佳性价比 (Sweet Spot)
    display_df['delta_dist'] = abs(display_df['delta'] - 0.80)
    
    # [修复点 1] 这里要用重命名后的 'IV%' 进行排序
    best_sweet_spot = display_df.sort_values(by=['delta_dist', 'IV%']).iloc[0]

    print(f"★ 机构甜蜜点 (Sweet Spot):")
    print(f"   合约: {best_sweet_spot['expiry']} | 行权价 ${best_sweet_spot['strike']}")
    print(f"   理由: Delta {best_sweet_spot['delta']}，且 IV ({best_sweet_spot['IV%']:.2f}%) 相对较低")
    print(f"   价格: ${best_sweet_spot['Price']:.2f} | 回本需涨: {best_sweet_spot['Prem%']:.2f}%")

    # 2. 寻找最安全 (Safety First)
    safe_bets = display_df[display_df['delta'] >= 0.85]
    if not safe_bets.empty:
        # [修复点 2] 这里也要改成 'IV%'
        best_safe = safe_bets.sort_values(by='IV%').iloc[0]
        print(f"\n🛡️ 防御型首选 (Safety):")
        print(f"   合约: {best_safe['expiry']} | 行权价 ${best_safe['strike']}")
        print(f"   理由: 深度实值 (Delta {best_safe['delta']}) + 低波动率 ({best_safe['IV%']:.2f}%)")
        print(f"   价格: ${best_safe['Price']:.2f} | 回本需涨: {best_safe['Prem%']:.2f}%")

# 运行
if __name__ == "__main__":
    screen_leaps_with_iv("AVGO")