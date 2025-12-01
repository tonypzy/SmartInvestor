import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
from py_vollib_vectorized import vectorized_implied_volatility, get_all_greeks

# === 界面美化设置 ===
pd.set_option('display.width', None)       # 自动适应屏幕宽度
pd.set_option('display.max_columns', 20)   # 允许显示更多列
pd.set_option('display.float_format', '{:.2f}'.format)

def screen_double_bull_spread_final(
    symbol, 
    max_put_strike,      # 你的"铁底"
    min_call_strike,     # 你的"目标顶"
    put_width=15,        # 保护宽度
    min_days=45, 
    max_days=90
):
    print(f"\n{'='*80}")
    print(f"🚀 {symbol} 机构策略筛选器 (最终修复版)")
    print(f"🎯 参数: 底 ${max_put_strike} | 顶 ${min_call_strike} | 宽 ${put_width}")
    print(f"{'='*80}\n")

    tk = yf.Ticker(symbol)
    
    try:
        current_price = tk.history(period="1d")['Close'].iloc[-1]
        print(f"📊 当前股价: ${current_price:.2f}")
    except:
        print("无法获取股价数据")
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
        print("❌ 未找到符合日期的期权链")
        return

    results = []
    risk_free_rate = 0.044 

    print(f"🔄 正在扫描 {len(target_dates)} 个到期日...\n")

    for date_str, days in target_dates:
        try:
            opts = tk.option_chain(date_str)
            calls = opts.calls.copy()
            puts = opts.puts.copy()
            if calls.empty or puts.empty: continue

            time_to_expiry = days / 365.0
            
            # 简化 Greeks 计算
            puts = puts[(puts['bid'] > 0) & (puts['ask'] > 0)]
            puts['mid'] = (puts['bid'] + puts['ask']) / 2
            puts['iv'] = vectorized_implied_volatility(puts['mid'], current_price, puts['strike'], time_to_expiry, risk_free_rate, 'p', q=0, return_as='numpy')
            greeks_p = get_all_greeks('p', current_price, puts['strike'], time_to_expiry, risk_free_rate, puts['iv'], q=0, model='black_scholes', return_as='dict')
            puts['delta'] = greeks_p['delta']

            calls = calls[(calls['bid'] > 0) & (calls['ask'] > 0)]
            calls['mid'] = (calls['bid'] + calls['ask']) / 2
            
            # --- 策略构建 ---
            short_put_candidates = puts[puts['strike'] <= max_put_strike]
            
            for _, sp_row in short_put_candidates.iterrows():
                short_put_strike = sp_row['strike']
                short_put_price = sp_row['mid']
                
                long_put_strike = short_put_strike - put_width
                lp_row = puts[puts['strike'] == long_put_strike]
                if lp_row.empty: continue
                long_put_price = lp_row.iloc[0]['mid']
                
                put_spread_credit = short_put_price - long_put_price
                if put_spread_credit <= 0: continue

                short_call_candidates = calls[calls['strike'] >= min_call_strike]
                
                for _, sc_row in short_call_candidates.iterrows():
                    short_call_strike = sc_row['strike']
                    short_call_price = sc_row['mid']
                    
                    total_budget = put_spread_credit + short_call_price
                    
                    potential_long_calls = calls[
                        (calls['mid'] <= total_budget) & 
                        (calls['strike'] < short_call_strike) &
                        (calls['strike'] > current_price) 
                    ].sort_values(by='strike', ascending=True)
                    
                    if potential_long_calls.empty: continue
                    
                    lc_row = potential_long_calls.iloc[0]
                    long_call_strike = lc_row['strike']
                    long_call_price = lc_row['mid']
                    
                    # === 计算核心指标 ===
                    net_credit = total_budget - long_call_price
                    collateral = put_width * 100
                    
                    call_spread_width = short_call_strike - long_call_strike
                    max_profit = (call_spread_width * 100) + (net_credit * 100)
                    real_max_loss = collateral - (net_credit * 100)

                    # === 关键修正：这里的 Key 必须和下面的 cols 完全一致 ===
                    results.append({
                        'Expiry': date_str,
                        'Days': days,
                        'BuyPut': int(long_put_strike),   # 修正为短名字
                        'SellPut': int(short_put_strike), # 修正为短名字
                        'BuyCall': int(long_call_strike), # 修正为短名字
                        'SellCall': int(short_call_strike),# 修正为短名字
                        'Credit': net_credit,             # 修正为短名字
                        'MaxLoss': real_max_loss,         # 修正为短名字
                        'MaxProfit': max_profit,          # 修正为短名字
                        'Margin': collateral,             # 修正为短名字
                        'P.Delta': sp_row['delta'],
                        'Start': long_call_strike         # 修正为短名字
                    })

        except Exception:
            continue

    if not results:
        print("未找到符合条件的策略。")
        return

    df = pd.DataFrame(results)
    df = df[df['Credit'] >= -0.10] 
    df = df.sort_values(by=['Start', 'MaxProfit'], ascending=[True, False])
    
    # 这里的名字现在和上面的 Key 是一一对应的了
    cols = ['Expiry', 'BuyPut', 'SellPut', 'BuyCall', 'SellCall', 
            'Credit', 'MaxProfit', 'MaxLoss', 'Margin', 'P.Delta', 'Start']
    
    print(f"✅ 筛选完成！共找到 {len(df)} 个策略。")
    print("-" * 100)
    print(df[cols].head(15).to_string(index=False))
    print("-" * 100)

    # 辅助打印函数 (也修正为使用短名字)
    def print_ticket(row, strategy_name, reason):
        print(f"🎫 {strategy_name}")
        print(f"   理由: {reason}")
        print(f"   合约: {row['Expiry']}")
        print(f"   ----------------------------------------------------")
        print(f"   1. Buy  Put  ${row['BuyPut']}")
        print(f"   2. Sell Put  ${row['SellPut']}")
        print(f"   3. Buy  Call ${row['BuyCall']}")
        print(f"   4. Sell Call ${row['SellCall']}")
        print(f"   ----------------------------------------------------")
        print(f"   💰 净收支:   ${row['Credit']:.2f}")
        print(f"   📉 最大亏损: ${row['MaxLoss']:.0f} (若股价跌破 {row['BuyPut']})")
        print(f"   📈 最大利润: ${row['MaxProfit']:.0f} (若股价涨破 {row['SellCall']})")
        print(f"   🎲 盈亏比:   1 : {row['MaxProfit']/row['MaxLoss']:.1f}")
        print("\n")

    print("\n🤖 AI 策略点评")
    print("=" * 60)

    if not df.empty:
        best_attack = df.iloc[0]
        print_ticket(best_attack, "🚀 最佳进攻型", f"起涨点最低 (${best_attack['Start']})，最容易获利。")

        best_reward = df.sort_values(by='MaxProfit', ascending=False).iloc[0]
        print_ticket(best_reward, "💰 最高赔率型", f"潜在利润最大 (${best_reward['MaxProfit']:.0f})。")

# ==========================================
# 运行脚本
# ==========================================
if __name__ == "__main__":
    screen_double_bull_spread_final(
        symbol="VST", 
        max_put_strike=150,     
        min_call_strike=225,    
        put_width=10,           
        min_days=60,            
        max_days=100
    )