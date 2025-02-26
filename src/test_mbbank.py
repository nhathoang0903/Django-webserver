import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
import torch
# Use newer torch configuration methods
torch.set_default_dtype(torch.float32)
torch.set_default_device('cpu')
import warnings
warnings.filterwarnings("ignore")

from mbbank import MBBank
from datetime import datetime, timedelta
import time

def test_mbbank_connection():
    USERNAME = "NHATHOANG0903"
    PASSWORD = "Nhathoang@4"
    account_no = "3099932002"

    try:
        print("Testing MBBank connection...")
        mb = MBBank(username=USERNAME, password=PASSWORD)
        
        print("Authenticating...")
        mb._authenticate()
        print("Authentication successful!")
        
        current_time = datetime.now()
        start_time = current_time - timedelta(minutes=5)
        
        print("Fetching recent transactions...")
        transactions = mb.getTransactionAccountHistory(
            accountNo=account_no,
            from_date=start_time,
            to_date=current_time
        )
        
        if transactions and 'transactionHistoryList' in transactions:
            print("Successfully retrieved transactions!")
            print(f"Found {len(transactions['transactionHistoryList'])} transactions")
        else:
            print("No transactions found in the last 5 minutes")
            
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        print("Test complete")

if __name__ == "__main__":
    test_mbbank_connection()
