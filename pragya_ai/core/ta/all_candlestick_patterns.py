# core/ta/candlestick/all_candlestick_patterns.py

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

# --- Perhitungan Properti Candlestick ---
def calculate_properties(df, trend_rule="SMA50"):
    """Menghitung semua properti lilin yang dibutuhkan untuk deteksi pola."""
    if df.empty:
        return df.copy()

    df_calc = df.copy()
    df_calc['body_hi'] = np.maximum(df_calc['close'], df_calc['open'])
    df_calc['body_lo'] = np.minimum(df_calc['close'], df_calc['open'])
    df_calc['body'] = df_calc['body_hi'] - df_calc['body_lo']
    df_calc['up_shadow'] = df_calc['high'] - df_calc['body_hi']
    df_calc['dn_shadow'] = df_calc['body_lo'] - df_calc['low']
    df_calc['range'] = df_calc['high'] - df_calc['low']
    df_calc['body_avg'] = df_calc['body'].ewm(span=14).mean()
    df_calc['is_white_body'] = df_calc['close'] > df_calc['open']
    df_calc['is_black_body'] = df_calc['close'] < df_calc['open']
    df_calc['is_long_body'] = df_calc['body'] > df_calc['body_avg']
    df_calc['is_small_body'] = df_calc['body'] < df_calc['body_avg']
    df_calc['body_middle'] = df_calc['body'] / 2 + df_calc['body_lo']
    
    C_DojiBodyPercent = 5.0
    df_calc['is_doji_body'] = (df_calc['range'] > 0) & (df_calc['body'] <= (df_calc['range'] * C_DojiBodyPercent / 100))
    df_calc['is_doji'] = df_calc['is_doji_body']
    
    if trend_rule == "SMA50":
        df_calc['sma50'] = df_calc['close'].rolling(window=50).mean()
        df_calc['downtrend'] = (df_calc['close'] < df_calc['sma50'])
        df_calc['uptrend'] = (df_calc['close'] > df_calc['sma50'])
    elif trend_rule == "SMA50, SMA200":
        df_calc['sma50'] = df_calc['close'].rolling(window=50).mean()
        df_calc['sma200'] = df_calc['close'].rolling(window=200).mean()
        df_calc['downtrend'] = (df_calc['close'] < df_calc['sma50']) & (df_calc['sma50'] < df_calc['sma200'])
        df_calc['uptrend'] = (df_calc['close'] > df_calc['sma50']) & (df_calc['sma50'] > df_calc['sma200'])
    else:
        df_calc['downtrend'] = False
        df_calc['uptrend'] = False
        
    return df_calc

def _get_signal_type(pattern_name):
    """Menentukan tipe sinyal dari nama pola."""
    name_lower = pattern_name.lower()
    if 'bullish' in name_lower or ('white' in name_lower and 'spinning' not in name_lower and 'marubozu' in name_lower):
        return 'bullish'
    elif 'bearish' in name_lower or ('black' in name_lower and 'spinning' not in name_lower and 'marubozu' in name_lower):
        return 'bearish'
    return 'neutral'

