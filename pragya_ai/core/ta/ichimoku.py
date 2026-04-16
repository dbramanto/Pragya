# pragya_ai/core/ta/ichimoku.py

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

# --- Logika Perhitungan Indikator Ichimoku ---
def _calculate_donchian_channel(high, low, length):
    """Menghitung Donchian Channel (rata-rata highest high dan lowest low)."""
    highest_high = high.rolling(window=length).max()
    lowest_low = low.rolling(window=length).min()
    return (highest_high + lowest_low) / 2

def calculate_ichimoku(df, conversion_periods=9, base_periods=26, lagging_span2_periods=52, displacement=26):
    """Menghitung indikator Ichimoku Kinko Hyo."""
    df_calc = df.copy()
    high = df_calc['high']
    low = df_calc['low']
    close = df_calc['close']

    # Komponen Ichimoku
    df_calc['tenkan_sen'] = _calculate_donchian_channel(high, low, conversion_periods)
    df_calc['kijun_sen'] = _calculate_donchian_channel(high, low, base_periods)
    
    df_calc['lead_line_1'] = ((df_calc['tenkan_sen'] + df_calc['kijun_sen']) / 2).shift(displacement)
    df_calc['lead_line_2'] = _calculate_donchian_channel(high, low, lagging_span2_periods).shift(displacement)
    df_calc['lagging_span'] = close.shift(-displacement)

    return df_calc

# --- Ekstraksi Laporan Ichimoku yang Efisien ---
def get_ichimoku_report(df, conversion_periods=9, base_periods=26, lagging_span2_periods=52, displacement=26):
    """Mengembalikan laporan mentah Ichimoku dari bar terakhir."""
    df_ichimoku = calculate_ichimoku(df, conversion_periods, base_periods, lagging_span2_periods, displacement)
    row = df_ichimoku.iloc[-1]
    
    if pd.isna(row['tenkan_sen']) or pd.isna(row['kijun_sen']):
        return None
    
    return {
        "time": row.name,
        "tenkan_sen": row["tenkan_sen"],
        "kijun_sen": row["kijun_sen"],
        "senkou_span_a": row["lead_line_1"],
        "senkou_span_b": row["lead_line_2"],
        "chikou_span": row["lagging_span"],
        "report_type": "ichimoku_data"
    }

# --- Fungsi Utama ---
def main():
    try:
        config = load_config('config.yaml')
        general_config = config['general']
        assets_config = config['assets']
        ichimoku_config = config.get('ichimoku_indicator', {})

        if general_config['symbol'] == 'auto':
            today = datetime.now().weekday()
            if today >= 0 and today <= 4:
                symbol = assets_config['weekday']
            else:
                symbol = assets_config['weekend']
        else:
            symbol = general_config['symbol']
        
        timeframe = general_config['timeframe']
        
        conversion_periods = ichimoku_config.get('conversion_periods', 9)
        base_periods = ichimoku_config.get('base_periods', 26)
        lagging_span2_periods = ichimoku_config.get('lagging_span2_periods', 52)
        displacement = ichimoku_config.get('displacement', 26)

        initialize_mt5()
        # Perlu bar lebih banyak untuk Ichimoku
        bars = max(500, lagging_span2_periods + displacement + 1)
        df = get_candles(symbol, timeframe, bars=bars)
        shutdown_mt5()

        ichimoku_report = get_ichimoku_report(df, conversion_periods, base_periods, lagging_span2_periods, displacement)
        
        print(f"Laporan Indikator Ichimoku untuk {symbol} ({timeframe})")
        print("--------------------------------------------------")
        
        if ichimoku_report:
            print(f"Time: {ichimoku_report['time']:%Y-%m-%d %H:%M:%S}")
            print(f"Tenkan Sen: {ichimoku_report['tenkan_sen']:.4f}")
            print(f"Kijun Sen: {ichimoku_report['kijun_sen']:.4f}")
            print(f"Senkou Span A: {ichimoku_report['senkou_span_a']:.4f}")
            print(f"Senkou Span B: {ichimoku_report['senkou_span_b']:.4f}")
            print(f"Chikou Span: {ichimoku_report['chikou_span']:.4f}")
        else:
            print("Tidak ada data Ichimoku yang valid pada bar terakhir.")

    except RuntimeError as e:
        print(f"Error: {e}")
    except FileNotFoundError as e:
        print(f"Error: {e}")
    except ValueError as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()