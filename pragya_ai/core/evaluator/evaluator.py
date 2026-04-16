# /pragya_ai/core/evaluator/evaluator.py

import yaml
from datetime import datetime
import os
import shutil
import pandas as pd

from core.backtester import backtester

def save_best_config_version(config, performance_metrics):
    """
    Menyimpan konfigurasi terbaik dan laporannya sebagai versi baru.
    """
    version_dir = "history"
    if not os.path.exists(version_dir):
        os.makedirs(version_dir)
        
    existing_versions = [f for f in os.listdir(version_dir) if f.startswith('config_v') and f.endswith('.yaml')]
    latest_version = 0
    if existing_versions:
        # Pengecekan untuk memastikan file report juga ada
        latest_version = max([int(f.split('v')[1].split('.')[0]) for f in existing_versions if f.startswith('config_v')])
    
    new_version_number = latest_version + 1
    new_config_filename = f"config_v{new_version_number}.yaml"
    new_report_filename = f"report_v{new_version_number}.txt"

    new_config_path = os.path.join(version_dir, new_config_filename)
    with open(new_config_path, 'w') as f:
        yaml.dump(config, f)
        
    new_report_path = os.path.join(version_dir, new_report_filename)
    with open(new_report_path, 'w') as f:
        f.write("========== Laporan Tuning ==========\n")
        f.write(f"Versi: {new_version_number}\n")
        f.write(f"Tanggal: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        for key, value in performance_metrics.items():
            f.write(f"{key}: {value}\n")
        f.write("\n====================================\n")
        
    print(f"Versi {new_version_number} berhasil disimpan di folder history.")
    return new_version_number
    
def find_best_config(base_config, df):
    """
    Melakukan tuning dengan menjalankan backtest untuk mencari konfigurasi terbaik.
    """
    print("Mencari konfigurasi terbaik dengan backtest...")
    
    configs_to_test = [
        base_config.copy(),
        base_config.copy()
    ]
    
    # Variasi parameter tuning
    configs_to_test[1]['risk_management']['stop_loss']['fibo_level'] = 0.5
    
    best_performance = None
    best_config_found = None
    
    for i, config in enumerate(configs_to_test):
        print(f"  > Menjalankan backtest untuk variasi {i+1}...")
        performance = backtester.run_backtest(df, config)
        
        if performance:
            if not best_performance or performance['total_profit'] > best_performance['total_profit']:
                best_performance = performance
                best_config_found = config
    
    if best_config_found:
        print("Konfigurasi terbaik ditemukan!")
        return best_config_found, best_performance
    else:
        print("Tidak ada konfigurasi yang valid ditemukan.")
        return None, None