# --- Logika Deteksi Pola ---
def _get_pattern_detectors():
    """Mengembalikan daftar detektor pola dengan kondisi dan tipe sinyal."""
    C_Factor = 2.0
    C_ShadowPercent = 5.0
    C_SpinningTopPercent = 34.0
    C_MarubozuShadowPercent = 5.0

    return {
        "Abandoned Baby Bullish": lambda d, i: d.iloc[i-2]['downtrend'] and d.iloc[i-2]['is_black_body'] and d.iloc[i-1]['is_doji_body'] and d.iloc[i]['is_white_body'] and d.iloc[i-2]['low'] > d.iloc[i-1]['high'] and d.iloc[i-1]['high'] < d.iloc[i]['low'],
        "Dragonfly Doji Bullish": lambda d, i: d.iloc[i]['is_doji_body'] and d.iloc[i]['up_shadow'] <= d.iloc[i]['body'],
        "Engulfing Bullish": lambda d, i: d.iloc[i-1]['downtrend'] and d.iloc[i]['is_white_body'] and d.iloc[i]['is_long_body'] and d.iloc[i-1]['is_black_body'] and d.iloc[i-1]['is_small_body'] and d.iloc[i]['close'] >= d.iloc[i-1]['open'] and d.iloc[i]['open'] <= d.iloc[i-1]['close'],
        "Hammer Bullish": lambda d, i: d.iloc[i]['downtrend'] and d.iloc[i]['is_small_body'] and d.iloc[i]['body'] > 0 and d.iloc[i]['dn_shadow'] >= C_Factor * d.iloc[i]['body'] and d.iloc[i]['up_shadow'] <= (C_ShadowPercent / 100 * d.iloc[i]['body']),
        "Harami Bullish": lambda d, i: d.iloc[i-1]['downtrend'] and d.iloc[i-1]['is_long_body'] and d.iloc[i-1]['is_black_body'] and d.iloc[i]['is_white_body'] and d.iloc[i]['is_small_body'] and d.iloc[i]['high'] <= d.iloc[i-1]['body_hi'] and d.iloc[i]['low'] >= d.iloc[i-1]['body_lo'],
        "Harami Cross Bullish": lambda d, i: d.iloc[i-1]['downtrend'] and d.iloc[i-1]['is_long_body'] and d.iloc[i-1]['is_black_body'] and d.iloc[i]['is_doji_body'] and d.iloc[i]['high'] <= d.iloc[i-1]['body_hi'] and d.iloc[i]['low'] >= d.iloc[i-1]['body_lo'],
        "Inverted Hammer Bullish": lambda d, i: d.iloc[i]['downtrend'] and d.iloc[i]['is_small_body'] and d.iloc[i]['body'] > 0 and d.iloc[i]['up_shadow'] >= C_Factor * d.iloc[i]['body'] and d.iloc[i]['dn_shadow'] <= (C_ShadowPercent / 100 * d.iloc[i]['body']),
        "Kicking Bullish": lambda d, i: d.iloc[i-1]['is_black_body'] and d.iloc[i-1]['is_long_body'] and d.iloc[i-1]['up_shadow'] <= C_MarubozuShadowPercent/100*d.iloc[i-1]['body'] and d.iloc[i-1]['dn_shadow'] <= C_MarubozuShadowPercent/100*d.iloc[i-1]['body'] and d.iloc[i]['is_white_body'] and d.iloc[i]['is_long_body'] and d.iloc[i]['up_shadow'] <= C_MarubozuShadowPercent/100*d.iloc[i]['body'] and d.iloc[i]['dn_shadow'] <= C_MarubozuShadowPercent/100*d.iloc[i]['body'] and d.iloc[i-1]['high'] < d.iloc[i]['low'],
        "Long Lower Shadow Bullish": lambda d, i: d.iloc[i]['dn_shadow'] > d.iloc[i]['range']/100*75.0,
        "Marubozu White Bullish": lambda d, i: d.iloc[i]['is_white_body'] and d.iloc[i]['is_long_body'] and d.iloc[i]['up_shadow'] <= C_MarubozuShadowPercent/100*d.iloc[i]['body'] and d.iloc[i]['dn_shadow'] <= C_MarubozuShadowPercent/100*d.iloc[i]['body'],
        "Morning Doji Star Bullish": lambda d, i: d.iloc[i-2]['is_long_body'] and d.iloc[i-1]['is_doji_body'] and d.iloc[i]['is_long_body'] and d.iloc[i-2]['downtrend'] and d.iloc[i-2]['is_black_body'] and d.iloc[i]['is_white_body'] and d.iloc[i-1]['body_hi'] < d.iloc[i-2]['body_lo'] and d.iloc[i]['body_lo'] > d.iloc[i-1]['body_hi'] and d.iloc[i]['close'] >= d.iloc[i-2]['body_middle'],
        "Morning Star Bullish": lambda d, i: d.iloc[i-2]['is_long_body'] and d.iloc[i-1]['is_small_body'] and d.iloc[i]['is_long_body'] and d.iloc[i-2]['downtrend'] and d.iloc[i-2]['is_black_body'] and d.iloc[i]['is_white_body'] and d.iloc[i-1]['body_hi'] < d.iloc[i-2]['body_lo'] and d.iloc[i]['body_lo'] > d.iloc[i-1]['body_hi'] and d.iloc[i]['close'] >= d.iloc[i-2]['body_middle'],
        "Piercing Bullish": lambda d, i: d.iloc[i-1]['downtrend'] and d.iloc[i-1]['is_black_body'] and d.iloc[i-1]['is_long_body'] and d.iloc[i]['is_white_body'] and d.iloc[i]['open'] <= d.iloc[i-1]['low'] and d.iloc[i]['close'] > d.iloc[i-1]['body_middle'] and d.iloc[i]['close'] < d.iloc[i-1]['open'],
        "Rising Three Methods Bullish": lambda d, i: d.iloc[i-4]['uptrend'] and d.iloc[i-4]['is_long_body'] and d.iloc[i-4]['is_white_body'] and d.iloc[i-3]['is_small_body'] and d.iloc[i-3]['is_black_body'] and d.iloc[i-3]['open'] < d.iloc[i-4]['high'] and d.iloc[i-3]['close'] > d.iloc[i-4]['low'] and d.iloc[i-2]['is_small_body'] and d.iloc[i-2]['is_black_body'] and d.iloc[i-2]['open'] < d.iloc[i-4]['high'] and d.iloc[i-2]['close'] > d.iloc[i-4]['low'] and d.iloc[i-1]['is_small_body'] and d.iloc[i-1]['is_black_body'] and d.iloc[i-1]['open'] < d.iloc[i-4]['high'] and d.iloc[i-1]['close'] > d.iloc[i-4]['low'] and d.iloc[i]['is_long_body'] and d.iloc[i]['is_white_body'] and d.iloc[i]['close'] > d.iloc[i-4]['close'],
        "Rising Window Bullish": lambda d, i: d.iloc[i-1]['uptrend'] and (d.iloc[i-1]['range']!=0 and d.iloc[i]['range']!=0) and d.iloc[i]['low'] > d.iloc[i-1]['high'],
        "Three White Soldiers Bullish": lambda d, i: d.iloc[i]['is_long_body'] and d.iloc[i-1]['is_long_body'] and d.iloc[i-2]['is_long_body'] and d.iloc[i]['is_white_body'] and d.iloc[i-1]['is_white_body'] and d.iloc[i-2]['is_white_body'] and d.iloc[i]['close'] > d.iloc[i-1]['close'] and d.iloc[i-1]['close'] > d.iloc[i-2]['close'] and d.iloc[i]['open'] < d.iloc[i-1]['close'] and d.iloc[i]['open'] > d.iloc[i-1]['open'] and d.iloc[i-1]['open'] < d.iloc[i-2]['close'] and d.iloc[i-1]['open'] > d.iloc[i-2]['open'],
        "TriStar Bullish": lambda d, i: d.iloc[i-2]['is_doji'] and d.iloc[i-1]['is_doji'] and d.iloc[i]['is_doji'] and d.iloc[i-2]['downtrend'] and d.iloc[i-1]['body_hi'] < d.iloc[i-2]['body_lo'] and d.iloc[i]['body_lo'] > d.iloc[i-1]['body_hi'],
        "Tweezer Bottom Bullish": lambda d, i: d.iloc[i-1]['downtrend'] and d.iloc[i-1]['is_black_body'] and d.iloc[i-1]['is_long_body'] and d.iloc[i]['is_white_body'] and np.abs(d.iloc[i]['low'] - d.iloc[i-1]['low']) <= d.iloc[i]['body_avg'] * 0.05,
        "Upside Tasuki Gap Bullish": lambda d, i: d.iloc[i-2]['is_long_body'] and d.iloc[i-1]['is_small_body'] and d.iloc[i]['uptrend'] and d.iloc[i-2]['is_white_body'] and d.iloc[i-1]['body_lo'] > d.iloc[i-2]['body_hi'] and d.iloc[i-1]['is_white_body'] and d.iloc[i]['is_black_body'] and d.iloc[i]['body_lo'] >= d.iloc[i-2]['body_hi'] and d.iloc[i]['body_lo'] <= d.iloc[i-1]['body_lo'],
        
        # Bearish Patterns
        "Abandoned Baby Bearish": lambda d, i: d.iloc[i-2]['uptrend'] and d.iloc[i-2]['is_white_body'] and d.iloc[i-1]['is_doji_body'] and d.iloc[i]['is_black_body'] and d.iloc[i-2]['high'] < d.iloc[i-1]['low'] and d.iloc[i-1]['low'] > d.iloc[i]['high'],
        "Dark Cloud Cover Bearish": lambda d, i: d.iloc[i-1]['uptrend'] and d.iloc[i-1]['is_white_body'] and d.iloc[i-1]['is_long_body'] and d.iloc[i]['is_black_body'] and d.iloc[i]['open'] >= d.iloc[i-1]['high'] and d.iloc[i]['close'] < d.iloc[i-1]['body_middle'] and d.iloc[i]['close'] > d.iloc[i-1]['open'],
        "Downside Tasuki Gap Bearish": lambda d, i: d.iloc[i-2]['is_long_body'] and d.iloc[i-1]['is_small_body'] and d.iloc[i]['downtrend'] and d.iloc[i-2]['is_black_body'] and d.iloc[i-1]['body_hi'] < d.iloc[i-2]['body_lo'] and d.iloc[i-1]['is_black_body'] and d.iloc[i]['is_white_body'] and d.iloc[i]['body_hi'] <= d.iloc[i-2]['body_lo'] and d.iloc[i]['body_hi'] >= d.iloc[i-1]['body_hi'],
        "Engulfing Bearish": lambda d, i: d.iloc[i-1]['uptrend'] and d.iloc[i]['is_black_body'] and d.iloc[i]['is_long_body'] and d.iloc[i-1]['is_white_body'] and d.iloc[i-1]['is_small_body'] and d.iloc[i]['close'] <= d.iloc[i-1]['open'] and d.iloc[i]['open'] >= d.iloc[i-1]['close'],
        "Evening Doji Star Bearish": lambda d, i: d.iloc[i-2]['is_long_body'] and d.iloc[i-1]['is_doji_body'] and d.iloc[i]['is_long_body'] and d.iloc[i-2]['uptrend'] and d.iloc[i-2]['is_white_body'] and d.iloc[i]['is_black_body'] and d.iloc[i-1]['body_lo'] > d.iloc[i-2]['body_hi'] and d.iloc[i]['body_lo'] <= d.iloc[i-2]['body_middle'] and d.iloc[i]['body_lo'] > d.iloc[i-2]['body_lo'] and d.iloc[i-1]['body_lo'] > d.iloc[i]['body_hi'],
        "Evening Star Bearish": lambda d, i: d.iloc[i-2]['is_long_body'] and d.iloc[i-1]['is_small_body'] and d.iloc[i]['is_long_body'] and d.iloc[i-2]['uptrend'] and d.iloc[i-2]['is_white_body'] and d.iloc[i]['is_black_body'] and d.iloc[i-1]['body_lo'] > d.iloc[i-2]['body_hi'] and d.iloc[i]['body_lo'] <= d.iloc[i-2]['body_middle'] and d.iloc[i]['body_lo'] > d.iloc[i-2]['body_lo'] and d.iloc[i-1]['body_lo'] > d.iloc[i]['body_hi'],
        "Falling Three Methods Bearish": lambda d, i: d.iloc[i-4]['downtrend'] and d.iloc[i-4]['is_long_body'] and d.iloc[i-4]['is_black_body'] and d.iloc[i-3]['is_small_body'] and d.iloc[i-3]['is_white_body'] and d.iloc[i-3]['open'] > d.iloc[i-4]['low'] and d.iloc[i-3]['close'] < d.iloc[i-4]['high'] and d.iloc[i-2]['is_small_body'] and d.iloc[i-2]['is_white_body'] and d.iloc[i-2]['open'] > d.iloc[i-4]['low'] and d.iloc[i-2]['close'] < d.iloc[i-4]['high'] and d.iloc[i-1]['is_small_body'] and d.iloc[i-1]['is_white_body'] and d.iloc[i-1]['open'] > d.iloc[i-4]['low'] and d.iloc[i-1]['close'] < d.iloc[i-4]['high'] and d.iloc[i]['is_long_body'] and d.iloc[i]['is_black_body'] and d.iloc[i]['close'] < d.iloc[i-4]['close'],
        "Falling Window Bearish": lambda d, i: d.iloc[i-1]['downtrend'] and (d.iloc[i-1]['range']!=0 and d.iloc[i]['range']!=0) and d.iloc[i]['high'] < d.iloc[i-1]['low'],
        "Gravestone Doji Bearish": lambda d, i: d.iloc[i]['is_doji_body'] and d.iloc[i]['dn_shadow'] <= d.iloc[i]['body'],
        "Hanging Man Bearish": lambda d, i: d.iloc[i]['uptrend'] and d.iloc[i]['is_small_body'] and d.iloc[i]['body'] > 0 and d.iloc[i]['dn_shadow'] >= C_Factor * d.iloc[i]['body'] and d.iloc[i]['up_shadow'] <= (C_ShadowPercent / 100 * d.iloc[i]['body']),
        "Harami Bearish": lambda d, i: d.iloc[i-1]['uptrend'] and d.iloc[i-1]['is_long_body'] and d.iloc[i-1]['is_white_body'] and d.iloc[i]['is_black_body'] and d.iloc[i]['is_small_body'] and d.iloc[i]['high'] <= d.iloc[i-1]['body_hi'] and d.iloc[i]['low'] >= d.iloc[i-1]['body_lo'],
        "Harami Cross Bearish": lambda d, i: d.iloc[i-1]['uptrend'] and d.iloc[i-1]['is_long_body'] and d.iloc[i-1]['is_white_body'] and d.iloc[i]['is_doji_body'] and d.iloc[i]['high'] <= d.iloc[i-1]['body_hi'] and d.iloc[i]['low'] >= d.iloc[i-1]['body_lo'],
        "Kicking Bearish": lambda d, i: d.iloc[i-1]['is_white_body'] and d.iloc[i-1]['is_long_body'] and d.iloc[i-1]['up_shadow'] <= C_MarubozuShadowPercent/100*d.iloc[i-1]['body'] and d.iloc[i-1]['dn_shadow'] <= C_MarubozuShadowPercent/100*d.iloc[i-1]['body'] and d.iloc[i]['is_black_body'] and d.iloc[i]['is_long_body'] and d.iloc[i]['up_shadow'] <= C_MarubozuShadowPercent/100*d.iloc[i]['body'] and d.iloc[i]['dn_shadow'] <= C_MarubozuShadowPercent/100*d.iloc[i]['body'] and d.iloc[i-1]['low'] > d.iloc[i]['high'],
        "Long Upper Shadow Bearish": lambda d, i: d.iloc[i]['up_shadow'] > d.iloc[i]['range']/100*75.0,
        "Marubozu Black Bearish": lambda d, i: d.iloc[i]['is_black_body'] and d.iloc[i]['is_long_body'] and d.iloc[i]['up_shadow'] <= C_MarubozuShadowPercent/100*d.iloc[i]['body'] and d.iloc[i]['dn_shadow'] <= C_MarubozuShadowPercent/100*d.iloc[i]['body'],
        "On Neck Bearish": lambda d, i: d.iloc[i-1]['downtrend'] and d.iloc[i-1]['is_black_body'] and d.iloc[i-1]['is_long_body'] and d.iloc[i]['is_white_body'] and d.iloc[i]['open'] < d.iloc[i-1]['close'] and d.iloc[i]['is_small_body'] and d.iloc[i]['range']!=0 and np.abs(d.iloc[i]['close'] - d.iloc[i-1]['low']) <= d.iloc[i]['body_avg'] * 0.05,
        "Shooting Star Bearish": lambda d, i: d.iloc[i]['uptrend'] and d.iloc[i]['is_small_body'] and d.iloc[i]['body'] > 0 and d.iloc[i]['up_shadow'] >= C_Factor * d.iloc[i]['body'] and d.iloc[i]['dn_shadow'] <= (C_ShadowPercent / 100 * d.iloc[i]['body']),
        "Three Black Crows Bearish": lambda d, i: d.iloc[i]['is_long_body'] and d.iloc[i-1]['is_long_body'] and d.iloc[i-2]['is_long_body'] and d.iloc[i]['is_black_body'] and d.iloc[i-1]['is_black_body'] and d.iloc[i-2]['is_black_body'] and d.iloc[i]['close'] < d.iloc[i-1]['close'] and d.iloc[i-1]['close'] < d.iloc[i-2]['close'] and d.iloc[i]['open'] > d.iloc[i-1]['close'] and d.iloc[i]['open'] < d.iloc[i-1]['open'] and d.iloc[i-1]['open'] > d.iloc[i-2]['close'] and d.iloc[i-1]['open'] < d.iloc[i-2]['open'],
        "Tweezer Top Bearish": lambda d, i: d.iloc[i-1]['uptrend'] and d.iloc[i-1]['is_white_body'] and d.iloc[i-1]['is_long_body'] and d.iloc[i]['is_black_body'] and np.abs(d.iloc[i]['high'] - d.iloc[i-1]['high']) <= d.iloc[i]['body_avg'] * 0.05,
        "TriStar Bearish": lambda d, i: d.iloc[i-2]['is_doji'] and d.iloc[i-1]['is_doji'] and d.iloc[i]['is_doji'] and d.iloc[i-2]['uptrend'] and d.iloc[i-1]['body_lo'] > d.iloc[i-2]['body_hi'] and d.iloc[i]['body_hi'] < d.iloc[i-1]['body_lo'],

        # Neutral Patterns
        "Doji Neutral": lambda d, i: d.iloc[i]['is_doji_body'],
        "Spinning Top Black Neutral": lambda d, i: d.iloc[i]['is_black_body'] and not d.iloc[i]['is_doji_body'] and d.iloc[i]['dn_shadow'] >= d.iloc[i]['range'] / 100 * C_SpinningTopPercent and d.iloc[i]['up_shadow'] >= d.iloc[i]['range'] / 100 * C_SpinningTopPercent,
        "Spinning Top White Neutral": lambda d, i: d.iloc[i]['is_white_body'] and not d.iloc[i]['is_doji_body'] and d.iloc[i]['dn_shadow'] >= d.iloc[i]['range'] / 100 * C_SpinningTopPercent and d.iloc[i]['up_shadow'] >= d.iloc[i]['range'] / 100 * C_SpinningTopPercent,
    }

