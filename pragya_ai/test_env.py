# test_env.py

import os
from dotenv import load_dotenv

load_dotenv()

mt5_login = os.getenv("MT5_LOGIN")
mt5_password = os.getenv("MT5_PASSWORD")

print(f"Login (raw): {repr(mt5_login)}")
print(f"Password (raw): {repr(mt5_password)}")