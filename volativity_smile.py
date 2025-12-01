import yfinance as yf
import matplotlib.pyplot as plt
import pandas as pd
import os

def analyze_option_iv(ticker_symbol, num_expirations=3, export_csv=True):
    """
    获取特定股票的期权链，绘制IV曲线，并导出数据到控制台和CSV。
    
    参数:
    ticker_symbol (str): 股票代码，例如 'SLV'
    num_expirations (int): 要抓取的最近到期日数量
    export_csv (bool): 是否保存为CSV文件
    """
    
    # 1. 获取股票对象
    stock = yf.Ticker(ticker_symbol)
    
    # 2. 获取所有可用的期权到期日
    try:
        expirations = stock.options
    except Exception as e:
        print(f"Error fetching options for {ticker_symbol}: {e}")
        return

    if not expirations:
        print(f"未找到 {ticker_symbol} 的期权数据。")
        return

    print(f"--- 正在分析 {ticker_symbol} ---")
    print(f"发现到期日: {expirations[:num_expirations]}")

    # 用于存储所有数据的列表
    all_iv_data = []

    # 设置绘图
    plt.figure(figsize=(12, 8))
    
    # 获取当前股价（用于在图上标记）
    try:
        hist = stock.history(period='1d')
        if not hist.empty:
            current_price = hist['Close'].iloc[-1]
            plt.axvline(x=current_price, color='black', linestyle='--', alpha=0.5, label=f'Current Price: ${current_price:.2f}')
        else:
            current_price = None
    except:
        current_price = None

    # 3. 循环获取特定到期日的数据
    for date in expirations[:num_expirations]:
        try:
            print(f"正在抓取到期日: {date}...")
            # 获取期权链数据
            opt_chain = stock.option_chain(date)
            calls = opt_chain.calls
            
            # --- 数据清洗与过滤 ---
            # 过滤掉成交量为0或IV明显错误的合约，以保证图表清晰
            # 这里的阈值可以根据需要调整，例如 volume > 10
            valid_calls = calls[(calls['impliedVolatility'] > 0.001) & (calls['volume'] > 0)].copy()
            
            if valid_calls.empty:
                print(f"  警告: {date} 没有符合条件的Call期权数据。")
                continue

            # --- 收集数据用于导出 ---
            for index, row in valid_calls.iterrows():
                all_iv_data.append({
                    'Ticker': ticker_symbol,
                    'Expiration': date,
                    'Type': 'Call',
                    'Strike': row['strike'],
                    'ImpliedVolatility': row['impliedVolatility'],
                    'LastPrice': row['lastPrice'],
                    'Volume': row['volume'],
                    'OpenInterest': row['openInterest']
                })

            # --- 绘制曲线 (Call Options) ---
            plt.plot(valid_calls['strike'], valid_calls['impliedVolatility'], 
                     label=f'Exp: {date}', linestyle='-', marker='o', markersize=4, alpha=0.8)

        except Exception as e:
            print(f"无法获取日期 {date} 的数据: {e}")

    # 4. 图表美化
    plt.title(f'{ticker_symbol} Implied Volatility Surface (Call Options)', fontsize=16)
    plt.xlabel('Strike Price ($)', fontsize=12)
    plt.ylabel('Implied Volatility (Decimal)', fontsize=12)
    plt.grid(True, which='both', linestyle='--', linewidth=0.5)
    plt.legend()
    
    # 智能限制X轴范围：集中在当前价格上下 40% 的区域，避免深实值/深虚值拉长图表
    if current_price:
        plt.xlim(current_price * 0.6, current_price * 1.4)
        
    plt.tight_layout()
    plt.show()

    # 5. 数据处理与输出
    if all_iv_data:
        # 转换为 DataFrame
        df = pd.DataFrame(all_iv_data)
        
        # --- 输出到控制台 ---
        print("\n" + "="*50)
        print(f"{ticker_symbol} IV 数据概览 (前15行):")
        print("="*50)
        # 格式化打印：IV保留4位小数，价格保留2位
        pd.set_option('display.max_rows', 20)
        print(df.head(15))
        print(f"\n... 总计获取 {len(df)} 条合约数据...")

        # --- 输出到CSV ---
        if export_csv:
            filename = f"{ticker_symbol}_iv_data.csv"
            df.to_csv(filename, index=False)
            print(f"\n[成功] 所有数据已保存至文件: {os.path.abspath(filename)}")
            print("CSV 包含列: Expiration, Strike, ImpliedVolatility, LastPrice, Volume, OpenInterest")
    else:
        print("未收集到有效数据。")

# --- 执行脚本 ---
# 分析 SLV，抓取最近 4 个到期日的数据
analyze_option_iv('SLV', num_expirations=4)