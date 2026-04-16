# core/ta/pivot_points.py

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

# --- Logika Perhitungan Indikator Pivot Points ---
def calculate_pivots(high, low, close, pivot_type="Traditional"):
    """
    Menghitung Pivot Point dan level S/R berdasarkan berbagai metode.
    """
    p = (high + low + close) / 3
    
    if pivot_type == "Traditional":
        r1 = 2 * p - low
        s1 = 2 * p - high
        r2 = p + (high - low)
        s2 = p - (high - low)
        r3 = high + 2 * (p - low)
        s3 = low - 2 * (high - p)
        return {'P': p, 'R1': r1, 'S1': s1, 'R2': r2, 'S2': s2, 'R3': r3, 'S3': s3}
    
    elif pivot_type == "Fibonacci":
        diff = high - low
        r1 = p + 0.382 * diff
        s1 = p - 0.382 * diff
        r2 = p + 0.618 * diff
        s2 = p - 0.618 * diff
        r3 = p + 1.0 * diff
        s3 = p - 1.0 * diff
        return {'P': p, 'R1': r1, 'S1': s1, 'R2': r2, 'S2': s2, 'R3': r3, 'S3': s3}

    elif pivot_type == "Woodie":
        p = (high + low + 2 * close) / 4
        r1 = 2 * p - low
        s1 = 2 * p - high
        r2 = p + high - low
        s2 = p - high + low
        r3 = r1 + high - low
        s3 = s1 - high + low
        return {'P': p, 'R1': r1, 'S1': s1, 'R2': r2, 'S2': s2, 'R3': r3, 'S3': s3}

    elif pivot_type == "Classic":
        r1 = 2 * p - low
        s1 = 2 * p - high
        r2 = p + (high - low)
        s2 = p - (high - low)
        r3 = r2 + (high - low)
        s3 = s2 - (high - low)
        return {'P': p, 'R1': r1, 'S1': s1, 'R2': r2, 'S2': s2, 'R3': r3, 'S3': s3}

    elif pivot_type == "DM":
        dm = high - low
        if dm > 0: p = high
        elif dm < 0: p = low
        else: p = close
        r1 = p + (high - low)
        s1 = p - (high - low)
        return {'P': p, 'R1': r1, 'S1': s1}

    elif pivot_type == "Camarilla":
        r4 = (high - low) * 1.1 / 2 + close
        r3 = (high - low) * 1.1 / 4 + close
        r2 = (high - low) * 1.1 / 6 + close
        r1 = (high - low) * 1.1 / 12 + close
        s1 = close - (high - low) * 1.1 / 12
        s2 = close - (high - low) * 1.1 / 6
        s3 = close - (high - low) * 1.1 / 4
        s4 = close - (high - low) * 1.1 / 2
        return {'P': p, 'R1': r1, 'S1': s1, 'R2': r2, 'S2': s2, 'R3': r3, 'S3': s3, 'R4': r4, 'S4': s4}

    return {}


# --- Ekstraksi Laporan Pivot Points yang Efisien ---
def get_pivot_report(df, pivot_type="Traditional", pivot_timeframe="Daily"):
    """Mengembalikan laporan mentah Pivot Points untuk periode terakhir."""
    
    # Pemetaan dari format Pine Script ke Pandas
    tf_map = {
        "Daily": "D", "Weekly": "W", "Monthly": "M", 
        "Quarterly": "Q", "Yearly": "Y"
    }
    
    # Ambil periode terakhir yang sudah selesai
    period_tf = tf_map.get(pivot_timeframe, "D")
    df_resampled = df.resample(period_tf).agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'
    }).dropna()

    if df_resampled.empty or len(df_resampled) < 2:
        return None

    # Mengambil bar terakhir yang sudah selesai
    last_period_data = df_resampled.iloc[-2]
    
    pivots = calculate_pivots(
        last_period_data['high'],
        last_period_data['low'],
        last_period_data['close'],
        pivot_type
    )

    if not pivots:
        return None
    
    return {
        "time": df.index[-1],
        "pivot_type": pivot_type,
        "pivot_timeframe": pivot_timeframe,
        "levels": pivots,
        "report_type": "pivot_data"
    }

# --- Fungsi Utama ---
def main():
    try:
        config = load_config('config.yaml')
        general_config = config['general']
        assets_config = config['assets']
        pivot_config = config.get('pivot_indicator', {})

        if general_config['symbol'] == 'auto':
            today = datetime.now().weekday()
            if today >= 0 and today <= 4:
                symbol = assets_config['weekday']
            else:
                symbol = assets_config['weekend']
        else:
            symbol = general_config['symbol']
        
        timeframe = general_config['timeframe']
        
        pivot_type = pivot_config.get('pivot_type', 'Traditional')
        pivot_tf = pivot_config.get('pivot_timeframe', 'Daily')

        initialize_mt5()
        df = get_candles(symbol, timeframe, bars=1000)
        shutdown_mt5()

        pivot_report = get_pivot_report(df, pivot_type, pivot_tf)
        
        print(f"Laporan Indikator Pivot Points untuk {symbol} ({timeframe})")
        print("--------------------------------------------------")
        
        if pivot_report:
            print(f"Time: {pivot_report['time']:%Y-%m-%d %H:%M:%S}")
            print(f"Pivot Type: {pivot_report['pivot_type']}")
            print(f"Pivot Timeframe: {pivot_report['pivot_timeframe']}")
            print("Levels:")
            for level, value in pivot_report['levels'].items():
                print(f"  - {level}: {value:.4f}")
        else:
            print("Tidak ada data Pivot Points yang valid.")

    except RuntimeError as e:
        print(f"Error: {e}")
    except FileNotFoundError as e:
        print(f"Error: {e}")
    except ValueError as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()