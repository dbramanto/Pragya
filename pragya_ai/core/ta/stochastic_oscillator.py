# core/ta/stochastic_oscillator.py

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

# --- Logika Perhitungan Indikator Stochastic Oscillator ---
def calculate_stochastic(df, period_k=14, smooth_k=1, period_d=3):
    """Menghitung indikator Stochastic Oscillator (%K dan %D)."""
    df_calc = df.copy()
    high = df_calc['high']
    low = df_calc['low']
    close = df_calc['close']

    lowest_low = low.rolling(window=period_k).min()
    highest_high = high.rolling(window=period_k).max()
    
    # Hitung %K mentah
    percent_k = 100 * ((close - lowest_low) / (highest_high - lowest_low))
    
    # Haluskan %K
    df_calc['%K'] = percent_k.rolling(window=smooth_k).mean()
    
    # Hitung %D sebagai MA dari %K
    df_calc['%D'] = df_calc['%K'].rolling(window=period_d).mean()

    return df_calc

# --- Ekstraksi Laporan Stochastic yang Efisien ---
def get_stochastic_report(df, period_k=14, smooth_k=1, period_d=3):
    """Mengembalikan laporan mentah Stochastic dari bar terakhir."""
    df_stoch = calculate_stochastic(df, period_k, smooth_k, period_d)
    row = df_stoch.iloc[-1]
    
    if pd.isna(row['%K']) or pd.isna(row['%D']):
        return None
    
    return {
        "time": row.name,
        "k_value": row['%K'],
        "d_value": row['%D'],
        "report_type": "stochastic_data"
    }

# --- Fungsi Utama ---
def main():
    try:
        config = load_config('config.yaml')
        general_config = config['general']
        assets_config = config['assets']
        stoch_config = config.get('stoch_indicator', {})

        if general_config['symbol'] == 'auto':
            today = datetime.now().weekday()
            if today >= 0 and today <= 4:
                symbol = assets_config['weekday']
            else:
                symbol = assets_config['weekend']
        else:
            symbol = general_config['symbol']
        
        timeframe = general_config['timeframe']
        period_k = stoch_config.get('period_k', 14)
        smooth_k = stoch_config.get('smooth_k', 1)
        period_d = stoch_config.get('period_d', 3)

        initialize_mt5()
        df = get_candles(symbol, timeframe, bars=max(500, period_k + period_d))
        shutdown_mt5()

        stoch_report = get_stochastic_report(df, period_k, smooth_k, period_d)
        
        print(f"Laporan Indikator Stochastic Oscillator untuk {symbol} ({timeframe})")
        print("--------------------------------------------------")
        
        if stoch_report:
            print(f"Time: {stoch_report['time']:%Y-%m-%d %H:%M:%S}")
            print(f"%K Value: {stoch_report['k_value']:.2f}")
            print(f"%D Value: {stoch_report['d_value']:.2f}")
        else:
            print("Tidak ada data Stochastic Oscillator yang valid.")

    except RuntimeError as e:
        print(f"Error: {e}")
    except FileNotFoundError as e:
        print(f"Error: {e}")
    except ValueError as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()