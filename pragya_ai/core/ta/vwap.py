# /pragya_ai/core/ta/vwap.py

import pandas as pd
import numpy as np

def calculate_vwap(df, anchor="Session", calc_mode="Standard Deviation", bands=None):
    """
    Menghitung VWAP dan band-nya.
    """
    if 'volume' not in df.columns:
        raise ValueError("DataFrame harus memiliki kolom 'volume'.")
    if 'high' not in df.columns or 'low' not in df.columns or 'close' not in df.columns:
        raise ValueError("DataFrame harus memiliki kolom 'high', 'low', dan 'close'.")

    df_calc = df.copy()
    
    # Pastikan index adalah datetime
    if not isinstance(df_calc.index, pd.DatetimeIndex):
        try:
            df_calc.index = pd.to_datetime(df_calc.index)
        except Exception:
            raise ValueError("Index DataFrame harus dalam format datetime.")

    df_calc['typical_price'] = (df_calc['high'] + df_calc['low'] + df_calc['close']) / 3
    df_calc['tpv'] = df_calc['typical_price'] * df_calc['volume']

    df_calc['cum_tpv'] = df_calc['tpv'].cumsum()
    df_calc['cum_volume'] = df_calc['volume'].cumsum()
    df_calc['vwap'] = df_calc['cum_tpv'] / df_calc['cum_volume']

    # Logika untuk band VWAP
    if bands and calc_mode == "Standard Deviation":
        df_calc['vwap_deviation'] = (df_calc['typical_price'] - df_calc['vwap']) ** 2
        df_calc['vwap_std'] = np.sqrt((df_calc['vwap_deviation'] * df_calc['volume']).cumsum() / df_calc['cum_volume'])

        for mult in bands:
            df_calc[f'upper_band_{mult}'] = df_calc['vwap'] + (df_calc['vwap_std'] * mult)
            df_calc[f'lower_band_{mult}'] = df_calc['vwap'] - (df_calc['vwap_std'] * mult)

    return df_calc

def get_vwap_report(df, anchor="Session", calc_mode="Standard Deviation", bands=[1.0, 2.0, 3.0]):
    """
    Menghasilkan laporan berdasarkan VWAP.
    """
    try:
        df_vwap = calculate_vwap(df, anchor, calc_mode, bands)
        
        last_vwap = df_vwap['vwap'].iloc[-1]
        last_close = df_vwap['close'].iloc[-1]

        report = {
            'vwap_value': last_vwap,
            'current_price_relation': 'Above VWAP' if last_close > last_vwap else 'Below VWAP'
        }
        
        return report

    except (ValueError, KeyError) as e:
        return None

# --- Fungsi utama untuk pengujian mandiri ---
if __name__ == '__main__':
    # Contoh data dummy
    data = {
        'open': [100, 102, 105, 103, 104],
        'high': [103, 106, 107, 105, 106],
        'low': [99, 101, 102, 101, 102],
        'close': [102, 105, 103, 104, 105],
        'volume': [1000, 1500, 1200, 1300, 1800]
    }
    dates = pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03', '2023-01-04', '2023-01-05'])
    test_df = pd.DataFrame(data, index=dates)

    report = get_vwap_report(test_df)
    if report:
        print("VWAP Report:")
        print(report)
    else:
        print("Gagal membuat laporan VWAP.")