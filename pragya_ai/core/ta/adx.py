# core/ta/adx.py

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

# --- Logika Perhitungan Indikator ADX ---
def calculate_adx(df, adxlen=14, dilen=14):
    """
    Menghitung Average Directional Index (ADX) menggunakan logika RMA (Wilder's Smoothing).
    """
    df_calc = df.copy()
    high = df_calc["high"]
    low = df_calc["low"]
    close = df_calc["close"]

    # Menghitung Directional Movement (DM)
    up = high.diff()
    down = -low.diff()
    
    # Menghitung +DM dan -DM
    plusDM = np.where((up > down) & (up > 0), up, 0)
    minusDM = np.where((down > up) & (down > 0), down, 0)
    
    # Menghitung True Range (TR)
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    df_calc["TR"] = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)

    # Implementasi ta.rma (Wilder's Smoothing)
    def rma(series, length):
        alpha = 1 / length
        return series.ewm(alpha=alpha, adjust=False).mean()

    # Smoothing +DM, -DM, dan TR dengan RMA
    smoothed_plusDM = rma(pd.Series(plusDM), dilen)
    smoothed_minusDM = rma(pd.Series(minusDM), dilen)
    smoothed_truerange = rma(df_calc["TR"], dilen)

    # Menghitung DI+ dan DI- (menggunakan .replace(np.inf, 0) untuk fixnan)
    plus_di = (100 * smoothed_plusDM / smoothed_truerange).replace(np.inf, 0).fillna(0)
    minus_di = (100 * smoothed_minusDM / smoothed_truerange).replace(np.inf, 0).fillna(0)
    
    # Menghitung DX
    sum_di = plus_di + minus_di
    dx = (100 * abs(plus_di - minus_di) / sum_di).replace(np.inf, 0).fillna(0)

    # Menghitung ADX (Smoothing DX dengan RMA)
    adx = rma(dx, adxlen)

    df_calc["ADX"] = adx
    df_calc["+DI"] = plus_di
    df_calc["-DI"] = minus_di
    return df_calc

# --- Ekstraksi Laporan Mentah ADX ---
def get_adx_report(df, adxlen=14, dilen=14):
    """
    Mengembalikan laporan mentah ADX dari bar terakhir.
    """
    df_adx = calculate_adx(df, adxlen, dilen)
    row = df_adx.iloc[-1]
    
    if pd.isna(row["ADX"]) or pd.isna(row["+DI"]) or pd.isna(row["-DI"]):
        return None
    
    return {
        "time": row.name,
        "adx_value": row["ADX"],
        "plus_di": row["+DI"],
        "minus_di": row["-DI"],
        "report_type": "adx_data"
    }

# --- Fungsi Utama ---
def main():
    try:
        config = load_config('config.yaml')
        general_config = config['general']
        assets_config = config['assets']

        if general_config['symbol'] == 'auto':
            today = datetime.now().weekday()
            if today >= 0 and today <= 4:
                symbol = assets_config['weekday']
            else:
                symbol = assets_config['weekend']
        else:
            symbol = general_config['symbol']
        
        timeframe = general_config['timeframe']
        adx_len = 14
        di_len = 14

        initialize_mt5()
        df = get_candles(symbol, timeframe)
        shutdown_mt5()

        adx_report = get_adx_report(df, adx_len, di_len)
        
        print(f"Laporan Indikator ADX (RMA) untuk {symbol} ({timeframe})")
        print("--------------------------------------------------")
        
        if adx_report:
            print(f"Time: {adx_report['time']:%Y-%m-%d %H:%M:%S}")
            print(f"ADX Value: {adx_report['adx_value']:.2f}")
            print(f"+DI: {adx_report['plus_di']:.2f}")
            print(f"-DI: {adx_report['minus_di']:.2f}")
        else:
            print("Tidak ada data ADX yang valid pada bar terakhir.")

    except RuntimeError as e:
        print(f"Error: {e}")
    except FileNotFoundError as e:
        print(f"Error: {e}")
    except ValueError as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()