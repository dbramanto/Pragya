# /pragya_ai/core/backtester/backtester.py
import pandas as pd
from core.agents import synthesizer
from core.analyst import analyst

def run_backtest(df, config):
    """
    Menjalankan simulasi trading menggunakan data historis dan
    menghitung metrik performa yang realistis.
    """
    print("Memulai backtest...")
    
    initial_balance = 10000.0
    balance = initial_balance
    max_drawdown = 0.0
    peak_balance = initial_balance
    total_trades = 0
    
    # Placeholder untuk posisi trading
    is_position_open = False
    entry_price = 0.0
    
    # Loop melalui setiap bar data historis untuk simulasi
    for i in range(len(df)):
        # Dapatkan laporan dan keputusan dari Analyst untuk data hingga bar saat ini
        reports = synthesizer.synthesize_reports(df.iloc[:i+1], config)
        decision = analyst.analyze_reports(reports, config)
        
        # Logika entry (hanya untuk Buy)
        if decision['decision'] == 'Buy' and not is_position_open:
            is_position_open = True
            entry_price = df.iloc[i]['close']
            total_trades += 1
            # print(f"OPEN BUY: {df.index[i]} at {entry_price}")
            
        # Logika exit
        if is_position_open:
            # Sederhana: hitung profit/loss
            profit = (df.iloc[i]['close'] - entry_price) 
            
            # Untuk demo, kita anggap exit jika profit > 100 atau loss > 500
            if profit > 100 or profit < -500:
                balance += profit
                is_position_open = False
                # print(f"CLOSE: {df.index[i]} with profit {profit}")
                
        # Perbarui drawdown
        if balance > peak_balance:
            peak_balance = balance
        current_drawdown = (peak_balance - balance) / peak_balance * 100
        if current_drawdown > max_drawdown:
            max_drawdown = current_drawdown
            
    # Jika ada posisi yang masih terbuka di akhir
    if is_position_open:
        balance += (df.iloc[-1]['close'] - entry_price)
        
    performance = {
        "total_profit": round(balance - initial_balance, 2),
        "max_drawdown": round(max_drawdown, 2),
        "sharpe_ratio": "N/A", # Perlu logika lebih lanjut
        "total_trades": total_trades
    }
        
    print("Backtest selesai.")
    return performance