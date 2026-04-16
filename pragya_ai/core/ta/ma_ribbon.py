# core/ta/ma_ribbon.py

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

# --- Logika Perhitungan Indikator MA Ribbon ---
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
    return series.rolling(window=length).mean()

def calculate_ma_ribbon(df, ma_settings):
    """
    Menghitung MA Ribbon dengan konfigurasi dinamis.
    ma_settings adalah list of dicts: [{'length': 20, 'type': 'SMA'}, ...]
    """
    df_calc = df.copy()
    src = df_calc['close']
    volume = df_calc.get('real_volume', None)
    
    ma_reports = {}
    for i, setting in enumerate(ma_settings):
        ma_label = f"MA{i+1}"
        length = setting['length']
        ma_type = setting['type']
        
        df_calc[ma_label] = _calculate_ma(src, length, ma_type, volume)
        ma_reports[ma_label] = df_calc[ma_label]
        
    return df_calc

# --- Ekstraksi Laporan MA Ribbon yang Efisien ---
def get_ma_ribbon_report(df, ma_settings):
    """Mengembalikan laporan mentah MA Ribbon dari bar terakhir."""
    df_ribbon = calculate_ma_ribbon(df, ma_settings)
    row = df_ribbon.iloc[-1]
    
    report = {
        "time": row.name,
        "report_type": "ma_ribbon_data",
        "mas": []
    }
    
    for i, setting in enumerate(ma_settings):
        ma_label = f"MA{i+1}"
        if ma_label in df_ribbon.columns and not pd.isna(row[ma_label]):
            report["mas"].append({
                "label": ma_label,
                "type": setting['type'],
                "length": setting['length'],
                "value": row[ma_label]
            })
            
    return report if report["mas"] else None

# --- Fungsi Utama ---
def main():
    try:
        config = load_config('config.yaml')
        general_config = config['general']
        assets_config = config['assets']
        ma_ribbon_config = config.get('ma_ribbon_indicator', {})

        if general_config['symbol'] == 'auto':
            today = datetime.now().weekday()
            if today >= 0 and today <= 4:
                symbol = assets_config['weekday']
            else:
                symbol = assets_config['weekend']
        else:
            symbol = general_config['symbol']
        
        timeframe = general_config['timeframe']
        
        ma_settings = ma_ribbon_config.get('ma_settings', [
            {'length': 20, 'type': 'SMA'},
            {'length': 50, 'type': 'SMA'},
            {'length': 100, 'type': 'SMA'},
            {'length': 200, 'type': 'SMA'},
        ])
        
        max_length = max(s['length'] for s in ma_settings)
        bars = max(500, max_length + 10)

        initialize_mt5()
        df = get_candles(symbol, timeframe, bars=bars)
        shutdown_mt5()

        ma_ribbon_report = get_ma_ribbon_report(df, ma_settings)
        
        print(f"Laporan Indikator MA Ribbon untuk {symbol} ({timeframe})")
        print("--------------------------------------------------")
        
        if ma_ribbon_report:
            print(f"Time: {ma_ribbon_report['time']:%Y-%m-%d %H:%M:%S}")
            for ma_data in ma_ribbon_report['mas']:
                print(f"{ma_data['label']}: {ma_data['value']:.4f} ({ma_data['type']}, {ma_data['length']})")
        else:
            print("Tidak ada data MA Ribbon yang valid pada bar terakhir.")

    except RuntimeError as e:
        print(f"Error: {e}")
    except FileNotFoundError as e:
        print(f"Error: {e}")
    except ValueError as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()