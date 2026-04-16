# core/ta/keltner.py

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

# --- Logika Perhitungan Indikator Keltner Channels ---
def _calculate_ma(series, length, ma_type):
    """Fungsi pembantu untuk menghitung SMA atau EMA."""
    if ma_type == "SMA":
        return series.rolling(window=length).mean()
    elif ma_type == "EMA":
        return series.ewm(span=length, adjust=False).mean()
    return series.rolling(window=length).mean() # Default

def _calculate_tr(df):
    """Menghitung True Range (TR)."""
    tr1 = df['high'] - df['low']
    tr2 = (df['high'] - df['close'].shift()).abs()
    tr3 = (df['low'] - df['close'].shift()).abs()
    return pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)

def _calculate_atr(df, length):
    """Menghitung Average True Range (ATR)."""
    tr = _calculate_tr(df)
    return tr.ewm(span=length, adjust=False).mean()

def calculate_keltner_channels(df, length=20, mult=2.0, exp=True, bands_style="Average True Range", atrlength=10):
    """Menghitung Keltner Channels."""
    df_calc = df.copy()
    src = df_calc['close']
    
    # Hitung basis (garis tengah)
    ma_type = "EMA" if exp else "SMA"
    df_calc['basis'] = _calculate_ma(src, length, ma_type)
    
    # Hitung pita volatilitas
    if bands_style == "Average True Range":
        volatility_band = _calculate_atr(df, atrlength)
    elif bands_style == "True Range":
        volatility_band = _calculate_tr(df).rolling(window=length).mean()
    elif bands_style == "Range":
        range_ma = (df['high'] - df['low']).rolling(window=length).mean()
        volatility_band = range_ma
    
    df_calc['upper'] = df_calc['basis'] + volatility_band * mult
    df_calc['lower'] = df_calc['basis'] - volatility_band * mult
    df_calc['basis_type'] = ma_type
    
    return df_calc

# --- Ekstraksi Laporan Keltner yang Efisien ---
def get_keltner_report(df, length=20, mult=2.0, exp=True, bands_style="Average True Range", atrlength=10):
    """Mengembalikan laporan mentah Keltner Channels dari bar terakhir."""
    df_keltner = calculate_keltner_channels(df, length, mult, exp, bands_style, atrlength)
    row = df_keltner.iloc[-1]
    
    if pd.isna(row['basis']) or pd.isna(row['upper']) or pd.isna(row['lower']):
        return None
    
    return {
        "time": row.name,
        "basis": row['basis'],
        "upper": row['upper'],
        "lower": row['lower'],
        "basis_type": row['basis_type'],
        "report_type": "keltner_data"
    }

# --- Fungsi Utama ---
def main():
    try:
        config = load_config('config.yaml')
        general_config = config['general']
        assets_config = config['assets']
        keltner_config = config.get('keltner_indicator', {})

        if general_config['symbol'] == 'auto':
            today = datetime.now().weekday()
            if today >= 0 and today <= 4:
                symbol = assets_config['weekday']
            else:
                symbol = assets_config['weekend']
        else:
            symbol = general_config['symbol']
        
        timeframe = general_config['timeframe']
        
        length = keltner_config.get('length', 20)
        mult = keltner_config.get('multiplier', 2.0)
        exp = keltner_config.get('use_exponential_ma', True)
        bands_style = keltner_config.get('bands_style', "Average True Range")
        atrlength = keltner_config.get('atr_length', 10)

        bars_needed = max(length, atrlength) + 2
        initialize_mt5()
        df = get_candles(symbol, timeframe, bars=bars_needed)
        shutdown_mt5()

        keltner_report = get_keltner_report(df, length, mult, exp, bands_style, atrlength)
        
        print(f"Laporan Indikator Keltner Channels untuk {symbol} ({timeframe})")
        print("--------------------------------------------------")
        
        if keltner_report:
            print(f"Time: {keltner_report['time']:%Y-%m-%d %H:%M:%S}")
            print(f"Basis ({keltner_report['basis_type']}): {keltner_report['basis']:.4f}")
            print(f"Upper: {keltner_report['upper']:.4f}")
            print(f"Lower: {keltner_report['lower']:.4f}")
        else:
            print("Tidak ada data Keltner Channels yang valid.")

    except RuntimeError as e:
        print(f"Error: {e}")
    except FileNotFoundError as e:
        print(f"Error: {e}")
    except ValueError as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()