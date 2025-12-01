import pandas as pd
import seaborn as sns

def find_best_skew_trade(csv_path, 
                         long_range=(0.55, 0.65), 
                         short_range=(0.25, 0.35)):
    """
    全自动寻找最佳 Skew 和 成本效率的组合
    """
    # 1. 读取并清洗数据
    df = pd.read_csv(csv_path)
    # 清洗货币符号
    for col in ['Strike', 'Mark', 'IV', 'Delta']:
        if col in df.columns and df[col].dtype == object:
            df[col] = df[col].astype(str).str.replace(r'[$,%]', '', regex=True).astype(float)
    
    # 标准化
    if 'IV' in df.columns: df['IV'] = df['IV'] / 100.0
    if 'Delta' in df.columns: df['Abs_Delta'] = df['Delta'].abs()
    
    # 2. 筛选合格池
    long_pool = df[(df['Abs_Delta'] >= long_range[0]) & (df['Abs_Delta'] <= long_range[1])]
    short_pool = df[(df['Abs_Delta'] >= short_range[0]) & (df['Abs_Delta'] <= short_range[1])]
    
    results = []
    
    # 3. 遍历计算
    for _, long in long_pool.iterrows():
        for _, short in short_pool.iterrows():
            if long['Strike'] < short['Strike']: # 确保是 Bull Call
                
                width = short['Strike'] - long['Strike']
                debit = long['Mark'] - short['Mark']
                
                # 计算核心指标
                trade = {
                    'Long_Strike': long['Strike'],
                    'Short_Strike': short['Strike'],
                    'Skew': short['IV'] - long['IV'],         # 越高越好
                    'Cost_Ratio': debit / width,              # 越低越好
                    'ROI': (width - debit) / debit,           # 越高越好
                    'Long_Delta': long['Abs_Delta'],
                    'Short_Delta': short['As_Delta']
                }
                results.append(trade)
    
    # 4. 排序并展示 (按 Skew 降序)
    df_res = pd.DataFrame(results).sort_values(by='Skew', ascending=False)
    
    # 格式化输出
    print(f"\n🏆 Top 5 最佳 Skew 策略 (Delta Long {long_range} / Short {short_range})")
    print("-" * 80)
    print(df_res[['Long_Strike', 'Short_Strike', 'Skew', 'Cost_Ratio', 
                  'Long_Delta', 'Short_Delta', 'ROI']].head(5).to_string(index=False, float_format="%.4f"))

# 运行
find_best_skew_trade('meta.csv')