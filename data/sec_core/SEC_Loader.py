import os
import glob
from sec_edgar_downloader import Downloader

class SEC_Loader:
    def __init__(self, company_name, email_address):
        current_script_folder = os.path.dirname(os.path.abspath(__file__))
        self.download_folder = os.path.join(current_script_folder, "sec_data")
        self.dl = Downloader(company_name, email_address, self.download_folder)
        self.base_dir = os.path.join(self.download_folder, "sec-edgar-filings")

    def fetch_filings(self, ticker, amount=4): 
        # amount 设为 4，确保能覆盖最近的一年
        print(f"🚀 [Ingestion] Downloading 10-K and 10-Q stream for {ticker}...")
        try:
            # 同时下载两种格式
            self.dl.get("10-K", ticker, limit=amount, download_details=True) # 只要最近两年的年报
            self.dl.get("10-Q", ticker, limit=amount, download_details=True) # 最近4个季度的季报
            print("✅ Download complete.")
        except Exception as e:
            print(f"❌ Download failed: {e}")

    def get_filing_paths(self, ticker, form_type):
        """
        [新功能] 获取所有下载的 Filing 文件夹路径
        """
        target_dir = os.path.join(self.base_dir, ticker, form_type)
        if not os.path.exists(target_dir):
            return []
        # sec-edgar-downloader 每个 filing 都在一个独立的文件夹里（Accession Number）
        # 我们获取该目录下所有的子文件夹
        subdirs = [os.path.join(target_dir, d) for d in os.listdir(target_dir) if os.path.isdir(os.path.join(target_dir, d))]
        return subdirs

    def get_all_filing_paths(self, ticker):
        """
        Retrieve both 10-K and 10-Q paths
        """
        folders_k = self.get_filing_paths(ticker, "10-K")
        folders_q = self.get_filing_paths(ticker, "10-Q")
        return folders_k + folders_q
