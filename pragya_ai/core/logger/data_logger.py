# /pragya_ai/core/logger/data_logger.py

import pandas as pd
import os
from datetime import datetime

log_file_path = "logs/trading_decisions.csv"

def initialize_logger():
    """
    Memastikan folder dan file log ada.
    """
    log_dir = os.path.dirname(log_file_path)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    if not os.path.exists(log_file_path):
        header = "timestamp,symbol,decision,confidence_score,rationale\n"
        with open(log_file_path, 'w') as f:
            f.write(header)
            
    print("Logger diinisialisasi.")
    
def log_decision(decision_data):
    """
    Menulis satu baris keputusan trading ke file log.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"{timestamp},{decision_data['symbol']},{decision_data['decision']},{decision_data['confidence_score']},{decision_data['rationale']}\n"
    
    with open(log_file_path, 'a') as f:
        f.write(log_entry)
        
    print("Keputusan trading dicatat.")