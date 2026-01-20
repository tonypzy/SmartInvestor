import sys
import os

# Add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

print("Checking imports...")

try:
    print("1. Importing InstitutionalDataPipeline...")
    from pipelines.data_pipeline import InstitutionalDataPipeline
    print("   ✅ Success")
    
    # Test instantiation
    print("   Testing instantiation...")
    pipeline = InstitutionalDataPipeline("Test", "test@example.com")
    print("   ✅ Instantiated")

except Exception as e:
    print(f"   ❌ Failed: {e}")

try:
    print("2. Importing Alpha_Engine...")
    from engines.alpha_engine import Alpha_Engine
    print("   ✅ Success")
except Exception as e:
    print(f"   ❌ Failed: {e}")

try:
    print("3. Importing Dashboards...")
    from dashboards.valuation_dashboard import ValuationDashboard
    from dashboards.peer_dashboard import PeerDashboard
    print("   ✅ Success")
except Exception as e:
    print(f"   ❌ Failed: {e}")

try:
    print("4. Importing Analysis Pipeline...")
    from pipelines.analysis_pipeline import get_fundamental_history
    print("   ✅ Success")
except Exception as e:
    print(f"   ❌ Failed: {e}")

# Note: We cannot easily import app.py due to streamlit, but imports inside it should be similar.
print("Done.")
