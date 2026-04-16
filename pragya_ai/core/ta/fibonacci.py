# core/ta/fibonacci.py

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

# --- Logika Perhitungan Inti Fibonacci ---
def _find_high_pivots(high_series, depth):
    """Mendeteksi pivot high."""
    is_high_pivot = high_series.rolling(window=depth*2 + 1, center=True).apply(lambda x: x.iloc[depth] == x.max(), raw=False)
    high_pivots = high_series[is_high_pivot == 1].dropna()
    return high_pivots

def _find_low_pivots(low_series, depth):
    """Mendeteksi pivot low."""
    is_low_pivot = low_series.rolling(window=depth*2 + 1, center=True).apply(lambda x: x.iloc[depth] == x.min(), raw=False)
    low_pivots = low_series[is_low_pivot == 1].dropna()
    return low_pivots

def calculate_fibonacci(df, mode="retracement", depth=10):
    """Menghitung level Fibonacci (Retracement atau Extension)."""
    high_pivots = _find_high_pivots(df['high'], depth // 2)
    low_pivots = _find_low_pivots(df['low'], depth // 2)
    
    if high_pivots.empty or low_pivots.empty:
        return None, None, {}

    last_high_pivot_time = high_pivots.index[-1]
    last_low_pivot_time = low_pivots.index[-1]
    last_high_pivot_price = high_pivots.iloc[-1]
    last_low_pivot_price = low_pivots.iloc[-1]
    
    swing_start_price = None
    swing_end_price = None
    levels = {}

    if last_high_pivot_time > last_low_pivot_time:  # Swing turun: High -> Low
        swing_end_price = last_high_pivot_price
        prev_low_pivots = low_pivots[low_pivots.index < last_high_pivot_time]
        if prev_low_pivots.empty: return None, None, {}
        swing_start_price = prev_low_pivots.iloc[-1]
    else:  # Swing naik: Low -> High
        swing_end_price = last_low_pivot_price
        prev_high_pivots = high_pivots[high_pivots.index < last_low_pivot_time]
        if prev_high_pivots.empty: return None, None, {}
        swing_start_price = prev_high_pivots.iloc[-1]

    diff = abs(swing_end_price - swing_start_price)

    if mode == "retracement":
        levels = {
            '0.0%': round(swing_start_price, 4),
            '23.6%': round(swing_end_price + 0.236 * diff, 4) if swing_start_price < swing_end_price else round(swing_end_price - 0.236 * diff, 4),
            '38.2%': round(swing_end_price + 0.382 * diff, 4) if swing_start_price < swing_end_price else round(swing_end_price - 0.382 * diff, 4),
            '50.0%': round(swing_end_price + 0.500 * diff, 4) if swing_start_price < swing_end_price else round(swing_end_price - 0.500 * diff, 4),
            '61.8%': round(swing_end_price + 0.618 * diff, 4) if swing_start_price < swing_end_price else round(swing_end_price - 0.618 * diff, 4),
            '78.6%': round(swing_end_price + 0.786 * diff, 4) if swing_start_price < swing_end_price else round(swing_end_price - 0.786 * diff, 4),
            '100.0%': round(swing_end_price + 1.0 * diff, 4) if swing_start_price < swing_end_price else round(swing_end_price - 1.0 * diff, 4),
        }
    elif mode == "extension":
        levels = {
            '0.0': round(swing_start_price, 4),
            '0.236': round(swing_end_price + 0.236 * diff, 4),
            '0.382': round(swing_end_price + 0.382 * diff, 4),
            '0.5': round(swing_end_price + 0.500 * diff, 4),
            '0.618': round(swing_end_price + 0.618 * diff, 4),
            '0.786': round(swing_end_price + 0.786 * diff, 4),
            '1.0': round(swing_end_price + 1.0 * diff, 4),
            '1.272': round(swing_end_price + 1.272 * diff, 4),
            '1.618': round(swing_end_price + 1.618 * diff, 4),
            '2.618': round(swing_end_price + 2.618 * diff, 4),
            '3.618': round(swing_end_price + 3.618 * diff, 4),
            '4.236': round(swing_end_price + 4.236 * diff, 4),
        }

    return swing_start_price, swing_end_price, levels

# --- Ekstraksi Laporan Fibonacci yang Efisien ---
def get_fibonacci_report(df, mode="retracement", depth=10):
    """Mengembalikan laporan mentah Fibonacci dari bar terakhir."""
    start_price, end_price, levels = calculate_fibonacci(df, mode, depth)
    
    if start_price is None or not levels:
        return None
    
    return {
        "time": df.index[-1],
        "swing_start": start_price,
        "swing_end": end_price,
        "fibonacci_levels": levels,
        "mode": mode,
        "report_type": "fibonacci_data"
    }

# --- Fungsi Utama ---
def main():
    try:
        config = load_config('config.yaml')
        general_config = config['general']
        assets_config = config['assets']
        fib_config = config.get('fib_indicator', {})

        if general_config['symbol'] == 'auto':
            today = datetime.now().weekday()
            if today >= 0 and today <= 4:
                symbol = assets_config['weekday']
            else:
                symbol = assets_config['weekend']
        else:
            symbol = general_config['symbol']
        
        timeframe = general_config['timeframe']
        mode = fib_config.get('mode', 'retracement')
        depth = fib_config.get('depth', 10)

        initialize_mt5()
        df = get_candles(symbol, timeframe, bars=500)
        shutdown_mt5()

        fib_report = get_fibonacci_report(df, mode, depth)
        
        print(f"Laporan Indikator Fibonacci ({mode.capitalize()}) untuk {symbol} ({timeframe})")
        print("--------------------------------------------------")
        
        if fib_report:
            print(f"Time: {fib_report['time']:%Y-%m-%d %H:%M:%S}")
            print(f"Swing Start: {fib_report['swing_start']:.4f}")
            print(f"Swing End: {fib_report['swing_end']:.4f}")
            print("📐 Levels:")
            for level, value in fib_report['fibonacci_levels'].items():
                print(f"  - {level}: {value:.4f}")
        else:
            print("Tidak ada data Fibonacci yang valid.")

    except RuntimeError as e:
        print(f"Error: {e}")
    except FileNotFoundError as e:
        print(f"Error: {e}")
    except ValueError as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()