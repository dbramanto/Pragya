# /pragya_ai/core/mt5_utils.py

import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime
import os
import yaml
import re
from typing import Optional

def load_env_manually():
    env_vars = {}
    try:
        with open('.env', 'r') as file:
            for line in file:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                match = re.match(r'^([^=]+)=(.*)$', line)
                if match:
                    key = match.group(1).strip()
                    value = match.group(2).strip().strip("'\"")
                    env_vars[key] = value
    except FileNotFoundError:
        raise FileNotFoundError("File .env tidak ditemukan. Pastikan sudah ada di direktori utama.")
    return env_vars

def initialize_mt5(server_name: Optional[str] = None):
    print("Mencoba inisialisasi MT5...")

    try:
        env_vars = load_env_manually()
        mt5_login_str = env_vars.get("MT5_LOGIN")
        mt5_password = env_vars.get("MT5_PASSWORD")

        if mt5_login_str is None or mt5_password is None:
            raise ValueError("Kredensial MT5 tidak ditemukan di file .env")

        mt5_login = int(mt5_login_str)
        mt5_password = mt5_password

    except ValueError as e:
        raise ValueError(f"Kesalahan format pada file .env: {e}")
    except Exception as e:
        raise ValueError(f"Error saat membaca file .env: {e}")

    if not mt5.initialize():
        print(f"initialize() failed, error code: {mt5.last_error()}")
        raise RuntimeError("Gagal menginisialisasi MT5.")

    print(f"Menggunakan login: '{mt5_login}'")
    print(f"Menggunakan password: '{mt5_password[:2]}...'")
    if server_name:
        print(f"Menggunakan server: '{server_name}'")

    if server_name:
        authorized = mt5.login(mt5_login, password=mt5_password, server=server_name)
    else:
        authorized = mt5.login(mt5_login, password=mt5_password)

    if not authorized:
        print(f"login() failed, error code: {mt5.last_error()}")
        raise RuntimeError("Gagal login ke akun MT5.")

    print("Koneksi ke MT5 berhasil.")

def shutdown_mt5():
    mt5.shutdown()

def get_candles(symbol, timeframe, bars=1000):
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
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)