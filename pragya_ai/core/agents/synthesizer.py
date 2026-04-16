# /pragya_ai/core/agents/synthesizer.py

import pandas as pd
from datetime import datetime

# Mengimpor semua fungsi laporan secara spesifik dari setiap modul
from core.ta.adx import get_adx_report
from core.ta.all_candlestick_patterns import extract_candlestick_signals
from core.ta.atr import get_atr_report
from core.ta.bb import get_bb_report
from core.ta.cci import get_cci_report
from core.ta.fibonacci import get_fibonacci_report
from core.ta.ichimoku import get_ichimoku_report
from core.ta.keltner import get_keltner_report
from core.ta.ma_ribbon import get_ma_ribbon_report
from core.ta.macd import get_macd_report
from core.ta.mfi import get_mfi_report
from core.ta.obv import get_obv_report
from core.ta.parabolic_sar import get_sar_report
from core.ta.pivot_points import get_pivot_report
from core.ta.roc import get_roc_report
from core.ta.rsi import get_rsi_report
from core.ta.stochastic_oscillator import get_stochastic_report
from core.ta.volatility import get_volatility_report
from core.ta.vwap import get_vwap_report
from core.ta.williams import get_williams_report


def get_all_indicator_reports(df, config):
    """
    Mengumpulkan laporan mentah dari semua modul indikator.
    """
    reports = {}
    
    # Ambil konfigurasi untuk setiap indikator
    adx_config = config.get('adx_indicator', {})
    atr_config = config.get('atr_indicator', {})
    bb_config = config.get('bb_indicator', {})
    cci_config = config.get('cci_indicator', {})
    fib_config = config.get('fib_indicator', {})
    ichimoku_config = config.get('ichimoku_indicator', {})
    keltner_config = config.get('keltner_indicator', {})
    ma_ribbon_config = config.get('ma_ribbon_indicator', {})
    macd_config = config.get('macd_indicator', {})
    mfi_config = config.get('mfi_indicator', {})
    obv_config = config.get('obv_indicator', {})
    sar_config = config.get('sar_indicator', {})
    pivot_config = config.get('pivot_indicator', {})
    roc_config = config.get('roc_indicator', {})
    rsi_config = config.get('rsi_indicator', {})
    stoch_config = config.get('stoch_indicator', {})
    vol_config = config.get('volatility_indicator', {})
    vwap_config = config.get('vwap_indicator', {})
    williams_config = config.get('williams_indicator', {})

    # Teruskan konfigurasi ke setiap modul
    reports['adx'] = get_adx_report(df, adx_config.get('adxlen', 14), adx_config.get('dilen', 14))
    reports['atr'] = get_atr_report(df, atr_config.get('length', 14), atr_config.get('smoothing', 'RMA'))
    reports['bb'] = get_bb_report(df, bb_config.get('length', 20), bb_config.get('ma_type', 'SMA'), bb_config.get('stddev_mult', 2.0))
    reports['cci'] = get_cci_report(df, cci_config.get('length', 20), cci_config.get('smoothing_ma_type', 'None'), cci_config.get('smoothing_ma_length', 14), cci_config.get('bb_stddev', 2.0))
    reports['fibonacci'] = get_fibonacci_report(df, fib_config.get('mode', 'retracement'), fib_config.get('depth', 10))
    reports['ichimoku'] = get_ichimoku_report(df, ichimoku_config.get('conversion_periods', 9), ichimoku_config.get('base_periods', 26), ichimoku_config.get('lagging_span2_periods', 52), ichimoku_config.get('displacement', 26))
    reports['keltner'] = get_keltner_report(df, keltner_config.get('length', 20), keltner_config.get('multiplier', 2.0), keltner_config.get('use_exponential_ma', True), keltner_config.get('bands_style', 'Average True Range'), keltner_config.get('atr_length', 10))
    reports['ma_ribbon'] = get_ma_ribbon_report(df, ma_ribbon_config.get('ma_settings', []))
    reports['macd'] = get_macd_report(df, macd_config.get('fast_length', 12), macd_config.get('slow_length', 26), macd_config.get('signal_smoothing', 9), macd_config.get('macd_ma_type', 'EMA'), macd_config.get('signal_ma_type', 'EMA'))
    reports['mfi'] = get_mfi_report(df, mfi_config.get('length', 14))
    reports['obv'] = get_obv_report(df, obv_config.get('smoothing_ma_type', 'None'), obv_config.get('smoothing_ma_length', 14), obv_config.get('bb_stddev', 2.0))
    reports['parabolic_sar'] = get_sar_report(df, sar_config.get('start', 0.02), sar_config.get('increment', 0.02), sar_config.get('maximum', 0.2))
    reports['pivot_points'] = get_pivot_report(df, pivot_config.get('pivot_type', 'Traditional'), pivot_config.get('pivot_timeframe', 'Daily'))
    reports['roc'] = get_roc_report(df, roc_config.get('length', 9))
    reports['rsi'] = get_rsi_report(df, rsi_config.get('rsi_length', 14), rsi_config.get('smoothing_ma_type', 'None'), rsi_config.get('smoothing_ma_length', 14), rsi_config.get('bb_stddev', 2.0), rsi_config.get('calculate_divergence', False))
    reports['stoch'] = get_stochastic_report(df, stoch_config.get('period_k', 14), stoch_config.get('smooth_k', 1), stoch_config.get('period_d', 3))
    reports['volatility'] = get_volatility_report(df, vol_config.get('hv_length', 10), vol_config.get('vstop_length', 20), vol_config.get('vstop_factor', 2.0), vol_config.get('rvi_length', 10), vol_config.get('rvi_ema_length', 14), vol_config.get('rvi_offset', 0))
    reports['vwap'] = get_vwap_report(df, vwap_config.get('anchor_period', 'Session'), vwap_config.get('calc_mode', 'Standard Deviation'), vwap_config.get('bands_multipliers', [1.0, 2.0, 3.0]))
    reports['williams'] = get_williams_report(df, williams_config.get('percent_r_length', 14), williams_config.get('alligator_jaw_length', 13), williams_config.get('alligator_teeth_length', 8), williams_config.get('alligator_lips_length', 5), williams_config.get('fractal_periods', 2))
    reports['candle_pattern'] = extract_candlestick_signals(df)

    reports['data'] = df

    return reports

def synthesize_reports(df, config):
    all_reports = get_all_indicator_reports(df, config)
    synthesized_report = {k: v for k, v in all_reports.items() if v is not None}
    return synthesized_report