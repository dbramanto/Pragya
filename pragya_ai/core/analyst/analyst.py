# /pragya_ai/core/analyst/analyst.py
import pandas as pd
import numpy as np
from datetime import datetime
from core.logger import data_logger
from core.filter import spike_detector
from core.ta import atr
import yaml

def analyze_reports(reports, config):
    current_time = datetime.now()
    symbol = "XAUUSD (M15)" 

    signal = 'Hold'
    confidence_score = 0
    rationale = []

    rsi_report = reports.get('rsi', {})
    macd_report = reports.get('macd', {})
    sar_report = reports.get('parabolic_sar', {})
    candle_report = reports.get('candle_pattern', [])
    adx_report = reports.get('adx', {})
    atr_report = reports.get('atr', {})

    is_spike_detected = spike_detector.detect_spike(reports.get('data'), atr_report)
    if is_spike_detected:
        final_decision = {
            "time": current_time,
            "symbol": symbol,
            "decision": "Hold",
            "confidence_score": 0.0,
            "rationale": "Sinyal diabaikan karena terdeteksi lonjakan harga (spike)."
        }
        data_logger.initialize_logger()
        data_logger.log_decision(final_decision)
        return final_decision

    score_bullish = 0
    score_bearish = 0
    
    adx_value = adx_report.get('adx_value', 0)
    if adx_value > 25:
        rationale.append("ADX menunjukkan tren kuat.")
        if adx_report.get('plus_di', 0) > adx_report.get('minus_di', 0):
            score_bullish += 20
        else:
            score_bearish += 20
    else:
        rationale.append("ADX menunjukkan tren lemah atau sideways.")
        
    if sar_report and sar_report.get('trend') == 'Uptrend':
        score_bullish += 15
        rationale.append("Parabolic SAR mengkonfirmasi uptrend.")
    if sar_report and sar_report.get('trend') == 'Downtrend':
        score_bearish += 15
        rationale.append("Parabolic SAR mengkonfirmasi downtrend.")
        
    if rsi_report.get('rsi_value', 50) < 30:
        score_bullish += 15
        rationale.append("RSI di area oversold.")
    if rsi_report.get('rsi_value', 50) > 70:
        score_bearish += 15
        rationale.append("RSI di area overbought.")
    
    if macd_report.get('macd_line', 0) > macd_report.get('signal_line', 0):
        score_bullish += 20
        rationale.append("MACD crossover bullish.")
    if macd_report.get('macd_line', 0) < macd_report.get('signal_line', 0):
        score_bearish += 20
        rationale.append("MACD crossover bearish.")

    if isinstance(candle_report, list):
        for signal_data in candle_report:
            if isinstance(signal_data, dict):
                if signal_data.get('type') == 'bullish':
                    score_bullish += 25
                    rationale.append(f"Pola candlestick {signal_data['pattern']} terdeteksi.")
                elif signal_data.get('type') == 'bearish':
                    score_bearish += 25
                    rationale.append(f"Pola candlestick {signal_data['pattern']} terdeteksi.")
    
    total_score = score_bullish + score_bearish
    if score_bullish > score_bearish and score_bullish >= 20: 
        signal = 'Buy'
        confidence_score = (score_bullish / total_score) * 100 if total_score > 0 else 0
    elif score_bearish > score_bullish and score_bearish >= 20:
        signal = 'Sell'
        confidence_score = (score_bearish / total_score) * 100 if total_score > 0 else 0
    else:
        signal = 'Hold'
        confidence_score = 0
        rationale = ["Tidak ada konfirmasi sinyal yang kuat."]
        
    final_decision = {
        "time": current_time,
        "symbol": symbol,
        "decision": signal,
        "confidence_score": round(confidence_score, 2),
        "rationale": " | ".join(rationale)
    }
    
    data_logger.initialize_logger()
    data_logger.log_decision(final_decision)

    return final_decision

if __name__ == "__main__":
    pass