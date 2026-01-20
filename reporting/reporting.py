class Reporting:
    @staticmethod
    def print_institutional_deck(ticker, metrics):
        def fmt(val, type='usd'):
            if val is None: return "N/A"
            if type == 'usd': return f"${val:,.0f}"
            if type == 'price': return f"${val:,.2f}"
            if type == 'pct': return f"{val:.2%}"
            if type == 'num': return f"{val:.2f}x"
            if type == 'bps': return f"{val:+.2f} bps"
            return str(val)

        print(f"\n💎 --- {ticker} Institutional Valuation Deck ---")
        print("=" * 50)
        
        # 板块 1: 市场概况
        print(f"📅 Latest Filing : {metrics['Report Date']} ({metrics.get('Report Source', 'N/A')})")
        print(f"💰 Current Price : {fmt(metrics['Real-time Price'], 'price')}")
        print(f"🏢 Market Cap    : {fmt(metrics['Market Cap'])}")
        print(f"🏗️ Enterprise Val: {fmt(metrics['Enterprise Value (EV)'])}")
        print("-" * 50)
        
        # 板块 2: 估值比率
        print(f"⚖️ P/E Ratio     : {fmt(metrics['P/E Ratio'], 'num')}")
        print(f"🌊 FCF Yield     : {fmt(metrics['FCF Yield'], 'pct')}")
        
        # --- [新增] 股东回报 ---
        tsy = metrics.get('Total Shareholder Yield', 0)
        print(f"🎁 Total Yield     : {fmt(tsy, 'pct')} (Buyback + Div)")
        # ---------------------

        print(f"🏦 Risk-Free Rate: {fmt(metrics.get('Risk-Free Rate'), 'pct')}")
        print(f"🚀 Implied ERP   : {fmt(metrics.get('Equity Risk Premium (ERP)'), 'pct')}")
        print("-" * 50)
        
        # 板块 3: 增长与质量
        # ... (保留 Revenue, Growth, Gross Margin) ...
        print(f"🛡️ Gross Margin  : {fmt(metrics['Gross Margin'], 'pct')}")

        # --- [新增] 经济增加值 ---
        roic_val = metrics.get('ROIC', 0)
        ke_val = metrics.get('Cost of Equity (Ke)', 0)
        spread = metrics.get('EVA Spread', 0)
        
        print(f"👑 ROIC (Quality)  : {fmt(roic_val, 'pct')}")
        print(f"📉 Cost of Equity  : {fmt(ke_val, 'pct')} (Hurdle Rate)")
        print(f"💎 EVA Spread      : {fmt(spread, 'pct')} (Value Creation)")
        
        # --- [新增] 市场预期透视 ---
        imp_g = metrics.get('Implied Growth', 0)
        gap = metrics.get('Alpha Gap', 0)
        gap_signal = "UNDERVALUED" if gap > 0 else "OVERVALUED"
        
        print("-" * 50)
        print(f"🔮 Market Implied Growth : {fmt(imp_g, 'pct')} (Priced-in)")
        print(f"⚡ Alpha Gap            : {fmt(gap, 'pct')} [{gap_signal}]")
        
        # -----------------------

        print("=" * 50)
