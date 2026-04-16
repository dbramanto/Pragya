# core/config.py

import MetaTrader5 as mt5
import datetime
import pytz
import os
import yaml
from dotenv import load_dotenv

# ====================
# 🔌 Load Konfigurasi
# ====================

# Load .env
load_dotenv(dotenv_path="telegram.env")

# Load config.yaml
with open("config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

# Zona waktu
TIMEZONE = pytz.timezone(config["general"].get("timezone", "UTC"))

# ==============================
# 🕒 Fungsi Umum & Waktu
# ==============================

def is_weekday():
    return datetime.datetime.now(TIMEZONE).weekday() < 5

def get_asset_for_today():
    aset = config["assets"]
    return aset["weekday"] if is_weekday() else aset["weekend"]

def get_timezone():
    return TIMEZONE

# ==============================
# ⚙️ General Settings
# ==============================

def get_general():
    return config.get("general", {})

def get_mode():
    return config["general"].get("mode", "auto")

def should_save_logs():
    return config["general"].get("save_logs", True)

def get_timeframe():
    return config["general"].get("timeframe", "M15")

# ==============================
# 💬 Telegram Settings
# ==============================

def is_telegram_enabled():
    return config.get("telegram", {}).get("enabled", False)

# ==============================
# 🧾 Account Info
# ==============================

def get_account_config():
    return config.get("account", {})

def get_leverage():
    setting = config["account"].get("leverage", "auto")
    if setting != "auto":
        return setting

    if not mt5.initialize():
        raise ConnectionError("MT5 gagal inisialisasi untuk leverage.")
    info = mt5.account_info()
    if info:
        return info.leverage
    raise RuntimeError("Info akun tidak ditemukan.")

def get_contract_size(symbol=None):
    if symbol is None:
        symbol = get_asset_for_today()

    setting = config["account"].get("contract_size", "auto")
    if setting != "auto":
        return setting

    if not mt5.initialize():
        raise ConnectionError("MT5 gagal inisialisasi untuk contract size.")
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info:
        return symbol_info.trade_contract_size
    raise RuntimeError(f"Info simbol tidak ditemukan: {symbol}")

def get_account_info():
    if not mt5.initialize():
        raise ConnectionError("MT5 gagal inisialisasi.")
    info = mt5.account_info()
    if not info:
        raise RuntimeError("Info akun tidak ditemukan.")
    return {
        "login": info.login,
        "leverage": info.leverage,
        "balance": info.balance,
        "equity": info.equity,
        "margin": info.margin,
        "free_margin": info.margin_free,
        "margin_level": info.margin_level,
        "currency": info.currency,
    }

# ==============================
# 💰 Compound Lot Strategy
# ==============================

def get_compound_config():
    return config.get("compound_lot", {})

# ==============================
# ⚠️ Risk Management
# ==============================

def get_risk_parameters():
    return config.get("risk_management", {})

# ==============================
# ⏬ Akses cepat
# ==============================

__all__ = [
    "config",
    "datetime",
    "pytz",
    "TIMEZONE",

    "is_weekday",
    "get_asset_for_today",
    "get_timezone",

    "get_general",
    "get_mode",
    "should_save_logs",
    "get_timeframe",

    "is_telegram_enabled",

    "get_account_config",
    "get_leverage",
    "get_contract_size",
    "get_account_info",

    "get_compound_config",
    "get_risk_parameters"
]
