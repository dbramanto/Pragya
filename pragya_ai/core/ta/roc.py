# pragya_ai/core/ta/roc.py

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime
import yaml

# --- Fungsi Dasar untuk Konfigurasi & MT5 ---
def load_config(config_path='config.yaml'):
    """Membaca file konfigurasi YAML dengan encoding UTF-8."""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    except FileNotFoundError:
        raise FileNotFoundError(f"Konfigurasi file tidak ditemukan di: {config_path}")
    except yaml.YAMLError as e:
        raise ValueError(f"Error saat memuat file konfigurasi: {e}")

def initialize_mt5():
    """Menginisialisasi koneksi ke MetaTrader 5."""
    if not mt5.initialize():
        raise RuntimeError("MT5 initialization failed")

def shutdown_mt5():
    """Mematikan koneksi ke MetaTrader 5."""
    mt5.shutdown()

def get_candles(symbol, timeframe, bars=500):
    """Mengambil data historis OHLC dari MetaTrader 5."""
    tf = getattr(mt5, f"TIMEFRAME_{timeframe}")
    rates = mt5.copy_rates_from_pos(symbol, tf, 0, bars)
    if rates is None:
        raise RuntimeError(f"Failed to get rates for {symbol}")
    
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    df.set_index('time', inplace=True)
    return df

# --- Logika Perhitungan Indikator Rate of Change (ROC) ---
def calculate_roc(df, period: int = 9):
    """Menghitung Rate of Change (ROC) untuk DataFrame."""
    df_calc = df.copy()
    source = df_calc['close']
    
    df_calc['ROC'] = ((source - source.shift(period)) / source.shift(period)) * 100
    
    return df_calc

# --- Ekstraksi Laporan ROC yang Efisien ---
def get_roc_report(df, period: int = 9):
    """Mengembalikan laporan mentah ROC dari bar terakhir."""
    df_roc = calculate_roc(df, period)
    row = df_roc.iloc[-1]
    
    if pd.isna(row['ROC']):
        return None
    
    return {
        "time": row.name,
        "roc_value": row['ROC'],
        "report_type": "roc_data"
    }

# --- Fungsi Utama ---
def main():
    try:
        config = load_config('config.yaml')
        general_config = config['general']
        assets_config = config['assets']
        roc_config = config.get('roc_indicator', {})

        if general_config['symbol'] == 'auto':
            today = datetime.now().weekday()
            if today >= 0 and today <= 4:
                symbol = assets_config['weekday']
            else:
                symbol = assets_config['weekend']
        else:
            symbol = general_config['symbol']
        
        timeframe = general_config['timeframe']
        period = roc_config.get('length', 9)

        initialize_mt5()
        df = get_candles(symbol, timeframe)
        shutdown_mt5()

        roc_report = get_roc_report(df, period)
        
        print(f"Laporan Indikator ROC untuk {symbol} ({timeframe})")
        print("--------------------------------------------------")
        
        if roc_report:
            print(f"Time: {roc_report['time']:%Y-%m-%d %H:%M:%S}")
            print(f"ROC Value: {roc_report['roc_value']:.2f}")
        else:
            print("Tidak ada data ROC yang valid pada bar terakhir.")

    except RuntimeError as e:
        print(f"Error: {e}")
    except FileNotFoundError as e:
        print(f"Error: {e}")
    except ValueError as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()