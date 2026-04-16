# core/ta/atr.py

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

# --- Logika Perhitungan Indikator ATR ---
def _calculate_ma(series, length, ma_type):
    """Fungsi pembantu untuk menghitung berbagai jenis Moving Average."""
    if ma_type == "SMA":
        return series.rolling(window=length).mean()
    elif ma_type == "EMA":
        return series.ewm(span=length, adjust=False).mean()
    elif ma_type == "RMA":
        alpha = 1 / length
        return series.ewm(alpha=alpha, adjust=False).mean()
    elif ma_type == "WMA":
        weights = np.arange(1, length + 1)
        return series.rolling(window=length).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)
    return series.rolling(window=length).mean() # Default ke SMA jika tidak dikenali

def calculate_atr(df, length=14, smoothing="RMA"):
    """
    Menghitung Average True Range (ATR) dengan opsi smoothing.
    """
    df_calc = df.copy()
    high = df_calc["high"]
    low = df_calc["low"]
    close = df_calc["close"]

    # Menghitung True Range (TR)
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    df_calc["TR"] = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)
    
    # Menghitung ATR dengan smoothing yang dipilih
    df_calc["ATR"] = _calculate_ma(df_calc["TR"], length, smoothing)
    df_calc["Smoothing"] = smoothing
    
    return df_calc

# --- Ekstraksi Laporan ATR yang Efisien ---
def get_atr_report(df, length=14, smoothing="RMA"):
    """Mengembalikan laporan mentah ATR dari bar terakhir."""
    df_atr = calculate_atr(df, length, smoothing)
    row = df_atr.iloc[-1]
    
    if pd.isna(row["ATR"]):
        return None
    
    return {
        "time": row.name,
        "atr_value": row["ATR"],
        "smoothing_type": row["Smoothing"],
        "report_type": "atr_data"
    }

# --- Fungsi Utama ---
def main():
    try:
        config = load_config('config.yaml')
        general_config = config['general']
        assets_config = config['assets']
        atr_config = config.get('atr_indicator', {})

        if general_config['symbol'] == 'auto':
            today = datetime.now().weekday()
            if today >= 0 and today <= 4:
                symbol = assets_config['weekday']
            else:
                symbol = assets_config['weekend']
        else:
            symbol = general_config['symbol']
        
        timeframe = general_config['timeframe']
        length = atr_config.get('length', 14)
        smoothing = atr_config.get('smoothing', 'RMA')

        initialize_mt5()
        df = get_candles(symbol, timeframe)
        shutdown_mt5()

        atr_report = get_atr_report(df, length, smoothing)
        
        print(f"Laporan Indikator ATR ({smoothing}) untuk {symbol} ({timeframe})")
        print("--------------------------------------------------")
        
        if atr_report:
            print(f"Time: {atr_report['time']:%Y-%m-%d %H:%M:%S}")
            print(f"ATR Value: {atr_report['atr_value']:.2f}")
        else:
            print("Tidak ada data ATR yang valid pada bar terakhir.")

    except RuntimeError as e:
        print(f"Error: {e}")
    except FileNotFoundError as e:
        print(f"Error: {e}")
    except ValueError as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()