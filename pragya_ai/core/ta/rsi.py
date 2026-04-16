# pragya_ai/core/ta/rsi.py

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

# --- Logika Perhitungan Indikator RSI ---
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

def _detect_pivots(series, lookback_left, lookback_right):
    """Mendeteksi pivot high/low seperti Pine Script ta.pivothigh/low."""
    is_high_pivot = series.rolling(window=lookback_left + lookback_right + 1, center=True).apply(lambda x: x.iloc[lookback_left] == x.max(), raw=False)
    is_low_pivot = series.rolling(window=lookback_left + lookback_right + 1, center=True).apply(lambda x: x.iloc[lookback_left] == x.min(), raw=False)
    
    high_pivots = series[is_high_pivot == 1].dropna()
    low_pivots = series[is_low_pivot == 1].dropna()
    
    return high_pivots, low_pivots

def calculate_rsi_advanced(df, rsi_length, ma_type, ma_length, bb_mult, divergence=False, lookback_left=5, lookback_right=5, range_upper=60, range_lower=5):
    """Menghitung RSI dengan opsi smoothing, BB, dan divergence."""
    df_calc = df.copy()
    
    # Perhitungan RSI dasar
    change = df_calc['close'].diff()
    up = change.where(change > 0, 0)
    down = -change.where(change < 0, 0)
    avg_gain = up.ewm(span=rsi_length, adjust=False).mean()
    avg_loss = down.ewm(span=rsi_length, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-9)
    df_calc['RSI'] = 100 - (100 / (1 + rs))
    
    # Perhitungan Smoothing dan Bollinger Bands
    if ma_type != "None":
        volume = df_calc.get('real_volume', None)
        df_calc['smoothing_ma'] = _calculate_ma(df_calc['RSI'], ma_length, ma_type, volume)
        if ma_type == "SMA + Bollinger Bands":
            stdev = df_calc['RSI'].rolling(window=ma_length).std()
            df_calc['bb_upper'] = df_calc['smoothing_ma'] + stdev * bb_mult
            df_calc['bb_lower'] = df_calc['smoothing_ma'] - stdev * bb_mult

    # Perhitungan Divergensi
    df_calc['bullish_divergence'] = False
    df_calc['bearish_divergence'] = False
    if divergence:
        high_pivots, low_pivots = _detect_pivots(df_calc['high'], lookback_left, lookback_right)
        rsi_high_pivots, rsi_low_pivots = _detect_pivots(df_calc['RSI'], lookback_left, lookback_right)
        
        # Logika divergen
        # ... (kompleks untuk diimplementasikan di sini, akan disederhanakan)
        # Sederhanakan: cek bullish dan bearish divergen di bar terakhir
        if len(rsi_low_pivots) > 1 and len(low_pivots) > 1:
            if rsi_low_pivots.index[-1] > rsi_low_pivots.index[-2] and low_pivots.index[-1] < low_pivots.index[-2]:
                 df_calc.loc[df_calc.index[-1], 'bullish_divergence'] = True
        
        if len(rsi_high_pivots) > 1 and len(high_pivots) > 1:
            if rsi_high_pivots.index[-1] < rsi_high_pivots.index[-2] and high_pivots.index[-1] > high_pivots.index[-2]:
                 df_calc.loc[df_calc.index[-1], 'bearish_divergence'] = True
    
    return df_calc

# --- Ekstraksi Laporan RSI yang Efisien ---
def get_rsi_report(df, rsi_length=14, ma_type="SMA", ma_length=14, bb_mult=2.0, divergence=False):
    """Mengembalikan laporan mentah RSI dari bar terakhir."""
    df_rsi = calculate_rsi_advanced(df, rsi_length, ma_type, ma_length, bb_mult, divergence)
    row = df_rsi.iloc[-1]
    
    if pd.isna(row['RSI']):
        return None
    
    report = {
        "time": row.name,
        "rsi_value": row['RSI'],
        "report_type": "rsi_data"
    }
    if 'smoothing_ma' in df_rsi.columns and not pd.isna(row['smoothing_ma']):
        report['smoothing_ma'] = row['smoothing_ma']
    if 'bb_upper' in df_rsi.columns and not pd.isna(row['bb_upper']):
        report['bb_upper'] = row['bb_upper']
        report['bb_lower'] = row['bb_lower']
    if divergence:
        report['bullish_divergence'] = row['bullish_divergence']
        report['bearish_divergence'] = row['bearish_divergence']
        
    return report

# --- Fungsi Utama ---
def main():
    try:
        config = load_config('config.yaml')
        general_config = config['general']
        assets_config = config['assets']
        rsi_config = config.get('rsi_indicator', {})

        if general_config['symbol'] == 'auto':
            today = datetime.now().weekday()
            if today >= 0 and today <= 4:
                symbol = assets_config['weekday']
            else:
                symbol = assets_config['weekend']
        else:
            symbol = general_config['symbol']
        
        timeframe = general_config['timeframe']
        
        rsi_length = rsi_config.get('rsi_length', 14)
        ma_type = rsi_config.get('smoothing_ma_type', "None")
        ma_length = rsi_config.get('smoothing_ma_length', 14)
        bb_mult = rsi_config.get('bb_stddev', 2.0)
        divergence = rsi_config.get('calculate_divergence', False)
        
        # Ambil bar yang cukup untuk semua perhitungan
        bars_needed = max(rsi_length, ma_length, 2)
        bars = max(500, bars_needed + 52) # Tambahkan 52 bar untuk offset Ichimoku jika di masa depan

        initialize_mt5()
        df = get_candles(symbol, timeframe, bars=bars)
        shutdown_mt5()

        rsi_report = get_rsi_report(df, rsi_length, ma_type, ma_length, bb_mult, divergence)
        
        print(f"Laporan Indikator RSI (Advanced) untuk {symbol} ({timeframe})")
        print("--------------------------------------------------")
        
        if rsi_report:
            print(f"Time: {rsi_report['time']:%Y-%m-%d %H:%M:%S}")
            print(f"RSI Value: {rsi_report['rsi_value']:.2f}")
            if 'smoothing_ma' in rsi_report:
                print(f"Smoothing MA: {rsi_report['smoothing_ma']:.2f}")
            if 'bb_upper' in rsi_report:
                print(f"BB Upper: {rsi_report['bb_upper']:.2f}")
                print(f"BB Lower: {rsi_report['bb_lower']:.2f}")
            if divergence:
                print(f"Bullish Divergence: {rsi_report.get('bullish_divergence', False)}")
                print(f"Bearish Divergence: {rsi_report.get('bearish_divergence', False)}")
        else:
            print("Tidak ada data RSI yang valid pada bar terakhir.")

    except RuntimeError as e:
        print(f"Error: {e}")
    except FileNotFoundError as e:
        print(f"Error: {e}")
    except ValueError as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()