def extract_candlestick_signals(df):
    """Menganalisis DataFrame dan mengembalikan semua pola candlestick yang terdeteksi."""
    signals = []
    df_processed = calculate_properties(df)
    pattern_detectors = _get_pattern_detectors()
    
    for i in range(len(df_processed)):
        for pattern_name, condition in pattern_detectors.items():
            min_bars = 5 if 'three' in pattern_name.lower() else 3 if 'tri' in pattern_name.lower() or 'star' in pattern_name.lower() or 'morning' in pattern_name.lower() or 'evening' in pattern_name.lower() or 'abandoned' in pattern_name.lower() or 'tasuki' in pattern_name.lower() else 2 if 'window' in pattern_name.lower() or 'engulfing' in pattern_name.lower() or 'harami' in pattern_name.lower() or 'tweezer' in pattern_name.lower() or 'kicking' in pattern_name.lower() or 'piercing' in pattern_name.lower() or 'on neck' in pattern_name.lower() else 1
            if i >= min_bars - 1:
                try:
                    if condition(df_processed, i):
                        signals.append((df_processed.index[i], pattern_name, _get_signal_type(pattern_name)))
                except (KeyError, IndexError):
                    continue

    return signals

def main():
    try:
        config = load_config('config.yaml')
        general_config = config['general']
        assets_config = config['assets']

        # Logika untuk menentukan simbol
        if general_config['symbol'] == 'auto':
            today = datetime.now().weekday()
            if today >= 0 and today <= 4:
                symbol = assets_config['weekday']
            else:
                symbol = assets_config['weekend']
        else:
            symbol = general_config['symbol']

        timeframe_str = general_config['timeframe']

        initialize_mt5()
        df = get_candles(symbol, timeframe_str, bars=500)
        shutdown_mt5()

        signals = extract_candlestick_signals(df)

        print(f"Hasil Analisis Pola Candlestick untuk {symbol} ({timeframe_str})")
        print("----------------------------------------------------------")
        print(f"{'Time':<20} {'Pattern':<35} {'Type':<10}")
        print("----------------------------------------------------------")

        if signals:
           for time, pattern, signal_type in signals[-10:]:
                print(f"{time:%Y-%m-%d %H:%M:%S} {pattern:<35} {signal_type:<10}")
        else:
            print("Tidak ada pola candlestick yang terdeteksi.")

    except RuntimeError as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()