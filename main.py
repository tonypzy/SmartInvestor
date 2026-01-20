import sys
from pipelines.analysis_pipeline import run_pipeline

def main():
    print("==========================================")
    print("   💎 SmartInvestor Institutional CLI    ")
    print("==========================================")
    
    print("Select Analysis Mode:")
    print("1. Deep Dive (Single Ticker)")
    print("2. Sector Scan (Multiple Tickers)")
    
    try:
        choice = input("\nEnter choice (1/2): ").strip()
        
        if choice == '1':
            ticker = input("Enter Ticker (e.g., AAPL): ").strip().upper()
            if not ticker:
                print("❌ Invalid ticker.")
                return
            
            run_pipeline([ticker], mode="DEEP_DIVE")
            
        elif choice == '2':
            default_tickers = "AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA"
            print(f"Default list: {default_tickers}")
            user_input = input("Enter Tickers (comma separated) or press Enter for default: ").strip()
            
            if not user_input:
                tickers = [t.strip().upper() for t in default_tickers.split(",")]
            else:
                tickers = [t.strip().upper() for t in user_input.split(",") if t.strip()]
            
            if not tickers:
                print("❌ No tickers provided.")
                return
                
            run_pipeline(tickers, mode="SECTOR_SCAN")
            
        else:
            print("❌ Invalid choice.")
            
    except KeyboardInterrupt:
        print("\n\nExiting...")
        sys.exit(0)

if __name__ == "__main__":
    main()
