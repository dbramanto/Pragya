# core/ta/bb.py

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
    """Mengambil data historis OHLCV dari MetaTrader 5."""
    tf = getattr(mt5, f"TIMEFRAME_{timeframe}")
    rates = mt5.copy_rates_from_pos(symbol, tf, 0, bars)
    if rates is None:
        raise RuntimeError(f"Failed to get rates for {symbol}")
    
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    df.set_index('time', inplace=True)
    return df

# --- Logika Perhitungan Indikator Bollinger Bands ---
def _calculate_ma(series, length, ma_type, volume=None):
    """Fungsi pembantu untuk menghitung berbagai jenis Moving Average."""
    if ma_type == "SMA":
        return series.rolling(window=length).mean()
    elif ma_type == "EMA":
        return series.ewm(span=length, adjust=False).mean()
    elif ma_type == "SMMA (RMA)":
        alpha = 1 / length
        return series.ewm(alpha=alpha, adjust=False).mean()
    elif ma_type == "WMA":
        weights = np.arange(1, length + 1)
        return series.rolling(window=length).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)
    elif ma_type == "VWMA" and volume is not None:
        return (series * volume).rolling(window=length).sum() / volume.rolling(window=length).sum()
    return series.rolling(window=length).mean() # Default ke SMA jika tidak dikenali

def calculate_bollinger_bands(df, length=20, ma_type="SMA", mult=2.0):
    """Menghitung Bollinger Bands (BB) untuk DataFrame."""
    df_calc = df.copy()
    close = df_calc['close']
    volume = df_calc.get('real_volume') # Gunakan volume jika tersedia

    # Menghitung basis dengan MA yang dipilih
    df_calc["BB_basis"] = _calculate_ma(close, length, ma_type, volume)
    
    # Menghitung Standar Deviasi
    df_calc["BB_stddev"] = close.rolling(window=length).std()
    
    # Menghitung pita atas dan bawah
    df_calc["BB_upper"] = df_calc["BB_basis"] + mult * df_calc["BB_stddev"]
    df_calc["BB_lower"] = df_calc["BB_basis"] - mult * df_calc["BB_stddev"]
    df_calc["Basis_Type"] = ma_type
    
    return df_calc

# --- Ekstraksi Laporan BB yang Efisien ---
def get_bb_report(df, length=20, ma_type="SMA", mult=2.0):
    """Mengembalikan laporan mentah BB dari bar terakhir."""
    df_bb = calculate_bollinger_bands(df, length, ma_type, mult)
    row = df_bb.iloc[-1]
    
    if pd.isna(row["BB_basis"]) or pd.isna(row["BB_upper"]) or pd.isna(row["BB_lower"]):
        return None
    
    return {
        "time": row.name,
        "bb_basis": row["BB_basis"],
        "bb_upper": row["BB_upper"],
        "bb_lower": row["BB_lower"],
        "basis_ma_type": row["Basis_Type"],
        "report_type": "bb_data"
    }

# --- Fungsi Utama ---
def main():
    try:
        config = load_config('config.yaml')
        general_config = config['general']
        assets_config = config['assets']
        bb_config = config.get('bb_indicator', {})

        if general_config['symbol'] == 'auto':
            today = datetime.now().weekday()
            if today >= 0 and today <= 4:
                symbol = assets_config['weekday']
            else:
                symbol = assets_config['weekend']
        else:
            symbol = general_config['symbol']
        
        timeframe = general_config['timeframe']
        
        # Parameter dari config atau nilai default
        length = bb_config.get('length', 20)
        ma_type = bb_config.get('ma_type', "SMA")
        mult = bb_config.get('stddev_mult', 2.0)

        initialize_mt5()
        df = get_candles(symbol, timeframe)
        shutdown_mt5()

        bb_report = get_bb_report(df, length=length, ma_type=ma_type, mult=mult)
        
        print(f"Laporan Indikator Bollinger Bands ({ma_type}) untuk {symbol} ({timeframe})")
        print("--------------------------------------------------")
        
        if bb_report:
            print(f"Time: {bb_report['time']:%Y-%m-%d %H:%M:%S}")
            print(f"Basis ({bb_report['basis_ma_type']}): {bb_report['bb_basis']:.4f}")
            print(f"Upper: {bb_report['bb_upper']:.4f}")
            print(f"Lower: {bb_report['bb_lower']:.4f}")
        else:
            print("Tidak ada data Bollinger Bands yang valid.")

    except RuntimeError as e:
        print(f"Error: {e}")
    except FileNotFoundError as e:
        print(f"Error: {e}")
    except ValueError as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()