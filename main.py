from InstitutionalEngine import InstitutionalEngine

engine = InstitutionalEngine('AVGO')

# 设置：每个日期展示最多3个方案
IS_PROTECTED = True 

df_report = engine.scan_seagull_range(
    min_dte=30, 
    max_dte=80, 
    force_zero_cost=False,
    min_buffer=0.08,
    protected=IS_PROTECTED
)

if not df_report.empty:
    print("\n" + "="*125)
    # 表头：增加了 ROMR
    header = f"{'Expiration':<12} | {'DTE':<4} | {'Net Prem':>8} | {'Ann Ret':>9} | {'Win Prob':>8} | {'ROMR':>6} | {'Buffer':>6} | {'Strikes'}"
    print(header)
    print("-" * 125)
    for _, row in df_report.iterrows():
        # 根据模式拼接行权价字符串
        if IS_PROTECTED:
            strikes = f"{row['K0_Strike']:.0f}/{row['K1_Strike']:.0f}/{row['K2_Strike']:.0f}/{row['K3_Strike']:.0f}"
        else:
            strikes = f"{row['K1_Strike']:.0f}/{row['K2_Strike']:.0f}/{row['K3_Strike']:.0f}"
            
        # 对应表头打印数据
        print(f"{row['Expiration']:<12} | {row['DTE']:<4} | {row['Net_Premium']:>8.2f} | "
              f"{row['Annual_Return']*100:>8.1f}% | {row['Win_Rate']*100:>7.1f}% | "
              f"{row['ROMR']:>6.2f} | {row['Buffer']*100:>5.1f}% | {strikes}")
    print("="*125)
    
    # 绘图第一个（Score最高）
    best_exp = df_report.iloc[0]['Expiration']
    res, metrics = engine.select_protected_seagull(best_exp) if IS_PROTECTED else engine.select_seagull_pro(best_exp)
    engine.plot_payoff(res, metrics)
else:
    print("范围内未找到有效策略。")