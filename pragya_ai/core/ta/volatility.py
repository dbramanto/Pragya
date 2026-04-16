# core/ta/volatility.py

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

# --- Logika Perhitungan Sub-Indikator Volatility ---
def _calculate_atr(df, period=14):
    """Menghitung ATR untuk digunakan di Volatility Stop."""
    high = df['high']
    low = df['low']
    close = df['close']
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()

def calculate_historical_volatility(df, length=10, annual=365):
    """Menghitung Historical Volatility (HV)."""
    df_calc = df.copy()
    log_return = np.log(df_calc['close'] / df_calc['close'].shift(1))
    stddev = log_return.rolling(window=length).std()
    
    # Asumsi timeframe.multiplier == 1 per default (1 bar = 1 hari)
    # Ini adalah asumsi untuk menyederhanakan logika Pine Script
    per = 1 # Jika menggunakan Daily (D1)
    if 'T' in df.index[-1].strftime('%H'): # Asumsi intraday
        per = 1
    
    df_calc['HV'] = 100 * stddev * np.sqrt(annual / per)
    return df_calc

def calculate_volatility_stop(df, length=20, factor=2.0):
    """Menghitung Volatility Stop (VStop) yang stateful."""
    df_calc = df.copy()
    atr = _calculate_atr(df, period=length)
    atr_m = atr * factor

    vstop = pd.Series(index=df.index, dtype=float)
    uptrend = pd.Series(index=df.index, dtype=bool)

    if not df_calc.empty:
        max_price = df_calc['close'].iloc[0]
        min_price = df_calc['close'].iloc[0]
        uptrend_val = True
        stop_val = df_calc['close'].iloc[0]
        
        for i in range(1, len(df_calc)):
            max_price = max(max_price, df_calc['close'].iloc[i])
            min_price = min(min_price, df_calc['close'].iloc[i])
            stop_val = uptrend_val and max(stop_val, max_price - atr_m.iloc[i]) or \
                       not uptrend_val and min(stop_val, min_price + atr_m.iloc[i])
            
            prev_uptrend_val = uptrend_val
            uptrend_val = df_calc['close'].iloc[i] - stop_val >= 0.0

            if uptrend_val != prev_uptrend_val:
                max_price = df_calc['close'].iloc[i]
                min_price = df_calc['close'].iloc[i]
                stop_val = max_price - atr_m.iloc[i] if uptrend_val else min_price + atr_m.iloc[i]
            
            vstop.iloc[i] = stop_val
            uptrend.iloc[i] = uptrend_val
    
    df_calc['VStop'] = vstop
    df_calc['VStop_Uptrend'] = uptrend
    return df_calc

def calculate_rvi(df, length=10, period_ema=14, offset=0):
    """Menghitung Relative Volatility Index (RVI) dengan smoothing."""
    df_calc = df.copy()
    src = df_calc['close']
    stddev = src.rolling(window=length).std()
    
    change_up = stddev.where(src.diff() > 0, 0)
    change_down = stddev.where(src.diff() <= 0, 0)
    
    upper = change_up.ewm(span=period_ema, adjust=False).mean()
    lower = change_down.ewm(span=period_ema, adjust=False).mean()
    
    df_calc['RVI'] = 100 * upper / (upper + lower)
    df_calc['RVI'] = df_calc['RVI'].shift(offset)
    
    return df_calc

# --- Ekstraksi Laporan Volatility yang Efisien ---
def get_volatility_report(df, hv_length, vstop_length, vstop_factor, rvi_length, rvi_ema_length, rvi_offset):
    """Menggabungkan laporan dari semua indikator volatilitas."""
    df_hv = calculate_historical_volatility(df, length=hv_length)
    df_vstop = calculate_volatility_stop(df, length=vstop_length, factor=vstop_factor)
    df_rvi = calculate_rvi(df, length=rvi_length, period_ema=rvi_ema_length, offset=rvi_offset)

    row_hv = df_hv.iloc[-1]
    row_vstop = df_vstop.iloc[-1]
    row_rvi = df_rvi.iloc[-1]
    
    report = {
        "time": df.index[-1],
        "report_type": "volatility_data",
        "hv_value": row_hv['HV'] if not pd.isna(row_hv['HV']) else None,
        "vstop_value": row_vstop['VStop'] if not pd.isna(row_vstop['VStop']) else None,
        "vstop_uptrend": row_vstop['VStop_Uptrend'] if not pd.isna(row_vstop['VStop_Uptrend']) else None,
        "rvi_value": row_rvi['RVI'] if not pd.isna(row_rvi['RVI']) else None
    }
    
    return report

# --- Fungsi Utama ---
def main():
    try:
        config = load_config('config.yaml')
        general_config = config['general']
        assets_config = config['assets']
        vol_config = config.get('volatility_indicator', {})

        if general_config['symbol'] == 'auto':
            today = datetime.now().weekday()
            if today >= 0 and today <= 4:
                symbol = assets_config['weekday']
            else:
                symbol = assets_config['weekend']
        else:
            symbol = general_config['symbol']
        
        timeframe = general_config['timeframe']

        hv_length = vol_config.get('hv_length', 10)
        vstop_length = vol_config.get('vstop_length', 20)
        vstop_factor = vol_config.get('vstop_factor', 2.0)
        rvi_length = vol_config.get('rvi_length', 10)
        rvi_ema_length = vol_config.get('rvi_ema_length', 14)
        rvi_offset = vol_config.get('rvi_offset', 0)

        # Ambil bar yang cukup untuk semua perhitungan
        bars_needed = max(hv_length, vstop_length, rvi_length, rvi_ema_length) + 10
        initialize_mt5()
        df = get_candles(symbol, timeframe, bars=bars_needed)
        shutdown_mt5()

        vol_report = get_volatility_report(df, hv_length, vstop_length, vstop_factor, rvi_length, rvi_ema_length, rvi_offset)
        
        print(f"Laporan Indikator Volatility untuk {symbol} ({timeframe})")
        print("--------------------------------------------------")
        
        if vol_report:
            print(f"Time: {vol_report['time']:%Y-%m-%d %H:%M:%S}")
            print(f"Historical Volatility: {vol_report['hv_value']:.2f}%" if vol_report['hv_value'] is not None else "Historical Volatility: N/A")
            print(f"Volatility Stop: {vol_report['vstop_value']:.4f}" if vol_report['vstop_value'] is not None else "Volatility Stop: N/A")
            print(f"VStop Uptrend: {vol_report['vstop_uptrend']}" if vol_report['vstop_uptrend'] is not None else "VStop Uptrend: N/A")
            print(f"RVI: {vol_report['rvi_value']:.2f}" if vol_report['rvi_value'] is not None else "RVI: N/A")
        else:
            print("Tidak ada data Volatility yang valid pada bar terakhir.")

    except RuntimeError as e:
        print(f"Error: {e}")
    except FileNotFoundError as e:
        print(f"Error: {e}")
    except ValueError as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()