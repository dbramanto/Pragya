# pragya_ai/core/ta/obv.py

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

# --- Logika Perhitungan Indikator OBV ---
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

def calculate_obv(df, smoothing_type="None", smoothing_length=14, bb_mult=2.0):
    """Menghitung On-Balance Volume (OBV) dengan opsi smoothing."""
    df_calc = df.copy()
    
    # Perhitungan OBV dasar
    price_change = df_calc['close'].diff()
    obv_change = np.where(price_change > 0, df_calc['real_volume'], np.where(price_change < 0, -df_calc['real_volume'], 0))
    df_calc['OBV'] = obv_change.cumsum()
    
    # Perhitungan Smoothing dan Bollinger Bands
    if smoothing_type != "None":
        volume = df_calc.get('real_volume')
        df_calc['smoothing_ma'] = _calculate_ma(df_calc['OBV'], smoothing_length, smoothing_type, volume)
        if smoothing_type == "SMA + Bollinger Bands":
            stdev = df_calc['OBV'].rolling(window=smoothing_length).std()
            df_calc['bb_upper'] = df_calc['smoothing_ma'] + stdev * bb_mult
            df_calc['bb_lower'] = df_calc['smoothing_ma'] - stdev * bb_mult
    
    return df_calc

# --- Ekstraksi Laporan OBV yang Efisien ---
def get_obv_report(df, smoothing_type="None", smoothing_length=14, bb_mult=2.0):
    """Mengembalikan laporan mentah OBV dari bar terakhir."""
    df_obv = calculate_obv(df, smoothing_type, smoothing_length, bb_mult)
    row = df_obv.iloc[-1]
    
    if pd.isna(row['OBV']):
        return None
    
    report = {
        "time": row.name,
        "obv_value": row['OBV'],
        "report_type": "obv_data"
    }

    if 'smoothing_ma' in df_obv.columns and not pd.isna(row['smoothing_ma']):
        report['smoothing_ma'] = row['smoothing_ma']
    if 'bb_upper' in df_obv.columns and not pd.isna(row['bb_upper']):
        report['bb_upper'] = row['bb_upper']
        report['bb_lower'] = row['bb_lower']
        
    return report

# --- Fungsi Utama ---
def main():
    try:
        config = load_config('config.yaml')
        general_config = config['general']
        assets_config = config['assets']
        obv_config = config.get('obv_indicator', {})

        if general_config['symbol'] == 'auto':
            today = datetime.now().weekday()
            if today >= 0 and today <= 4:
                symbol = assets_config['weekday']
            else:
                symbol = assets_config['weekend']
        else:
            symbol = general_config['symbol']
        
        timeframe = general_config['timeframe']
        
        smoothing_type = obv_config.get('smoothing_ma_type', "None")
        smoothing_length = obv_config.get('smoothing_ma_length', 14)
        bb_mult = obv_config.get('bb_stddev', 2.0)

        initialize_mt5()
        bars = max(500, smoothing_length + 2)
        df = get_candles(symbol, timeframe, bars=bars)
        shutdown_mt5()

        obv_report = get_obv_report(df, smoothing_type, smoothing_length, bb_mult)
        
        print(f"Laporan Indikator OBV (Advanced) untuk {symbol} ({timeframe})")
        print("--------------------------------------------------")
        
        if obv_report:
            print(f"Time: {obv_report['time']:%Y-%m-%d %H:%M:%S}")
            print(f"OBV Value: {obv_report['obv_value']:.2f}")
            if 'smoothing_ma' in obv_report:
                print(f"Smoothing MA: {obv_report['smoothing_ma']:.2f}")
            if 'bb_upper' in obv_report:
                print(f"BB Upper: {obv_report['bb_upper']:.2f}")
                print(f"BB Lower: {obv_report['bb_lower']:.2f}")
        else:
            print("Tidak ada data OBV yang valid pada bar terakhir.")

    except RuntimeError as e:
        print(f"Error: {e}")
    except FileNotFoundError as e:
        print(f"Error: {e}")
    except ValueError as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()