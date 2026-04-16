# pragya_ai/core/ta/macd.py

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

# --- Logika Perhitungan Indikator MACD ---
def _calculate_ma(series, length, ma_type):
    """Fungsi pembantu untuk menghitung Moving Average (SMA atau EMA)."""
    if ma_type == "SMA":
        return series.rolling(window=length).mean()
    elif ma_type == "EMA":
        return series.ewm(span=length, adjust=False).mean()
    return series.ewm(span=length, adjust=False).mean() # Default ke EMA jika tidak dikenali

def calculate_macd(df, fast=12, slow=26, signal=9, macd_ma_type="EMA", signal_ma_type="EMA"):
    """Menghitung MACD Line, Signal Line, dan Histogram."""
    df_calc = df.copy()
    src = df_calc['close']
    
    fast_ma = _calculate_ma(src, fast, macd_ma_type)
    slow_ma = _calculate_ma(src, slow, macd_ma_type)
    df_calc['macd_line'] = fast_ma - slow_ma
    
    df_calc['signal_line'] = _calculate_ma(df_calc['macd_line'], signal, signal_ma_type)
    df_calc['histogram'] = df_calc['macd_line'] - df_calc['signal_line']
    
    return df_calc

# --- Ekstraksi Laporan MACD yang Efisien ---
def get_macd_report(df, fast=12, slow=26, signal=9, macd_ma_type="EMA", signal_ma_type="EMA"):
    """Mengembalikan laporan mentah MACD dari bar terakhir."""
    df_macd = calculate_macd(df, fast, slow, signal, macd_ma_type, signal_ma_type)
    row = df_macd.iloc[-1]
    
    if pd.isna(row['macd_line']) or pd.isna(row['signal_line']):
        return None
    
    return {
        "time": row.name,
        "macd_line": row['macd_line'],
        "signal_line": row['signal_line'],
        "histogram": row['histogram'],
        "report_type": "macd_data"
    }

# --- Fungsi Utama ---
def main():
    try:
        config = load_config('config.yaml')
        general_config = config['general']
        assets_config = config['assets']
        macd_config = config.get('macd_indicator', {})

        if general_config['symbol'] == 'auto':
            today = datetime.now().weekday()
            if today >= 0 and today <= 4:
                symbol = assets_config['weekday']
            else:
                symbol = assets_config['weekend']
        else:
            symbol = general_config['symbol']
        
        timeframe = general_config['timeframe']
        
        fast = macd_config.get('fast_length', 12)
        slow = macd_config.get('slow_length', 26)
        signal_length = macd_config.get('signal_smoothing', 9)
        macd_ma_type = macd_config.get('macd_ma_type', "EMA")
        signal_ma_type = macd_config.get('signal_ma_type', "EMA")

        initialize_mt5()
        df = get_candles(symbol, timeframe)
        shutdown_mt5()

        macd_report = get_macd_report(df, fast, slow, signal_length, macd_ma_type, signal_ma_type)
        
        print(f"Laporan Indikator MACD untuk {symbol} ({timeframe})")
        print("--------------------------------------------------")
        
        if macd_report:
            print(f"Time: {macd_report['time']:%Y-%m-%d %H:%M:%S}")
            print(f"MACD Line: {macd_report['macd_line']:.4f}")
            print(f"Signal Line: {macd_report['signal_line']:.4f}")
            print(f"Histogram: {macd_report['histogram']:.4f}")
        else:
            print("Tidak ada data MACD yang valid.")

    except RuntimeError as e:
        print(f"Error: {e}")
    except FileNotFoundError as e:
        print(f"Error: {e}")
    except ValueError as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()