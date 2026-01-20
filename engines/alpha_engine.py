import pandas as pd

class Alpha_Engine:
    @staticmethod
    def derive_q4_metrics(filings_list):
        """
        [修复版] 自适应倒推 Q4
        自动解决 Revenue (通常是单季) 和 Cash Flow (通常是累积) 的数据口径冲突
        """
        latest = filings_list[0]
        if latest.get('Source') != '10-K' or len(filings_list) < 4:
            return None
        
        q3 = filings_list[1]
        q2 = filings_list[2]
        q1 = filings_list[3]
        
        print(f"🧮 Deriving Q4 Data from 10-K ({latest.get('Period End Date')})...")

        q4_derived = latest.copy()
        q4_derived['Source'] = '10-Q (Derived)'
        q4_derived['Source Type'] = '10-Q'
        
        flow_metrics = ['Revenue', 'COGS', 'Operating Income', 'Net Income', 'Operating Cash Flow', 'CapEx', 'Buybacks', 'Dividends']
        
        for m in flow_metrics:
            val_10k = latest.get(m, 0)
            
            # 1. 尝试“离散扣减法” (Discrete Subtraction)
            # 假设 Q1, Q2, Q3 都是单季数据 (适用于 Revenue/Income)
            sum_discrete = q3.get(m, 0) + q2.get(m, 0) + q1.get(m, 0)
            derived_discrete = val_10k - sum_discrete
            
            # 2. 尝试“累积扣减法” (YTD Subtraction)
            # 假设 Q3 是前9个月累积数据 (适用于 Cash Flow)
            val_q3_ytd = q3.get(m, 0)
            derived_ytd = val_10k - val_q3_ytd
            
            # --- 智能决策核心 ---
            # 如果 10K 是正数，但“离散法”算出了负数，说明肯定扣多了（遇到了 YTD 陷阱）
            # 这时候强制使用“累积法”
            if val_10k > 0 and derived_discrete < 0:
                final_val = derived_ytd
                # 调试打印，让你知道它对 Cash Flow 做了特殊处理
                if m == 'Operating Cash Flow':
                    print(f"   🔧 Detected YTD Cash Flow. Adjusted: {val_10k:,.0f} - {val_q3_ytd:,.0f} = {final_val:,.0f}")
            else:
                # 否则默认使用离散法（ Revenue 通常走这里）
                final_val = derived_discrete

            q4_derived[m] = final_val
            
        return q4_derived

    @staticmethod
    def process_time_series(ticker, fundamentals_list, market_data):
        """
        [新增] 时间序列引擎：提取过去 N 个季度的核心指标走势
        """
        if not fundamentals_list: return None
        
        history_data = []
        current_mkt_cap = market_data['Market Cap']
        
        print(f"📉 Building historical trend for {ticker} over {len(fundamentals_list)} filings...")

        for filing in fundamentals_list:
            try:
                # 1. 确定年化系数 (10-K vs 10-Q)
                # 注意：这里我们做简化处理，直接用 Filing 的类型来决定 Run Rate
                # 这样可以在不进行复杂的 Q4 倒推情况下，快速画出趋势线
                source = filing.get('Source', '10-Q')
                af = 1.0 if '10-K' in source else 4.0
                
                # 2. 提取并年化核心数据
                rev = filing.get('Revenue', 0) * af
                cogs = filing.get('COGS', 0) * af
                ocf = filing.get('Operating Cash Flow', 0) * af
                capex = filing.get('CapEx', 0) * af
                
                # 3. 计算比率
                if rev == 0: continue
                
                gross_margin = (rev - cogs) / rev
                fcf = ocf - capex
                
                # FCF Yield (使用当前市值做分母，观察“盈利能力变化”对当前估值的贡献)
                # 这回答了：如果是以前的盈利能力，现在的股价算便宜吗？
                fcf_yield = fcf / current_mkt_cap if current_mkt_cap else 0
                
                history_data.append({
                    'Date': filing.get('Period End Date'),
                    'Source': source,
                    'Gross Margin': gross_margin,
                    'FCF Yield': fcf_yield
                })
                
            except Exception as e:
                continue
                
        # 转为 DataFrame
        df = pd.DataFrame(history_data)
        return df

    @staticmethod
    def process_analysis(ticker, fundamentals_list, market_data):
        if not fundamentals_list: return None
        
        curr = fundamentals_list[0]
        prev = None 
        
        # --- 1. 智能路由与数据归一化 (Normalization) ---
        # 目标：无论输入是什么，最终都把 curr 变成“单季度量级”
        
        # 情况 A: 最新的是 10-K -> 尝试倒推 Q4
        is_derived_q4 = False
        if curr.get('Source') == '10-K':
            q4_derived = Alpha_Engine.derive_q4_metrics(fundamentals_list) # 调用之前的倒推函数
            if q4_derived:
                # 成功！用 Q4 替换掉 10-K 成为当前分析对象
                curr = q4_derived
                prev = fundamentals_list[1] # Q3
                is_derived_q4 = True
                print(f"🔄 Switched mode: Analyzing Implied Q4 vs Q3 ({prev.get('Period End Date')})")
            else:
                # 失败（可能缺少历史Q），回退到年报分析
                print("⚠️ Q4 derivation failed. Fallback to Annual Analysis.")
                # 寻找上一年的 10-K 做对比
                for f in fundamentals_list[1:]:
                    if f.get('Source') == '10-K':
                        prev = f
                        break
    
        # 情况 B: 最新的是 10-Q
        else:
            if len(fundamentals_list) > 1:
                prev = fundamentals_list[1]
                print(f"🔎 Analyzing Q{curr.get('Source')} vs Previous Quarter")
    
        # --- 2. 统一计算逻辑 ---
        
        # 关键点：确定年化系数 (AF)
        # 如果是 Derived Q4 或者 原生 10-Q，系数都是 4.0
        # 只有在倒推失败回退到年报(10-K)模式时，系数才是 1.0
        af = 1.0 if (curr.get('Source') == '10-K' and not is_derived_q4) else 4.0
    
        # 流量数据 (Flows) -> 年化
        revenue_run_rate = curr['Revenue'] * af
        net_income_run_rate = curr['Net Income'] * af
        op_cash_flow_run_rate = curr['Operating Cash Flow'] * af # 注意：现金流也要年化才能算 Yield
        
        # 存量数据 (Stocks) -> 不动
        # 资产负债表永远取最新的快照
        total_debt = curr.get('Long Term Debt', 0) + curr.get('Short Term Debt', 0)
        cash = curr['Cash']
    
        # --- 3. 高阶比率计算 ---
        
        # 环比增长 (QoQ / YoY)
        sequential_growth = 0.0
        if prev and prev.get('Revenue', 0) > 0:
            sequential_growth = (curr['Revenue'] - prev['Revenue']) / prev['Revenue']
    
        # 毛利率
        gross_margin = (curr['Revenue'] - curr['COGS']) / curr['Revenue'] if curr['Revenue'] else 0
        
        # 毛利率变化 (Margin Expansion)
        margin_expansion = 0.0
        if prev:
            prev_margin = (prev['Revenue'] - prev['COGS']) / prev['Revenue'] if prev['Revenue'] else 0
            margin_expansion = (gross_margin - prev_margin) * 100 # basis points
    
        # FCF (单季)
        fcf_quarterly = curr['Operating Cash Flow'] - curr['CapEx']
    
        # 估值 (Valuation)
        mkt_cap = market_data['Market Cap']
        ev = mkt_cap + total_debt - cash
        
        # 估值倍数 (分母必须是年化的 Run Rate)
        pe = mkt_cap / net_income_run_rate if net_income_run_rate else 0
        
        # FCF Yield = (单季FCF * 4) / 市值
        fcf_yield = (fcf_quarterly * af) / mkt_cap if mkt_cap else 0
        ev_ebit = ev / (curr['Operating Income'] * af) if curr.get('Operating Income') else 0
    
        # --- [新增] ROIC 计算 (Quality Metric) ---
        # 1. 计算 NOPAT (Net Operating Profit After Tax)
        # 我们假设有效税率为 21% (美国企业税率)
        op_income_run_rate = curr.get('Operating Income', 0) * af
        nopat = op_income_run_rate * (1 - 0.21)
        
        # 2. 计算投入资本 (Invested Capital)
        # 公式：总债务 + 股东权益 - 现金
        # 逻辑：这是公司实际“占用”的资金
        equity = curr.get('Stockholders Equity', 0)
        invested_capital = total_debt + equity - cash
        
        # 3. 计算 ROIC
        # 只有当投入资本为正时才有意义
        roic = nopat / invested_capital if invested_capital and invested_capital > 0 else 0
    
        # --- [新增] 资本回报与风险定价 (Capital Allocation & CAPM) ---
        
        # A. 股东回报 (Shareholder Yield)
        # Buybacks 和 Dividends 也是流量数据，需要年化 (Run Rate)
        buyback_run_rate = curr.get('Buybacks', 0) * af
        dividend_run_rate = curr.get('Dividends', 0) * af
        
        # 计算 Yield (相对于市值)
        buyback_yield = buyback_run_rate / mkt_cap if mkt_cap else 0
        dividend_yield = dividend_run_rate / mkt_cap if mkt_cap else 0
        total_shareholder_yield = buyback_yield + dividend_yield
    
        # B. 权益成本 (Cost of Equity - CAPM Model)
        # Ke = RiskFree + Beta * (Market Return - RiskFree)
        # 我们假设市场风险溢价 (Market Risk Premium) 为 5.0%
        beta = market_data.get('Beta', 1.0)
        if beta is None: beta = 1.0 # 默认 Beta 为 1
        
        rfr = market_data.get('Risk-Free Rate', 0.045)
        cost_of_equity = rfr + (beta * 0.05) 
        
        # C. 经济增加值 (EVA Spread)
        eva_spread = roic - cost_of_equity
    
        # --- [新增] Reverse DCF (反向定价) ---
        # 核心逻辑：市场当前价格暗示了未来的增长率是多少？
        # 如果 FCF Yield (5%) < Cost of Equity (9%)，说明市场依然期待 4% 的增长来补足回报
        # Implied Growth = Cost of Equity - FCF Yield
        implied_growth = cost_of_equity - fcf_yield
        
        # 计算 "Alpha Gap" (预期差)
        # 简单的用近期增长率 - 市场隐含增长率
        # 如果 Gap > 0，说明公司实际增长快于市场预期 -> 低估 (Undervalued)
        # 注意：这里我们用 Sequential Growth 近似，严谨点可以用 3年 CAGR
        alpha_gap = sequential_growth - implied_growth
    
        # --- 新增：宏观估值调整 ---
        erp = fcf_yield - rfr
    
        return {
            # --- 基础元数据 (之前丢失的部分) ---
            "Report Date": curr.get('Period End Date'),
            "Report Source": curr.get('Source Type', curr.get('Source')),
            "Real-time Price": market_data['Price'],
            "Market Cap": mkt_cap,
            "Enterprise Value (EV)": ev,
    
            # --- [新增] 把定价指标加进返回字典 ---
            "Implied Growth": implied_growth,
            "Alpha Gap": alpha_gap,
            
            # --- 核心指标 ---
            "Revenue (Run Rate)": revenue_run_rate,
            "Sequential Growth": sequential_growth,
            "Gross Margin": gross_margin,
            "Margin Expansion": margin_expansion,
            
            # --- 估值与质量 ---
            "P/E Ratio": pe,
            "FCF Yield": fcf_yield,
            "EV/EBIT": ev_ebit,
            "ROIC": roic,
            
            # --- 宏观 ---
            "Risk-Free Rate": rfr,
            "Equity Risk Premium (ERP)": erp,
    
            # --- [新增] 把新指标加进返回字典 ---
            "Buyback Yield": buyback_yield,
            "Dividend Yield": dividend_yield,
            "Total Shareholder Yield": total_shareholder_yield,
            "Beta": beta,
            "Cost of Equity (Ke)": cost_of_equity,
            "EVA Spread": eva_spread,
        }
