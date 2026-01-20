import yfinance as yf

class Market_Data:
    @staticmethod
    def get_realtime_market_data(ticker):
        """
        [修改版] 增加宏观数据抓取 (^TNX - 10年期美债收益率)
        """
        print(f"📡 [Market Data] Fetching real-time data for {ticker}...")
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # --- 新增：抓取无风险利率 (Risk-Free Rate) ---
            # 我们使用 Yahoo Finance 的 ^TNX 代码
            try:
                tnx = yf.Ticker("^TNX")
                # 获取最新一天的收盘价 (Yield)
                # 注意：^TNX 的价格 4.25 代表 4.25%，所以要除以 100
                tnx_hist = tnx.history(period="5d") # 抓5d防假期
                if not tnx_hist.empty:
                    rfr = tnx_hist['Close'].iloc[-1] / 100
                else:
                    rfr = 0.045 # Fallback: 默认 4.5%
            except Exception as e:
                print(f"   ⚠️ Failed to fetch ^TNX, using default 4.5%: {e}")
                rfr = 0.045

            market_data = {
                "Price": info.get('currentPrice', info.get('regularMarketPrice')),
                "Market Cap": info.get('marketCap'),
                "Shares Outstanding": info.get('sharesOutstanding'),
                "Beta": info.get('beta'),
                "Industry": info.get('industry'),
                "Risk-Free Rate": rfr # <--- 注入宏观因子
            }
            return market_data
        except Exception as e:
            print(f"❌ Market Data Error: {e}")
            return None
