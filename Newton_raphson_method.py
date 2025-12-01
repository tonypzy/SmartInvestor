import numpy as np
from scipy.stats import norm

class OptionSolver:
    def __init__(self, S, K, T, r, option_type='call'):
        """
        初始化期权参数
        S: 标的资产价格 (Stock Price)
        K: 行权价 (Strike Price)
        T: 距离到期时间 (年化, e.g. 6/365)
        r: 无风险利率 (e.g. 0.045)
        option_type: 'call' 或 'put'
        """
        self.S = S
        self.K = K
        self.T = T
        self.r = r
        self.type = option_type.lower()

    def _calculate_d1_d2(self, sigma):
        """计算 Black-Scholes 模型中的 d1 和 d2"""
        # 防止 sigma 为 0 导致除零错误
        if sigma <= 1e-6: sigma = 1e-6
        
        d1 = (np.log(self.S / self.K) + (self.r + 0.5 * sigma ** 2) * self.T) / (sigma * np.sqrt(self.T))
        d2 = d1 - sigma * np.sqrt(self.T)
        return d1, d2

    def bs_price(self, sigma):
        """计算 Black-Scholes 理论价格"""
        d1, d2 = self._calculate_d1_d2(sigma)
        
        if self.type == 'call':
            price = self.S * norm.cdf(d1) - self.K * np.exp(-self.r * self.T) * norm.cdf(d2)
        else:
            price = self.K * np.exp(-self.r * self.T) * norm.cdf(-d2) - self.S * norm.cdf(-d1)
        return price

    def bs_vega(self, sigma):
        """计算 Vega (价格对波动率的导数)"""
        # Call 和 Put 的 Vega 是一样的
        d1, _ = self._calculate_d1_d2(sigma)
        vega = self.S * norm.pdf(d1) * np.sqrt(self.T)
        return vega

    def implied_volatility(self, market_price, tol=1e-5, max_iter=100):
        """
        使用牛顿-拉夫逊法计算隐含波动率 (IV)
        
        market_price: 市场上的期权现价
        tol: 容忍误差 (Tolerance)
        max_iter: 最大迭代次数
        """
        # 1. 初始猜测 (Initial Guess)
        # 通常设为 0.5 (50%) 是个不错的起点
        sigma = 0.5 
        
        for i in range(max_iter):
            # 2. 计算当前猜测下的理论价格
            price = self.bs_price(sigma)
            
            # 3. 计算与市场价的差值 (Diff)
            diff = market_price - price
            
            # 4. 检查是否满足精度要求 (收敛判断)
            if abs(diff) < tol:
                return sigma
            
            # 5. 计算当前的 Vega (梯度/斜率)
            vega = self.bs_vega(sigma)
            
            # 保护机制：如果 Vega 太小 (接近 0)，牛顿法会失效 (除以零飞逸)
            # 这通常发生在深度实值或深度虚值期权上
            if abs(vega) < 1e-8:
                print("警告: Vega 过小，牛顿法无法收敛，建议改用二分法")
                return None 
            
            # 6. 牛顿法核心更新公式： x_new = x_old - f(x) / f'(x)
            # 这里的 f(x) 是 (理论价 - 市场价)，所以如果理论价低了(diff>0)，我们需要增加 sigma
            # 注意符号：diff = market - price = - (price - market)
            # 公式变体：sigma = sigma + diff / vega
            sigma = sigma + diff / vega
            
            # 保护机制：波动率不可能是负数
            if sigma <= 0:
                sigma = 1e-5
                
        print("警告: 达到最大迭代次数，未能收敛")
        return sigma

# --- 实战测试 (使用你的 SLV 数据) ---

# 参数设置
S_current = 51.19   # 估算的 SLV 股价
Strike = 51.0       # 行权价
Days = 5 + (12 + 4) / 24 + (40 + 4 * 60) / (24 * 60)           # 剩余天数
T_annual = Days / 365.0
RiskFreeRate = 0.0388 # 假设 4.5% 无风险利率
Market_Price = 1.32 # 市场价格

# 实例化求解器
solver = OptionSolver(S=S_current, K=Strike, T=T_annual, r=RiskFreeRate, option_type='call')

# 计算 IV
iv = solver.implied_volatility(Market_Price)

print("-" * 30)
print(f"标的资产: SLV (Est. ${S_current})")
print(f"期权: Dec 05 ${Strike} Call")
print(f"市场价格: ${Market_Price}")
print("-" * 30)

if iv:
    print(f"计算出的隐含波动率 (IV): {iv:.4%}")
    print(f"验证: 带入 IV 算出的理论价格 = ${solver.bs_price(iv):.4f}")
else:
    print("计算失败")