# /pragya_ai/core/mt5_utils.py
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime
import os
from dotenv import load_dotenv
import yaml

# Load environment variables from .env file
load_dotenv()

def initialize_mt5():
    """
    Menginisialisasi koneksi ke MetaTrader 5.
    """
    print("Mencoba inisialisasi MT5...")
    if not mt5.initialize():
        print(f"initialize() failed, error code: {mt5.last_error()}")
        raise RuntimeError("Gagal menginisialisasi MT5.")
    
    # Ambil kredensial dari environment variables dan bersihkan spasi
    mt5_login_str = os.getenv("MT5_LOGIN")
    mt5_password = os.getenv("MT5_PASSWORD")

    if mt5_login_str is None or mt5_password is None:
        raise ValueError("Kredensial MT5 tidak ditemukan di file .env")

    mt5_login = int(mt5_login_str.strip()) # Pastikan spasi dihilangkan
    mt5_password = mt5_password.strip() # Pastikan spasi dihilangkan

    print(f"Menggunakan login: '{mt5_login}'")
    print(f"Menggunakan password: '{mt5_password[:2]}...'") # Sembunyikan sebagian password untuk keamanan
    
    # Masuk ke akun trading
    authorized = mt5.login(mt5_login, password=mt5_password)
    if not authorized:
        print(f"login() failed, error code: {mt5.last_error()}")
        raise RuntimeError("Gagal login ke akun MT5.")
    
    print("Koneksi ke MT5 berhasil.")
    
def shutdown_mt5():
    """
    Memutuskan koneksi dari MetaTrader 5.
    """
    mt5.shutdown()

def get_candles(symbol, timeframe, bars=1000):
    """
    Mengambil data candlestick dari MT5.
    """
    try:
        if not mt5.symbol_select(symbol, True):
            print(f"Gagal memilih symbol {symbol}. Periksa nama symbol.")
            return None
        
        timeframe_map = {
            'M1': mt5.TIMEFRAME_M1,
            'M5': mt5.TIMEFRAME_M5,
            'M15': mt5.TIMEFRAME_M15,
            'M30': mt5.TIMEFRAME_M30,
            'H1': mt5.TIMEFRAME_H1,
            'H4': mt5.TIMEFRAME_H4,
            'D1': mt5.TIMEFRAME_D1
        }
        
        if timeframe.upper() not in timeframe_map:
            raise ValueError(f"Timeframe '{timeframe}' tidak valid. Pilih dari: {list(timeframe_map.keys())}")
            
        timeframe_mt5 = timeframe_map[timeframe.upper()]

        rates = mt5.copy_rates_from_pos(symbol, timeframe_mt5, 0, bars)
        if rates is None or not rates.size:
            print(f"Gagal mengambil data untuk {symbol} ({timeframe}). Coba lagi.")
            return None

        rates_frame = pd.DataFrame(rates)
        rates_frame['time'] = pd.to_datetime(rates_frame['time'], unit='s')
        rates_frame.set_index('time', inplace=True)
        return rates_frame
        
    except Exception as e:
        print(f"Error saat mengambil data MT5: {e}")
        return None

def load_config(file_path):
    """
    Memuat file konfigurasi YAML.
    """
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)