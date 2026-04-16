# pragya_ai/core/ta/mfi.py

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

# --- Logika Perhitungan Indikator Money Flow Index (MFI) ---
def calculate_mfi(df, period: int = 14):
    """
    Menghitung Money Flow Index (MFI) menggunakan operasi vektor.
    """
    df_calc = df.copy()
    
    df_calc['tp'] = (df_calc['high'] + df_calc['low'] + df_calc['close']) / 3
    df_calc['money_flow'] = df_calc['tp'] * df_calc['real_volume']

    df_calc['flow_change'] = df_calc['tp'].diff()
    
    positive_flow = df_calc['money_flow'].where(df_calc['flow_change'] > 0, 0)
    negative_flow = df_calc['money_flow'].where(df_calc['flow_change'] < 0, 0)
    
    pos_mf_sum = positive_flow.rolling(window=period).sum()
    neg_mf_sum = negative_flow.rolling(window=period).sum()

    mf_ratio = pos_mf_sum / neg_mf_sum.replace(0, 1e-9)
    df_calc['MFI'] = 100 - (100 / (1 + mf_ratio))
    
    return df_calc

# --- Ekstraksi Laporan MFI yang Efisien ---
def get_mfi_report(df, period: int = 14):
    """Mengembalikan laporan mentah MFI dari bar terakhir."""
    df_mfi = calculate_mfi(df, period)
    row = df_mfi.iloc[-1]
    
    if pd.isna(row['MFI']):
        return None
    
    return {
        "time": row.name,
        "mfi_value": row['MFI'],
        "report_type": "mfi_data"
    }

# --- Fungsi Utama ---
def main():
    try:
        config = load_config('config.yaml')
        general_config = config['general']
        assets_config = config['assets']
        mfi_config = config.get('mfi_indicator', {})

        if general_config['symbol'] == 'auto':
            today = datetime.now().weekday()
            if today >= 0 and today <= 4:
                symbol = assets_config['weekday']
            else:
                symbol = assets_config['weekend']
        else:
            symbol = general_config['symbol']
        
        timeframe = general_config['timeframe']
        period = mfi_config.get('length', 14)

        initialize_mt5()
        df = get_candles(symbol, timeframe)
        shutdown_mt5()

        mfi_report = get_mfi_report(df, period)
        
        print(f"Laporan Indikator MFI untuk {symbol} ({timeframe})")
        print("--------------------------------------------------")
        
        if mfi_report:
            print(f"Time: {mfi_report['time']:%Y-%m-%d %H:%M:%S}")
            print(f"MFI Value: {mfi_report['mfi_value']:.2f}")
        else:
            print("Tidak ada data MFI yang valid pada bar terakhir.")

    except RuntimeError as e:
        print(f"Error: {e}")
    except FileNotFoundError as e:
        print(f"Error: {e}")
    except ValueError as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()