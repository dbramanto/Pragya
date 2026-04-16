# /pragya_ai/core/filter/spike_detector.py
import pandas as pd
from core.ta import atr

def detect_spike(df, atr_report, spike_threshold=2.0):
    """
    Mendeteksi lonjakan harga (spike) dengan membandingkan
    perubahan harga bar terakhir dengan ATR.
    """
    if df.empty or atr_report is None:
        return False
        
    last_bar = df.iloc[-1]
    current_range = last_bar['high'] - last_bar['low']
    
    avg_true_range = atr_report.get('atr_value')
    
    if avg_true_range is not None and avg_true_range > 0:
        # Jika range bar terakhir lebih besar dari threshold * ATR, maka dianggap spike
        if current_range > (avg_true_range * spike_threshold):
            return True
            
    return False