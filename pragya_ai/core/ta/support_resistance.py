# pragya_ai/core/ta/support_resistance.py

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

# --- Logika Perhitungan Indikator Support & Resistance ---
def _pivothigh(high_series, left, right):
    """Replikasi fungsi pivothigh() di Pine Script."""
    is_pivot = high_series.rolling(window=left + right + 1, center=True).apply(
        lambda x: x.iloc[left] == x.max(), raw=False
    )
    pivots = high_series[is_pivot == 1].dropna()
    return pivots

def _pivotlow(low_series, left, right):
    """Replikasi fungsi pivotlow() di Pine Script."""
    is_pivot = low_series.rolling(window=left + right + 1, center=True).apply(
        lambda x: x.iloc[left] == x.min(), raw=False
    )
    pivots = low_series[is_pivot == 1].dropna()
    return pivots

def _calculate_volume_oscillator(volume_series, short=5, long=10):
    """Menghitung Volume Oscillator."""
    short_ema = volume_series.ewm(span=short, adjust=False).mean()
    long_ema = volume_series.ewm(span=long, adjust=False).mean()
    return 100 * (short_ema - long_ema) / long_ema.replace(0, 1e-9)

def calculate_support_resistance(df, left_bars=15, right_bars=15, vol_period_short=5, vol_period_long=10, volume_thresh=20):
    """Menghitung level S/R dan mendeteksi breakout."""
    df_calc = df.copy()
    
    # Deteksi pivot high/low
    high_pivots = _pivothigh(df_calc['high'], left_bars, right_bars)
    low_pivots = _pivotlow(df_calc['low'], left_bars, right_bars)

    # Deteksi S/R dari pivot terakhir
    resistance_level = high_pivots.iloc[-1] if not high_pivots.empty else None
    support_level = low_pivots.iloc[-1] if not low_pivots.empty else None

    # Hitung Volume Oscillator
    df_calc['volume_osc'] = _calculate_volume_oscillator(df_calc['real_volume'], vol_period_short, vol_period_long)

    # Deteksi breakout
    is_sr_broken = False
    is_wick_signal = False
    signal_type = None

    if support_level is not None and df_calc['close'].iloc[-1] < support_level:
        if df_calc['volume_osc'].iloc[-1] > volume_thresh:
            is_sr_broken = True
            signal_type = "Support Broken (Bearish)"
        elif df_calc['open'].iloc[-1] - df_calc['close'].iloc[-1] > df_calc['high'].iloc[-1] - df_calc['open'].iloc[-1]:
            is_wick_signal = True
            signal_type = "Bear Wick (Bearish)"
    
    if resistance_level is not None and df_calc['close'].iloc[-1] > resistance_level:
        if df_calc['volume_osc'].iloc[-1] > volume_thresh:
            is_sr_broken = True
            signal_type = "Resistance Broken (Bullish)"
        elif df_calc['open'].iloc[-1] - df_calc['low'].iloc[-1] > df_calc['close'].iloc[-1] - df_calc['open'].iloc[-1]:
            is_wick_signal = True
            signal_type = "Bull Wick (Bullish)"
            
    return resistance_level, support_level, signal_type

# --- Ekstraksi Laporan S/R yang Efisien ---
def get_sr_report(df, left_bars=15, right_bars=15, vol_period_short=5, vol_period_long=10, volume_thresh=20):
    """Mengembalikan laporan S/R dari bar terakhir."""
    resistance, support, signal_type = calculate_support_resistance(df, left_bars, right_bars, vol_period_short, vol_period_long, volume_thresh)
    
    report = {
        "time": df.index[-1],
        "support_level": support,
        "resistance_level": resistance,
        "report_type": "sr_data",
        "signal": signal_type
    }
    
    return report

# --- Fungsi Utama ---
def main():
    try:
        config = load_config('config.yaml')
        general_config = config['general']
        assets_config = config['assets']
        sr_config = config.get('sr_indicator', {})

        if general_config['symbol'] == 'auto':
            today = datetime.now().weekday()
            if today >= 0 and today <= 4:
                symbol = assets_config['weekday']
            else:
                symbol = assets_config['weekend']
        else:
            symbol = general_config['symbol']
        
        timeframe = general_config['timeframe']
        
        left_bars = sr_config.get('left_bars', 15)
        right_bars = sr_config.get('right_bars', 15)
        volume_thresh = sr_config.get('volume_threshold', 20)
        vol_period_short = 5
        vol_period_long = 10

        initialize_mt5()
        bars_needed = left_bars + right_bars + max(vol_period_short, vol_period_long) + 2
        df = get_candles(symbol, timeframe, bars=bars_needed)
        shutdown_mt5()

        sr_report = get_sr_report(df, left_bars, right_bars, vol_period_short, vol_period_long, volume_thresh)
        
        print(f"Laporan Indikator Support & Resistance untuk {symbol} ({timeframe})")
        print("--------------------------------------------------")
        
        if sr_report:
            print(f"Time: {sr_report['time']:%Y-%m-%d %H:%M:%S}")
            print(f"🔻 Support Level: {sr_report['support_level']:.4f}" if sr_report['support_level'] else "🔻 Support Level: Tidak terdeteksi")
            print(f"🔺 Resistance Level: {sr_report['resistance_level']:.4f}" if sr_report['resistance_level'] else "🔺 Resistance Level: Tidak terdeteksi")
            print(f"Signal: {sr_report['signal']}")
        else:
            print("Tidak ada data S/R yang valid pada bar terakhir.")

    except RuntimeError as e:
        print(f"Error: {e}")
    except FileNotFoundError as e:
        print(f"Error: {e}")
    except ValueError as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()