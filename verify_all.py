import sys
import os
import io
import contextlib

# Add project root to path ensuring we can import options_runner
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from options_runner.utils.market_data import MarketDataService

# Import all screeners
from options_runner.screeners.iron_condor import IronCondorScreener
from options_runner.screeners.zebra import ZebraScreener
from options_runner.screeners.bull_put import BullPutScreener
from options_runner.screeners.bull_call import BullCallScreener
from options_runner.screeners.double_bull import DoubleBullScreener
from options_runner.screeners.strangle_short import ShortStrangleScreener
from options_runner.screeners.strangle_long import LongStrangleScreener
from options_runner.screeners.leaps import LeapsScreener
from options_runner.screeners.deep_itm import DeepITMScreener
from options_runner.screeners.bear_call import BearCallScreener

def verify_all(symbol="SPY"):
    print(f"🚀 Starting Smoke Test on {symbol}...")
    
    # 1. Instantiate MarketDataService once (Dependency Injection)
    try:
        market = MarketDataService()
        # Pre-fetch basic data to be sure
        print("   - Market Data Service Initialized.")
    except Exception as e:
        print(f"🔥 Critical Error: Failed to initialize MarketDataService: {e}")
        return

    # List of strategy classes to test
    strategies = [
        ("IronCondor", IronCondorScreener),
        ("Zebra", ZebraScreener),
        ("BullPut", BullPutScreener),
        ("BullCall", BullCallScreener),
        ("DoubleBull", DoubleBullScreener),
        ("ShortStrangle", ShortStrangleScreener),
        ("LongStrangle", LongStrangleScreener),
        ("Leaps", LeapsScreener),
        ("DeepITM", DeepITMScreener),
        ("BearCall", BearCallScreener)
    ]
    
    passed_count = 0
    failed_count = 0
    
    print("-" * 50)

    for name, screener_cls in strategies:
        try:
            # Instantiate strategy
            screener = screener_cls(market)
            
            # Prepare kwargs for specific strategies that require them
            kwargs = {}
            if name == "DoubleBull":
                # DoubleBull needs explicit strikes usually, we provide safe defaults for testing
                current_price = market.get_current_price(symbol)
                kwargs = {
                    'max_put_strike': int(current_price * 0.9), 
                    'min_call_strike': int(current_price * 1.05)
                }
            elif name == "BearCall":
                 # Optional but helpful to set min sell strike
                 pass

            # Capture stdout to determine if setups were found
            f = io.StringIO()
            with contextlib.redirect_stdout(f):
                screener.run(symbol, **kwargs)
            
            output = f.getvalue()
            
            # Analyze output
            if "No valid strategies" in output or "No dates" in output:
                status_msg = "Run completed (No setups found)"
            else:
                # Basic heuristic: if it printed a table, it likely found setups.
                # All separate strategies print a table header or pandas output.
                status_msg = "Run completed (Setups found)"
            
            print(f"✅ {name}: {status_msg}")
            passed_count += 1
            
        except Exception as e:
            print(f"❌ {name}: {str(e)}")
            failed_count += 1
            # Import traceback to print stack trace if needed, but per requirements just msg
            # traceback.print_exc()

    print("-" * 50)
    print(f"🏁 Smoke Test Summary: Total: {len(strategies)}, Passed: {passed_count}, Failed: {failed_count}")

if __name__ == "__main__":
    # Allow passing symbol via CLI
    target_symbol = "SPY"
    if len(sys.argv) > 1:
        target_symbol = sys.argv[1]
    
    verify_all(target_symbol)
