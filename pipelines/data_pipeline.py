import os
import glob
import pandas as pd
from sec_edgar_downloader import Downloader
from data.sec_core.SEC_Parser import SEC_Parser
from data.market_data import Market_Data

class InstitutionalDataPipeline:
    def __init__(self, company_name, email_address):
        """
        Main Pipeline Class acting as a Facade for Data Ingestion and Parsing.
        """
        # 1. Get absolute path
        current_script_folder = os.path.dirname(os.path.abspath(__file__))
        
        # 2. Define storage folder. Note: Since we are in pipelines/, creating sec_data here.
        # Ideally this should be centralized. Let's traverse up to data/ if possible, 
        # or just keep it local to be safe with existing logic.
        # Let's put it in data/sec_data relative to project root (pipelines/../data/sec_data)
        project_root = os.path.dirname(current_script_folder) # SmartInvestor/
        self.download_folder = os.path.join(project_root, "data", "sec_data")
        
        if not os.path.exists(self.download_folder):
            os.makedirs(self.download_folder, exist_ok=True)
            
        # 3. Initialize Downloader
        self.dl = Downloader(company_name, email_address, self.download_folder)
        
        # 4. Initialize Parser
        self.parser = SEC_Parser()
        
        self.base_dir = self.download_folder
        print(f"📂 [Init] SEC Data Path: {self.download_folder}")

    def fetch_filings(self, ticker, form_type="10-K", amount=1):
        """
        Downloads filings.
        """
        print(f"🚀 [Ingestion] Downloading latest {amount} {form_type} for {ticker}...")
        try:
            self.dl.get(form_type, ticker, limit=amount)
            print("✅ Download command executed.")
        except Exception as e:
            print(f"❌ Download failed: {e}")

    def get_fundamental_history(self, ticker):
        """
        Orchestrates finding and parsing all historical filings (10-K and 10-Q).
        Returns a list of dictionaries (metrics).
        """
        all_data = []
        forms = ["10-K", "10-Q"]
        
        # Structure: sec_data/sec-edgar-filings/{ticker}/{form_type}/{accession_number}/...
        
        for form in forms:
            ticker_root = os.path.join(self.base_dir, "sec-edgar-filings", ticker, form)
            if not os.path.exists(ticker_root):
                continue
            
            # Iterate over accession number directories
            # each subdirectory is one filing
            for item in os.listdir(ticker_root):
                filing_path = os.path.join(ticker_root, item)
                if os.path.isdir(filing_path):
                    # Parse this filing folder
                    data = self.parser.parse_single_filing(filing_path)
                    if data:
                        # Ensure Source is set correctly if parser didn't set it (parser sets it based on path)
                        # We can enforce it
                        if data.get('Source') == 'Unknown':
                            data['Source'] = form
                        
                        # Only include if we have a valid date
                        if 'Period End Date' in data:
                            all_data.append(data)

        # Sort by date descending
        all_data.sort(key=lambda x: x.get('Period End Date', '0000-00-00'), reverse=True)
        return all_data

    def get_realtime_market_data(self, ticker):
        """
        Delegate to Market_Data
        """
        return Market_Data.get_realtime_market_data(ticker)

    # Legacy method support if needed, but get_fundamental_history is preferred
    def parse_financials(self, ticker, form_type="10-K"):
        # This was single file parsing. 
        # We can implement it by reusing get_fundamental_history and taking the first one?
        # Or just return None as it's legacy.
        print("⚠️ parse_financials is deprecated. Use get_fundamental_history.")
        return None

if __name__ == "__main__":
    # Test
    pipeline = InstitutionalDataPipeline("SmartInvestor_Lab", "test@example.com")
    # pipeline.fetch_filings("AAPL", amount=1)
    # h = pipeline.get_fundamental_history("AAPL")
    # print(h)