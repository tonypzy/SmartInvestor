import sys
import os
import glob

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.sec_core.SEC_Parser import SEC_Parser

def debug():
    parser = SEC_Parser()
    
    # Path to a real downloaded file
    base_path = r"c:\Users\tonypzy\Desktop\programming_files\VisualStudioCode\SmartInvestor\data\sec_core\sec_data\sec-edgar-filings\AAPL\10-K"
    
    # Find a folder
    if not os.path.exists(base_path):
        print("Path not found")
        return

    subdirs = [os.path.join(base_path, d) for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d))]
    target_folder = subdirs[0] # Pick the first one
    
    print(f"Debugging folder: {target_folder}")
    
    # Run parsing
    data = parser.parse_single_filing(target_folder)
    print("Extracted Data:", data)

if __name__ == "__main__":
    debug()
