# core/fa/economic_calendar.py

import requests # <-- Pastikan Anda sudah menginstal pustaka ini
import pandas as pd
from datetime import datetime, timedelta
import yaml

# Mengimpor utilitas dasar MT5 dan Config
from core import mt5_utils

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


# --- Pakar Analisis Fundamental: Kalender Ekonomi ---
def get_economic_calendar_report(config):
    """
    Mengambil dan memproses laporan dari kalender ekonomi secara riil (membutuhkan API).
    Logika ini disesuaikan untuk event-event terkait USD dan BTC.
    """
    
    # --- BLUEPRINT UNTUK PENGAMBILAN DATA RIIL ---
    # Anda perlu mengganti logika di bawah dengan API call yang sebenarnya.
    # Contoh penggunaan pustaka 'requests':
    # try:
    #     api_key = "API_KEY_ANDA"
    #     url = f"https://api.sumberdata.com/calendar?api_key={api_key}"
    #     response = requests.get(url, timeout=10)
    #     response.raise_for_status() # Akan memunculkan error jika respons tidak 200 OK
    #     economic_events_source = response.json()
    # except Exception as e:
    #     print(f"Error saat memanggil API kalender ekonomi: {e}")
    #     return None

    # Simulasikan data dari API untuk demonstrasi
    economic_events_source = [
        {'time': datetime.now() + timedelta(minutes=5), 'currency': 'USD', 'event': 'Suku Bunga', 'impact': 'High'},
        {'time': datetime.now() + timedelta(minutes=15), 'currency': 'USD', 'event': 'Unemployment Rate', 'impact': 'High'},
        {'time': datetime.now() + timedelta(minutes=30), 'currency': 'EUR', 'event': 'GDP', 'impact': 'Medium'},
        {'time': datetime.now() + timedelta(minutes=45), 'currency': 'BTC', 'event': 'Halving Event', 'impact': 'High'},
    ]
    
    current_time = datetime.now()
    
    # Filter event hanya yang berdampak tinggi dan terkait USD atau BTC
    relevant_events = [
        event for event in economic_events_source
        if event['impact'] == 'High' and (event['currency'] == 'USD' or event['currency'] == 'BTC')
    ]
    
    # Filter event dalam jendela waktu yang akan datang (misal, 30 menit ke depan)
    event_window = timedelta(minutes=30)
    upcoming_events = [
        event for event in relevant_events
        if current_time < event['time'] <= current_time + event_window
    ]
    
    if not upcoming_events:
        return None
        
    return {
        "time": current_time,
        "upcoming_events": upcoming_events,
        "report_type": "fa_data"
    }

# --- Fungsi Utama (untuk pengujian mandiri) ---
if __name__ == "__main__":
    try:
        config = load_config('../../config.yaml')
        
        report = get_economic_calendar_report(config)
        
        print("Laporan Kalender Ekonomi:")
        print("--------------------------------------------------")
        
        if report:
            print(f"Time: {report['time']:%Y-%m-%d %H:%M:%S}")
            print("Upcoming Events:")
            for event in report['upcoming_events']:
                print(f" - {event['event']} ({event['currency']}) at {event['time']:%H:%M}, Impact: {event['impact']}")
        else:
            print("Tidak ada event berdampak tinggi dalam jendela waktu yang ditentukan.")

    except FileNotFoundError as e:
        print(f"Error: {e}")
    except ValueError as e:
        print(f"Error: {e}")