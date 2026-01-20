import pandas as pd
from data.sec_core.SEC_Loader import SEC_Loader
from data.sec_core.SEC_Parser import SEC_Parser
from data.market_data import Market_Data
from engines.alpha_engine import Alpha_Engine
from reporting.reporting import Reporting
from dashboards.valuation_dashboard import ValuationDashboard
from dashboards.peer_dashboard import PeerDashboard


def get_fundamental_history(ticker, loader, parser):
    """
    Orchestrates the loading and parsing of filings to build a history.
    """
    # 1. Get all file paths
    # Note: We need to implement get_all_filing_paths in SEC_Loader or use the two calls
    paths_k = loader.get_filing_paths(ticker, "10-K")
    paths_q = loader.get_filing_paths(ticker, "10-Q")
    all_paths = paths_k + paths_q
    
    all_data = []
    for path in all_paths:
        data = parser.parse_single_filing(path)
        if data and 'Period End Date' in data:
            all_data.append(data)
            
    # 2. Sort by date (descending)
    all_data.sort(key=lambda x: x.get('Period End Date', '0000-00-00'), reverse=True)
    return all_data

def run_pipeline(target_tickers, mode="DEEP_DIVE", email="tony.peng@example.com"):
    # --- Dependencies Injection ---
    loader = SEC_Loader("SmartInvestor_Lab", email)
    parser = SEC_Parser()
    alpha = Alpha_Engine()
    reporting = Reporting()
    
    print(f"\n🚀 System Mode: [{mode}] | Targets: {len(target_tickers)}")
    print("=" * 60)

    batch_results = []

    for ticker in target_tickers:
        print(f"\n📡 Analyzing {ticker}...")
        try:
            # 1. Ingestion
            download_limit = 12 if mode == "DEEP_DIVE" else 4
            loader.fetch_filings(ticker, amount=download_limit)
            
            # 2. Data Construction
            fundamentals = get_fundamental_history(ticker, loader, parser)
            
            # 3. Market Data
            realtime_data = Market_Data.get_realtime_market_data(ticker)
            
            if fundamentals and realtime_data:
                # 4. Alpha Generation
                metrics = alpha.process_analysis(ticker, fundamentals, realtime_data)
                
                # 5. Reporting
                reporting.print_institutional_deck(ticker, metrics)

                # 6. Visualization / Batching
                if mode == "DEEP_DIVE":
                    print(f"🎨 Launching Deep Dive Dashboard for {ticker}...")
                    
                    df_trends = alpha.process_time_series(ticker, fundamentals, realtime_data)
                    viz = ValuationDashboard()
                    
                    if df_trends is not None and not df_trends.empty:
                         print("   (1/2) Showing Historical Trends...")
                         viz.plot_historical_trends(ticker, df_trends)
                    
                    print("   (2/2) Showing Valuation Snapshot...")
                    viz.plot_dashboard(ticker, metrics)
                
                else:
                    # Collect for peers
                    summary = {
                        'Ticker': ticker,
                        'Market Cap': metrics['Market Cap'],
                        'FCF Yield': metrics['FCF Yield'],
                        'Sequential Growth': metrics['Sequential Growth'],
                        'EV/EBIT': metrics['EV/EBIT'],
                        'P/E Ratio': metrics['P/E Ratio'],
                        'ERP': metrics.get('Equity Risk Premium (ERP)', 0),
                        'ROIC': metrics.get('ROIC', 0)
                    }
                    batch_results.append(summary)

            else:
                print(f"⚠️ Skipping {ticker}: Data incomplete.")

        except Exception as e:
            print(f"❌ Error analyzing {ticker}: {e}")
            import traceback
            traceback.print_exc()

    # --- Sector Scan Conclusion ---
    if mode == "SECTOR_SCAN":
        print("\n🏁 Sector Scan Complete. Preparing Comparison Map...")
        if batch_results:
            df_peers = pd.DataFrame(batch_results)
            
            print("\n📋 Top Picks by FCF Yield:")
            pd.options.display.float_format = '{:,.2f}'.format
            print(df_peers[['Ticker', 'FCF Yield', 'Sequential Growth', 'P/E Ratio']].sort_values(by='FCF Yield', ascending=False))
            
            print("\n🎨 Launching Peer Comparison Dashboard...")
            peer_viz = PeerDashboard()
            peer_viz.plot_peer_comparison(df_peers)
        else:
            print("❌ No valid data collected for sector analysis.")

if __name__ == "__main__":
    # Example usage
    run_pipeline(['AAPL'], mode="DEEP_DIVE")