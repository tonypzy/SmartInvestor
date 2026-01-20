import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd
import numpy as np

class PeerDashboard:
    def __init__(self):
        # 罗宾汉/彭博 风格色板
        self.styles = {
            'bg': '#000000',
            'grid': '#1a1a1a',
            'text': '#ffffff',
            'bubble_pos': '#00c805', # 正收益 (绿)
            'bubble_neg': '#ff5a5f', # 负收益 (红)
            'highlight': '#00a4eb'   # 高亮 (蓝)
        }
        
        # 全局配置
        plt.rcParams.update({
            'font.family': 'sans-serif',
            'font.weight': 'bold',
            'axes.edgecolor': self.styles['bg'],
            'axes.facecolor': self.styles['bg'],
            'figure.facecolor': self.styles['bg'],
            'text.color': self.styles['text'],
            'xtick.color': '#888888',
            'ytick.color': '#888888',
            'axes.labelcolor': '#888888',
            'axes.grid': True,
            'grid.color': self.styles['grid'],
            'grid.linestyle': '--'
        })

    def plot_peer_comparison(self, df_metrics):
        """
        绘制同业对标散点图 (Alpha Map)
        X轴: Growth (动量)
        Y轴: Value (估值/Yield)
        气泡大小: Market Cap
        """
        if df_metrics.empty:
            print("❌ No data to plot.")
            return

        # 1. 提取数据
        tickers = df_metrics['Ticker']
        x_growth = df_metrics['Sequential Growth']
        y_yield = df_metrics['FCF Yield']
        # 气泡大小：归一化处理，防止气泡太大或太小
        mkt_caps = df_metrics['Market Cap']
        bubble_sizes = (mkt_caps / mkt_caps.max()) * 2000 + 100 

        # 2. 创建画布
        fig, ax = plt.subplots(figsize=(14, 9))

        # 3. 绘制参考线 (中位数) - 划分象限
        median_x = x_growth.median()
        median_y = y_yield.median()
        
        ax.axvline(x=median_x, color='#444444', linestyle=':', linewidth=1)
        ax.axhline(y=median_y, color='#444444', linestyle=':', linewidth=1)

        # 4. 绘制气泡 (Scatter)
        # 根据 FCF Yield 正负决定颜色
        colors = [self.styles['bubble_pos'] if y > 0 else self.styles['bubble_neg'] for y in y_yield]
        
        scatter = ax.scatter(x_growth, y_yield, s=bubble_sizes, c=colors, alpha=0.6, edgecolors='white', linewidth=1.5)

        # 5. 添加标签 (Ticker)
        for i, txt in enumerate(tickers):
            # 将文字放在气泡中心
            ax.annotate(txt, (x_growth[i], y_yield[i]), 
                        ha='center', va='center', 
                        color='white', fontsize=10, fontweight='bold')
            
            # 在气泡下方显示简要数据
            label_detail = f"Yld:{y_yield[i]:.1%}\nGrw:{x_growth[i]:.1%}"
            ax.annotate(label_detail, (x_growth[i], y_yield[i]), 
                        xytext=(0, -45), textcoords='offset points',
                        ha='center', va='top', fontsize=8, color='#aaaaaa')

        # 6. 装饰与标注
        ax.set_title("Sector Alpha Map: Growth vs. Valuation", fontsize=20, fontweight='bold', pad=20, color='white')
        ax.set_xlabel("Sequential Growth (Momentum)", fontsize=12, labelpad=10)
        ax.set_ylabel("FCF Yield (Value)", fontsize=12, labelpad=10)

        # 格式化坐标轴百分比
        ax.xaxis.set_major_formatter(mticker.PercentFormatter(1.0))
        ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))

        # 7. 添加象限说明 (Institutional Insight)
        # 右上：GARP (Growth at Reasonable Price)
        ax.text(0.95, 0.95, "💰 SWEET SPOT\nHigh Growth + High Yield", 
                transform=ax.transAxes, ha='right', va='top', color=self.styles['bubble_pos'], alpha=0.5, fontsize=12)
        
        # 左下：Value Trap / Overvalued
        ax.text(0.05, 0.05, "⚠️ AVOID AREA\nLow Growth + Low Yield", 
                transform=ax.transAxes, ha='left', va='bottom', color=self.styles['bubble_neg'], alpha=0.5, fontsize=12)

        plt.tight_layout()
        print("📊 Peer Comparison Dashboard Generated.")
        plt.show()

        plt.tight_layout()
        return fig