import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.dates as mdates
import seaborn as sns
import pandas as pd

class ValuationDashboard:
    def __init__(self):
        # Robinhood 风格色板
        self.rh = {
            'bg': '#000000', 'green': '#00c805', 'red': '#ff5a5f',
            'blue': '#00a4eb', 'gold': '#ff9f00', 'text': '#ffffff',
            'sub': '#888888', 'grid': '#1a1a1a'
        }
        # 全局配置
        plt.rcParams.update({
            'font.family': 'sans-serif', 'font.weight': 'bold',
            'axes.edgecolor': self.rh['bg'], 'axes.facecolor': self.rh['bg'],
            'figure.facecolor': self.rh['bg'], 'text.color': self.rh['text'],
            'xtick.color': self.rh['sub'], 'ytick.color': self.rh['sub'],
            'axes.labelcolor': self.rh['sub'], 'axes.grid': True,
            'grid.color': self.rh['grid'], 'grid.linestyle': '--'
        })

    def plot_historical_trends(self, ticker, df_history):
        """
        [新增] 绘制历史趋势图 (Sparklines)
        包含: Gross Margin 走势 & FCF Yield 走势
        """
        if df_history is None or df_history.empty:
            print("❌ No historical data to plot.")
            return

        # 确保按时间正序排列 (从过去到现在)
        df = df_history.sort_values(by='Date')
        dates = pd.to_datetime(df['Date'])

        # 创建画布 (上下两图)
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
        plt.subplots_adjust(hspace=0.3) # 调整间距

        # --- 图表 A: Gross Margin Trend (盈利能力) ---
        # 逻辑：毛利率下降是危险信号
        margins = df['Gross Margin']
        ax1.plot(dates, margins, color=self.rh['blue'], linewidth=2.5, marker='o', markersize=6)
        ax1.fill_between(dates, margins, min(margins)*0.98, color=self.rh['blue'], alpha=0.1)
        
        ax1.set_title(f"{ticker} Gross Margin Trend (L8Q)", fontsize=16, color='white', fontweight='bold', pad=15)
        ax1.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))
        
        # 标注最新值
        last_date = dates.iloc[-1]
        last_margin = margins.iloc[-1]
        ax1.text(last_date, last_margin, f"  {last_margin:.1%}", color=self.rh['blue'], fontsize=12, fontweight='bold', va='center')

        # --- 图表 B: FCF Yield Trend (估值吸引力) ---
        # 逻辑：Yield 升高说明变便宜，降低说明变贵
        yields = df['FCF Yield']
        # 颜色逻辑：Yield > 4% 为绿，否则为红/橙
        line_color = self.rh['green'] if yields.iloc[-1] > 0.04 else self.rh['gold']
        
        ax2.plot(dates, yields, color=line_color, linewidth=2.5, marker='o', markersize=6)
        ax2.fill_between(dates, yields, min(yields)*0.9, color=line_color, alpha=0.1)
        
        ax2.set_title("FCF Yield Trend (based on Current Market Cap)", fontsize=16, color='white', fontweight='bold', pad=15)
        ax2.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m')) # 时间格式
        
        # 标注最新值
        last_yield = yields.iloc[-1]
        ax2.text(last_date, last_yield, f"  {last_yield:.2%}", color=line_color, fontsize=12, fontweight='bold', va='center')

        print("📊 Historical Trend Dashboard Generated.")
        plt.show()


    def plot_dashboard(self, ticker, metrics):
        if not metrics:
            print("❌ No metrics to plot.")
            return

        # ---------------------------------------------------------
        # 1. 准备数据
        # ---------------------------------------------------------
        # A. 漏斗数据
        rev = metrics.get('Revenue (Run Rate)', 0)
        gross_profit = rev * metrics.get('Gross Margin', 0)
        pe = metrics.get('P/E Ratio', 0)
        ni = metrics['Market Cap'] / pe if pe else 0
        fcf = metrics['Market Cap'] * metrics.get('FCF Yield', 0)

        # B. 估值数据
        ev_ebit = metrics.get('EV/EBIT', 0)
        
        # ---------------------------------------------------------
        # 2. 创建画布 (2行2列)
        # ---------------------------------------------------------
        fig = plt.figure(figsize=(14, 8))
        gs = fig.add_gridspec(2, 2, height_ratios=[1.2, 1]) # 上面稍微高一点
        
        # ---------------------------------------------------------
        # 图表 A: 盈利漏斗 (Financial Funnel) - 柱状图
        # ---------------------------------------------------------
        ax1 = fig.add_subplot(gs[0, :])
        
        labels = ['Revenue', 'Gross Profit', 'Net Income', 'Free Cash Flow']
        values = [rev, gross_profit, ni, fcf]
        # 使用霓虹配色区分层级
        colors = [self.rh['blue'], '#00dbe7', self.rh['green'], self.rh['gold']]
        
        bars = ax1.bar(labels, values, color=colors, width=0.5, zorder=3)
        
        # 顶部大标题
        ax1.text(0, 1.15, f"{ticker} Financial Funnel", transform=ax1.transAxes, 
                 fontsize=18, fontweight='bold', color='white')
        ax1.text(0, 1.08, "Annualized Run-Rate (Billions)", transform=ax1.transAxes, 
                 fontsize=11, color=self.rh['sub'])

        # 柱子上方的数值标签
        for bar in bars:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height * 1.02,
                    f'${height/1e9:,.1f}B',
                    ha='center', va='bottom', color='white', fontweight='bold', fontsize=11)
        
        # Y轴格式化
        ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: f'${x/1e9:,.0f}B'))
        ax1.grid(axis='x', visible=False) # 隐藏竖向网格
        
        # ---------------------------------------------------------
        # 图表 B: 估值倍数 (Valuation Multiples) - 横向条形图
        # ---------------------------------------------------------
        ax2 = fig.add_subplot(gs[1, 0])
        
        ratios = ['P/E Ratio', 'EV/EBIT']
        vals = [pe, ev_ebit]
        # 逻辑颜色：红色代表 P/E (通常较高), 绿色代表 EV/EBIT (扣除现金后较低)
        ratio_colors = [self.rh['red'], self.rh['green']]
        
        bars2 = ax2.barh(ratios, vals, color=ratio_colors, height=0.5, zorder=3)
        
        ax2.text(0, 1.1, "Valuation Reality", transform=ax2.transAxes, 
                 fontsize=14, fontweight='bold', color='white')
        
        # 条形右侧数值
        for bar in bars2:
            width = bar.get_width()
            ax2.text(width + 0.5, bar.get_y() + bar.get_height()/2,
                    f'{width:.1f}x',
                    ha='left', va='center', color='white', fontsize=11, fontweight='bold')
            
        ax2.set_xlim(0, max(vals)*1.4) # 留出右侧空间写字
        ax2.grid(axis='y', visible=False)

        # ---------------------------------------------------------
        # 图表 C: 核心记分卡 (Institutional Signal) - 纯文字
        # ---------------------------------------------------------
        ax3 = fig.add_subplot(gs[1, 1])
        ax3.axis('off')
        
        # 数据准备
        fcf_yield = metrics.get('FCF Yield', 0)
        growth = metrics.get('Sequential Growth', 0)
        margin_exp = metrics.get('Margin Expansion', 0)
        
        # 颜色逻辑
        c_yield = self.rh['green'] if fcf_yield > 0.04 else self.rh['red']
        c_growth = self.rh['green'] if growth > 0 else self.rh['red']
        
        # 绘制文本 (模拟 App 界面布局)
        ax3.text(0.05, 0.95, "INSTITUTIONAL SIGNAL", fontsize=12, color=self.rh['sub'], fontweight='bold')
        
        # 1. FCF Yield
        ax3.text(0.05, 0.75, "FCF Yield (Alpha)", fontsize=11, color='white')
        ax3.text(0.55, 0.75, f"{fcf_yield:.2%}", fontsize=18, color=c_yield, fontweight='bold')
        
        # 2. Growth
        ax3.text(0.05, 0.55, "Seq. Growth (QoQ)", fontsize=11, color='white')
        ax3.text(0.55, 0.55, f"{growth:.2%}", fontsize=18, color=c_growth, fontweight='bold')
        
        # 3. Margin Trend
        trend_str = "Expanding" if margin_exp > 0 else "Contracting"
        c_trend = self.rh['green'] if margin_exp > 0 else self.rh['red']
        
        ax3.text(0.05, 0.35, "Margin Trend", fontsize=11, color='white')
        ax3.text(0.55, 0.35, f"{trend_str}", fontsize=16, color=c_trend, fontweight='bold')
        
        # 装饰线
        ax3.plot([0.05, 0.9], [0.68, 0.68], color=self.rh['grid'], linewidth=1)
        ax3.plot([0.05, 0.9], [0.48, 0.48], color=self.rh['grid'], linewidth=1)

        # ---------------------------------------------------------
        # 3. 调整布局与展示
        # ---------------------------------------------------------
        plt.subplots_adjust(hspace=0.4, wspace=0.3, top=0.9, bottom=0.1, left=0.1, right=0.9)
        
        print("📊 Robinhood Data Dashboard Generated.")
        plt.show()