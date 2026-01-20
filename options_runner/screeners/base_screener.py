from abc import ABC, abstractmethod
from options_runner.utils.market_data import MarketDataService

class BaseScreener(ABC):
    def __init__(self, market_service: MarketDataService):
        self.market = market_service

    @abstractmethod
    def run(self, symbol: str, **kwargs):
        """
        Main execution method for the screener.
        """
        pass

    def log(self, message):
        print(message)

    def log_header(self, title):
        print("\n" + "="*100)
        print(f"🚀 {title}")
        print("="*100)

    def log_separator(self):
        print("-" * 60)
