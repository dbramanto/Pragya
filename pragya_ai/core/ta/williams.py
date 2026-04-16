# core/ta/williams.py

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

# --- Logika Perhitungan Sub-Indikator Williams ---
def _calculate_smma(series, length):
    """Menghitung Smoothed Moving Average (SMMA)."""
    alpha = 1 / length
    return series.ewm(alpha=alpha, adjust=False).mean()

def calculate_percent_r(df, length=14):
    """Menghitung Williams Percent Range (%R)."""
    df_calc = df.copy()
    highest_high = df_calc['high'].rolling(window=length).max()
    lowest_low = df_calc['low'].rolling(window=length).min()
    
    df_calc['percent_r'] = 100 * (df_calc['close'] - highest_high) / (highest_high - lowest_low)
    return df_calc

def calculate_alligator(df, jaw_len=13, teeth_len=8, lips_len=5, jaw_offset=8, teeth_offset=5, lips_offset=3):
    """Menghitung Williams Alligator."""
    df_calc = df.copy()
    hl2 = (df_calc['high'] + df_calc['low']) / 2
    
    df_calc['jaw'] = _calculate_smma(hl2, jaw_len).shift(jaw_offset)
    df_calc['teeth'] = _calculate_smma(hl2, teeth_len).shift(teeth_offset)
    df_calc['lips'] = _calculate_smma(hl2, lips_len).shift(lips_offset)
    
    return df_calc

def calculate_fractals(df, n=2):
    """Menghitung Williams Fractals."""
    df_calc = df.copy()
    
    up_fractal = (df_calc['high'].shift(n) < df_calc['high']) & \
                 (df_calc['high'].shift(n+1) < df_calc['high']) & \
                 (df_calc['high'].rolling(window=n, center=False).min().shift(n) > df_calc['high']) & \
                 (df_calc['high'].rolling(window=n, center=False).min().shift(-n) > df_calc['high'])
    
    down_fractal = (df_calc['low'].shift(n) > df_calc['low']) & \
                   (df_calc['low'].shift(n+1) > df_calc['low']) & \
                   (df_calc['low'].rolling(window=n, center=False).max().shift(n) < df_calc['low']) & \
                   (df_calc['low'].rolling(window=n, center=False).max().shift(-n) < df_calc['low'])
                   
    df_calc['up_fractal'] = up_fractal
    df_calc['down_fractal'] = down_fractal
    return df_calc


# --- Ekstraksi Laporan Williams yang Efisien ---
def get_williams_report(df, r_length=14, jaw_len=13, teeth_len=8, lips_len=5, fractal_n=2):
    """Menggabungkan laporan dari semua indikator Williams."""
    df_r = calculate_percent_r(df, length=r_length)
    df_alligator = calculate_alligator(df, jaw_len, teeth_len, lips_len)
    df_fractals = calculate_fractals(df, n=fractal_n)

    row = df.iloc[-1]
    
    report = {
        "time": row.name,
        "report_type": "williams_data",
        "percent_r": df_r.iloc[-1]['percent_r'] if 'percent_r' in df_r.columns and not pd.isna(df_r.iloc[-1]['percent_r']) else None,
        "alligator_jaw": df_alligator.iloc[-1]['jaw'] if 'jaw' in df_alligator.columns and not pd.isna(df_alligator.iloc[-1]['jaw']) else None,
        "alligator_teeth": df_alligator.iloc[-1]['teeth'] if 'teeth' in df_alligator.columns and not pd.isna(df_alligator.iloc[-1]['teeth']) else None,
        "alligator_lips": df_alligator.iloc[-1]['lips'] if 'lips' in df_alligator.columns and not pd.isna(df_alligator.iloc[-1]['lips']) else None,
        "up_fractal": df_fractals.iloc[-1]['up_fractal'] if 'up_fractal' in df_fractals.columns and not pd.isna(df_fractals.iloc[-1]['up_fractal']) else None,
        "down_fractal": df_fractals.iloc[-1]['down_fractal'] if 'down_fractal' in df_fractals.columns and not pd.isna(df_fractals.iloc[-1]['down_fractal']) else None,
    }
    
    return report

# --- Fungsi Utama ---
def main():
    try:
        config = load_config('config.yaml')
        general_config = config['general']
        assets_config = config['assets']
        william_config = config.get('william_indicator', {})

        if general_config['symbol'] == 'auto':
            today = datetime.now().weekday()
            if today >= 0 and today <= 4:
                symbol = assets_config['weekday']
            else:
                symbol = assets_config['weekend']
        else:
            symbol = general_config['symbol']
        
        timeframe = general_config['timeframe']
        
        r_length = william_config.get('percent_r_length', 14)
        jaw_len = william_config.get('alligator_jaw_length', 13)
        teeth_len = william_config.get('alligator_teeth_length', 8)
        lips_len = william_config.get('alligator_lips_length', 5)
        fractal_n = william_config.get('fractal_periods', 2)

        # Ambil bar yang cukup untuk semua perhitungan
        max_length = max(r_length, jaw_len, teeth_len, lips_len, fractal_n * 2 + 1)
        bars_needed = max(500, max_length + 26) # Perlu bar lebih banyak untuk offset

        initialize_mt5()
        df = get_candles(symbol, timeframe, bars=bars_needed)
        shutdown_mt5()

        william_report = get_williams_report(df, r_length, jaw_len, teeth_len, lips_len, fractal_n)
        
        print(f"Laporan Indikator Williams untuk {symbol} ({timeframe})")
        print("--------------------------------------------------")
        
        if william_report:
            print(f"Time: {william_report['time']:%Y-%m-%d %H:%M:%S}")
            print(f"Williams %R: {william_report['percent_r']:.2f}" if william_report['percent_r'] is not None else "Williams %R: N/A")
            print(f"Alligator Jaw: {william_report['alligator_jaw']:.4f}" if william_report['alligator_jaw'] is not None else "Alligator Jaw: N/A")
            print(f"Alligator Teeth: {william_report['alligator_teeth']:.4f}" if william_report['alligator_teeth'] is not None else "Alligator Teeth: N/A")
            print(f"Alligator Lips: {william_report['alligator_lips']:.4f}" if william_report['alligator_lips'] is not None else "Alligator Lips: N/A")
            print(f"Up Fractal: {william_report['up_fractal']}" if william_report['up_fractal'] is not None else "Up Fractal: N/A")
            print(f"Down Fractal: {william_report['down_fractal']}" if william_report['down_fractal'] is not None else "Down Fractal: N/A")
        else:
            print("Tidak ada data Williams yang valid pada bar terakhir.")

    except RuntimeError as e:
        print(f"Error: {e}")
    except FileNotFoundError as e:
        print(f"Error: {e}")
    except ValueError as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()