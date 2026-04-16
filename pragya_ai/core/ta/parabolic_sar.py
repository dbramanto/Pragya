# core/ta/parabolic_sar.py

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

# --- Logika Perhitungan Indikator Parabolic SAR ---
def calculate_parabolic_sar(df, start=0.02, increment=0.02, maximum=0.2):
    """
    Menghitung Parabolic SAR dengan logika stateful.
    """
    df_calc = df.copy()
    
    # Inisialisasi Series dengan tipe data yang benar
    df_calc['SAR'] = np.nan
    df_calc['uptrend'] = np.nan
    df_calc['EP'] = np.nan
    df_calc['AF'] = np.nan
    df_calc['uptrend'] = df_calc['uptrend'].astype(bool)

    # Logika stateful dalam loop
    uptrend = False
    EP = 0.0
    SAR = 0.0
    AF = start
    
    if len(df_calc) > 1:
        # Inisialisasi bar pertama (bar_index = 1 di Pine Script)
        if df_calc['close'].iloc[1] > df_calc['close'].iloc[0]:
            uptrend = True
            EP = df_calc['high'].iloc[1]
            SAR = df_calc['low'].iloc[0]
        else:
            uptrend = False
            EP = df_calc['low'].iloc[1]
            SAR = df_calc['high'].iloc[0]
            
        df_calc.loc[df_calc.index[1], 'uptrend'] = uptrend
        df_calc.loc[df_calc.index[1], 'EP'] = EP
        df_calc.loc[df_calc.index[1], 'SAR'] = SAR
        df_calc.loc[df_calc.index[1], 'AF'] = AF

        for i in range(2, len(df_calc)):
            # Update SAR
            SAR = SAR + AF * (EP - SAR)
            
            # Deteksi Reversal
            if uptrend:
                if SAR > df_calc['low'].iloc[i]:
                    uptrend = False
                    SAR = max(EP, df_calc['high'].iloc[i])
                    EP = df_calc['low'].iloc[i]
                    AF = start
                
                SAR = min(SAR, df_calc['low'].iloc[i-1])
                if i > 1:
                    SAR = min(SAR, df_calc['low'].iloc[i-2])
            else:
                if SAR < df_calc['high'].iloc[i]:
                    uptrend = True
                    SAR = min(EP, df_calc['low'].iloc[i])
                    EP = df_calc['high'].iloc[i]
                    AF = start

                SAR = max(SAR, df_calc['high'].iloc[i-1])
                if i > 1:
                    SAR = max(SAR, df_calc['high'].iloc[i-2])

            # Update EP dan AF
            if uptrend and df_calc['high'].iloc[i] > EP:
                EP = df_calc['high'].iloc[i]
                AF = min(AF + increment, maximum)
            elif not uptrend and df_calc['low'].iloc[i] < EP:
                EP = df_calc['low'].iloc[i]
                AF = min(AF + increment, maximum)
            
            df_calc.loc[df_calc.index[i], 'SAR'] = SAR
            df_calc.loc[df_calc.index[i], 'uptrend'] = uptrend
            df_calc.loc[df_calc.index[i], 'EP'] = EP
            df_calc.loc[df_calc.index[i], 'AF'] = AF

    return df_calc

# --- Ekstraksi Laporan SAR yang Efisien ---
def get_sar_report(df, start=0.02, increment=0.02, maximum=0.2):
    """Mengembalikan laporan mentah Parabolic SAR dari bar terakhir."""
    df_sar = calculate_parabolic_sar(df, start, increment, maximum)
    row = df_sar.iloc[-1]
    
    if pd.isna(row['SAR']) or pd.isna(row['uptrend']):
        return None
    
    trend = "Uptrend" if row['uptrend'] else "Downtrend"
    
    return {
        "time": row.name,
        "sar_value": row['SAR'],
        "trend": trend,
        "report_type": "sar_data"
    }

# --- Fungsi Utama ---
def main():
    try:
        config = load_config('config.yaml')
        general_config = config['general']
        assets_config = config['assets']
        sar_config = config.get('sar_indicator', {})

        if general_config['symbol'] == 'auto':
            today = datetime.now().weekday()
            if today >= 0 and today <= 4:
                symbol = assets_config['weekday']
            else:
                symbol = assets_config['weekend']
        else:
            symbol = general_config['symbol']
        
        timeframe = general_config['timeframe']
        
        start = sar_config.get('start', 0.02)
        increment = sar_config.get('increment', 0.02)
        maximum = sar_config.get('maximum', 0.2)

        initialize_mt5()
        df = get_candles(symbol, timeframe)
        shutdown_mt5()

        sar_report = get_sar_report(df, start, increment, maximum)
        
        print(f"Laporan Indikator Parabolic SAR untuk {symbol} ({timeframe})")
        print("--------------------------------------------------")
        
        if sar_report:
            print(f"Time: {sar_report['time']:%Y-%m-%d %H:%M:%S}")
            print(f"SAR Value: {sar_report['sar_value']:.4f}")
            print(f"Current Trend: {sar_report['trend']}")
        else:
            print("Tidak ada data SAR yang valid pada bar terakhir.")

    except RuntimeError as e:
        print(f"Error: {e}")
    except FileNotFoundError as e:
        print(f"Error: {e}")
    except ValueError as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()