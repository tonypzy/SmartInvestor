import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
from py_vollib_vectorized import vectorized_implied_volatility, get_all_greeks

def screen_bull_put_spreads_advanced_ai(
    symbol, 
    spread_widths=[10, 15, 20], 
    min_days=30, 
    max_days=60,
    max_sell_strike=None,  # 限制卖方最高价 (例如 600)
    min_buy_strike=None    # 限制买方最低价 (例如 550)
):
    # 容错处理
    if isinstance(spread_widths, (int, float)):
        spread_widths = [spread_widths]

    pd.set_option('display.max_rows', None)
    pd.set_option('display.width', 1000)
    pd.set_option('display.float_format', '{:.2f}'.format)

    print(f"=== 启动 {symbol} 高级筛选 (含 AI 推荐) ===")
    print(f"宽度: {spread_widths} | 期限: {min_days}-{max_days}天")
    
    constraints_txt = []
    if max_sell_strike: constraints_txt.append(f"Sell <= ${max_sell_strike}")
    if min_buy_strike: constraints_txt.append(f"Buy >= ${min_buy_strike}")
    print(f"限制: {' | '.join(constraints_txt) if constraints_txt else '无'}")
    
    tk = yf.Ticker(symbol)
    
    try:
        current_price = tk.fast_info.get('last_price', None)
        if not current_price:
            current_price = tk.history(period="1d")['Close'].iloc[-1]
        print(f"当前股价: ${current_price:.2f}\n")
    except:
        return

    all_dates = tk.options
    target_dates = []
    now = datetime.now()
    
    for d_str in all_dates:
        d_date = datetime.strptime(d_str, "%Y-%m-%d")
        days = (d_date - now).days
        if min_days <= days <= max_days:
            target_dates.append((d_str, days))
            
    if not target_dates:
        print("未找到符合日期的期权链。")
        return

    results = []
    risk_free_rate = 0.044 

    print(f"正在扫描 {len(target_dates)} 个到期日...\n")

    for date_str, days in target_dates:
        try:
            chain = tk.option_chain(date_str).puts
            if chain.empty: continue
            
            # 数据清洗
            chain = chain[(chain['bid'] > 0) & (chain['ask'] > 0)].copy()
            chain['mid_price'] = (chain['bid'] + chain['ask']) / 2
            time_to_expiry = days / 365.0
            
            # 计算 Greeks
            chain['iv_raw'] = vectorized_implied_volatility(
                chain['mid_price'], current_price, chain['strike'], time_to_expiry, 
                risk_free_rate, 'p', q=0, return_as='numpy'
            )
            greeks = get_all_greeks(
                'p', current_price, chain['strike'], time_to_expiry, 
                risk_free_rate, chain['iv_raw'], q=0, model='black_scholes', return_as='dict'
            )
            chain['delta'] = greeks['delta']

            # === 筛选卖出腿 ===
            short_candidates = chain[(chain['delta'] > -0.45) & (chain['delta'] < -0.10)].copy()
            
            # 应用最高价限制
            if max_sell_strike is not None:
                short_candidates = short_candidates[short_candidates['strike'] <= max_sell_strike]

            if short_candidates.empty: continue

            # === 匹配买入腿 ===
            for index, short_row in short_candidates.iterrows():
                short_strike = short_row['strike']
                
                for width in spread_widths:
                    target_long_strike = short_strike - width
                    
                    # 应用最低价限制
                    if min_buy_strike is not None and target_long_strike < min_buy_strike:
                        continue

                    long_row = chain[chain['strike'] == target_long_strike]
                    
                    if not long_row.empty:
                        long_row = long_row.iloc[0]
                        net_credit = short_row['mid_price'] - long_row['mid_price']
                        
                        if net_credit <= 0.05: continue
                        
                        max_loss = width - net_credit
                        ror = (net_credit / max_loss) * 100
                        pop = (1 - abs(short_row['delta'])) * 100
                        break_even = short_strike - net_credit
                        buffer_pct = ((current_price - break_even) / current_price) * 100

                        spread_data = {
                            'Expiry': date_str,
                            'Width': width,
                            'Short Put': short_strike,
                            'Long Put': target_long_strike,
                            'S. Delta': round(short_row['delta'], 2),
                            'Credit': net_credit,
                            'RoR%': ror,
                            'Prob%': pop,
                            'Buffer%': buffer_pct
                        }
                        results.append(spread_data)

        except Exception:
            continue

    if not results:
        print("根据您的限制条件，未找到符合的策略。")
        return

    df = pd.DataFrame(results)
    
    # 过滤低回报单
    filtered_df = df[df['RoR%'] >= 8].copy()
    
    # 排序：宽度 -> Delta
    filtered_df = filtered_df.sort_values(by=['Width', 'S. Delta'], ascending=[True, True])

    cols = ['Expiry', 'Width', 'Short Put', 'Long Put', 'S. Delta', 'Credit', 'RoR%', 'Prob%', 'Buffer%']
    
    print("="*110)
    print(f"=== 筛选结果列表 ===")
    print("="*110)
    if filtered_df.empty:
        print("无数据。")
    else:
        print(filtered_df[cols].to_string(index=False))

    # ==========================================
    # 🤖 AI 智能推荐模块 (新增)
    # ==========================================
    print("\n" + "-"*50)
    print(f"🤖 AI 策略推荐 (基于限制条件)")
    print("-" * 50)

    if filtered_df.empty:
        print("无有效数据，无法推荐。")
        return

    # 1. 收益激进型 (Max Yield)
    # 逻辑: 在符合限制的前提下，找 RoR 最高的 (通常 Delta 偏大)
    best_yield = filtered_df.sort_values(by='RoR%', ascending=False).iloc[0]
    print(f"🚀 收益激进型 (High Yield):")
    print(f"   合约: {best_yield['Expiry']} | 宽度 ${best_yield['Width']}")
    print(f"   卖 ${best_yield['Short Put']} / 买 ${best_yield['Long Put']}")
    print(f"   回报: {best_yield['RoR%']:.1f}% | 胜率 ~{best_yield['Prob%']:.0f}%")
    print(f"   警告: 安全垫仅 {best_yield['Buffer%']:.1f}%，需严格止损。")
    print("")

    # 2. 铜墙铁壁型 (Safest)
    # 逻辑: Delta 绝对值最小 (离股价最远) 且 RoR 至少有 10% (不然没意义)
    safe_candidates = filtered_df[filtered_df['RoR%'] >= 10]
    if not safe_candidates.empty:
        # Delta 是负数，越接近 0 (即越大) 越安全 (如 -0.1 > -0.3)
        best_safe = safe_candidates.sort_values(by='S. Delta', ascending=False).iloc[0]
        print(f"🛡️ 铜墙铁壁型 (Safest):")
        print(f"   合约: {best_safe['Expiry']} | 宽度 ${best_safe['Width']}")
        print(f"   卖 ${best_safe['Short Put']} / 买 ${best_safe['Long Put']}")
        print(f"   理由: 极低 Delta ({best_safe['S. Delta']}) + {best_safe['Buffer%']:.1f}% 深厚安全垫")
        print(f"   回报: {best_safe['RoR%']:.1f}% (适合大资金稳健收租)")
    else:
        print("🛡️ 安全型: 未找到符合低风险且回报>10%的组合。")
    print("")

    # 3. 机构均衡型 (Balanced)
    # 逻辑: Delta 在 -0.20 到 -0.30 之间 (机构甜点区)
    # 新增逻辑: Buffer 必须在 5% 到 8% 之间 (防止离现价太近)
    # 排序: 在满足上述条件下，找 RoR 最高的
    balanced = filtered_df[
        (filtered_df['S. Delta'] <= -0.20) & 
        (filtered_df['S. Delta'] >= -0.30) &
        (filtered_df['Buffer%'] >= 5.0) & 
        (filtered_df['Buffer%'] <= 8.0)
    ]
    if not balanced.empty:
        best_bal = balanced.sort_values(by='RoR%', ascending=False).iloc[0]
        print(f"⚖️ 机构均衡型 (Smart Money):")
        print(f"   合约: {best_bal['Expiry']} | 宽度 ${best_bal['Width']}")
        print(f"   卖 ${best_bal['Short Put']} / 买 ${best_bal['Long Put']}")
        print(f"   理由: Delta {best_bal['S. Delta']} 处于最佳风险收益比区间")
        print(f"   回报: {best_bal['RoR%']:.1f}% | 胜率 ~{best_bal['Prob%']:.0f}%")
    else:
        print("⚖️ 均衡型: 您的限制条件可能排除了机构甜点区 (Delta -0.25)，建议放宽价格限制。")

# ==========================================
# 运行示例
# ==========================================
if __name__ == "__main__":
    # 假设场景：
    # Meta 当前约 $633
    # 1. 我认为 $600 是铁底 (max_sell_strike=600)
    # 2. 我不想买太便宜的垃圾期权 (min_buy_strike=580)
    
    screen_bull_put_spreads_advanced_ai(
        "META", 
        spread_widths=[10, 12.5, 15, 17.5, 20], 
        min_days=20, 
        max_days=60,
        max_sell_strike=600, 
        min_buy_strike=585
    )