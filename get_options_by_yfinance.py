import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
# 引入向量化计算库，用于快速计算 IV 和 Greeks
from py_vollib_vectorized import vectorized_implied_volatility, get_all_greeks

def get_option_data(symbol, target_date=None):
    """
    获取指定股票在指定日期的期权链数据，并计算 IV 和希腊字母。
    """
    
    # 1. 创建 Ticker 对象
    stock = yf.Ticker(symbol)
    
    # 2. 获取所有可用的行权日
    avail_dates = stock.options
    
    if not avail_dates:
        print(f"错误: 无法获取 {symbol} 的期权日期，请检查股票代码是否正确。")
        return None, None

    # 3. 日期处理
    if target_date is None:
        target_date = avail_dates[0]
        print(f"未指定日期，默认使用: {target_date}")
    elif target_date not in avail_dates:
        print(f"错误: 日期 {target_date} 不在可选列表中。")
        print(f"可选日期: {avail_dates}")
        return None, None

    # ==========================================
    # 准备计算所需的参数
    # ==========================================
    print(f"正在获取 {symbol} 数据及 {target_date} 的期权链...")
    
    # A. 获取标的当前价格 (S)
    try:
        # 尝试获取实时价格，如果失败则获取昨日收盘价
        history = stock.history(period="1d")
        if not history.empty:
            underlying_price = history['Close'].iloc[-1]
        else:
            # 备用方案：通过 fast_info 获取
            underlying_price = stock.fast_info.get('last_price', None)
        
        if underlying_price is None:
            raise ValueError("无法获取当前股价")
            
        print(f"当前标的价格 ({symbol}): {underlying_price:.2f}")
    except Exception as e:
        print(f"获取股价失败: {e}")
        return None, None

    # B. 计算距离到期时间 (T, 年化)
    expiry = pd.to_datetime(target_date) + pd.Timedelta(hours=16) # 假设收盘时间
    now = pd.Timestamp.now()
    days_to_expiry = (expiry - now).days
    
    # 防止过期或当日到期导致除以0
    if days_to_expiry <= 0:
        time_to_expiry = 0.001 
    else:
        time_to_expiry = days_to_expiry / 365.0

    # C. 无风险利率 (r) - 这里硬编码为 4.4% (0.044)，可根据美债收益率调整
    risk_free_rate = 0.044

    # ==========================================
    # 定义计算核心逻辑函数
    # ==========================================
    def process_chain(df, flag):
        if df.empty:
            return df
        
        # 1. 确定计算用的价格 (User Logic)
        # 如果 bid 和 ask 都有值，用中间价；否则用 lastPrice
        # 创建一个临时列 'calc_price'
        df['mid_price'] = (df['bid'] + df['ask']) / 2
        
        # 使用 np.where 实现条件逻辑：如果 mid_price > 0 用 mid_price，否则用 lastPrice
        df['calc_price'] = np.where(df['mid_price'] > 0, df['mid_price'], df['lastPrice'])
        
        # 标记数据来源，方便查看
        df['price_source'] = np.where(df['mid_price'] > 0, 'Mid', 'Last')

        # 2. 计算隐含波动率 (IV)
        # py_vollib_vectorized 可以处理 pandas Series
        df['calc_IV'] = vectorized_implied_volatility(
            df['calc_price'],       # 期权价格
            underlying_price,       # 标的价格
            df['strike'],           # 行权价
            time_to_expiry,         # 剩余时间
            risk_free_rate,         # 无风险利率
            flag,                   # 'c' for Call, 'p' for Put
            q=0,                    # 股息率 (简化为0)
            return_as='numpy'       # 返回 numpy 数组
        )

        # 3. 计算希腊字母 (Greeks)
        greeks = get_all_greeks(
            flag,
            underlying_price,
            df['strike'],
            time_to_expiry,
            risk_free_rate,
            df['calc_IV'],          # 使用刚才算出来的 IV
            q=0,
            model='black_scholes',
            return_as='dict'
        )

        # 将结果合并入 DataFrame
        for key, value in greeks.items():
            df[key] = value
            
        return df

    # ==========================================
    # 获取数据并处理
    # ==========================================
    try:
        opt = stock.option_chain(target_date)
        calls = opt.calls.copy()
        puts = opt.puts.copy()

        # 计算 Calls
        calls = process_chain(calls, 'c')
        # 计算 Puts
        puts = process_chain(puts, 'p')

        # ==========================================
        # 展示设置
        # ==========================================
        # 定义要显示的列 (新增了 Greeks 和 calc_IV)
        columns_to_show = [
            'contractSymbol', 'strike', 'lastPrice', 'bid', 'ask', 
            'price_source', 'calc_IV', 'delta', 'gamma', 'theta', 'vega'
        ]
        
        pd.set_option('display.max_rows', None)
        pd.set_option('display.width', 1000)
        pd.set_option('display.float_format', '{:.4f}'.format) # 设置小数精度

        # 设定筛选范围：当前股价的 +/- 20%
        lower_bound = underlying_price * 0.5
        upper_bound = underlying_price * 1.5
        
        # 筛选 Calls
        calls_filtered = calls[
            (calls['strike'] >= lower_bound) & 
            (calls['strike'] <= upper_bound)
        ]

        # 筛选 Puts
        puts_filtered = puts[
            (puts['strike'] >= lower_bound) & 
            (puts['strike'] <= upper_bound)
        ]
        print(f"\n=== 看涨期权 (Calls) [S={underlying_price:.2f}] (只显示行权价 {lower_bound:.1f}-{upper_bound:.1f}) ===")
        if not calls_filtered.empty:
            print(calls_filtered[columns_to_show].dropna(subset=['calc_IV']).to_string(index=False))
        
        print(f"\n=== 看跌期权 (Puts) [S={underlying_price:.2f}] (只显示行权价 {lower_bound:.1f}-{upper_bound:.1f}) ===")
        if not puts_filtered.empty:
            print(puts_filtered[columns_to_show].dropna(subset=['calc_IV']).to_string(index=False))

    except Exception as e:
        print(f"处理数据时发生错误: {e}")
        import traceback
        traceback.print_exc()
        return None, None

# ==========================================
# 主程序入口
# ==========================================
if __name__ == "__main__":
    ticker_symbol = "HOOD" 
    expiration_date = "2025-11-28" 
    
    calls_df, puts_df = get_option_data(ticker_symbol, expiration_date)
    
    # 如果你想保存到 CSV 查看完整数据
    if calls_df is not None:
        calls_df.to_csv(f"{ticker_symbol}_calls_greeks.csv")
        print(f"\n数据已保存至 {ticker_symbol}_calls_greeks.csv")