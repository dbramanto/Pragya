# /pragya_ai/main.py

import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime
from core.agents import synthesizer
from core.analyst import analyst
from core.evaluator import evaluator
from core import mt5_utils
import yaml
import shutil
import os

def is_performance_anomaly_detected(log_file="logs/trading_decisions.csv", loss_streak_threshold=5):
    try:
        if not os.path.exists(log_file):
            return False
            
        df_logs = pd.read_csv(log_file)
        if df_logs.empty:
            return False

        last_decisions = df_logs['decision'].tail(loss_streak_threshold)
        if len(last_decisions) < loss_streak_threshold:
            return False

        if all(decision != 'Hold' for decision in last_decisions):
            return True
            
    except Exception as e:
        print(f"Error saat mengecek anomali performa: {e}")
        return False
        
    return False

def is_periodic_check_due():
    return datetime.now().weekday() == 6

def main():
    try:
        config = mt5_utils.load_config('config.yaml')
        general_config = config['general']
        assets_config = config['assets']
        account_config = config['account']
        
        if general_config['symbol'] == 'auto':
            today = datetime.now().weekday()
            if today >= 0 and today <= 4:
                symbol = assets_config['weekday']
            else:
                symbol = assets_config['weekend']
        else:
            symbol = general_config['symbol']
        
        timeframe = general_config['timeframe']
        
        server_to_use = account_config.get('server')
        if server_to_use and server_to_use.lower() != 'auto':
            mt5_utils.initialize_mt5(server_to_use)
        else:
            print("Mode Server Otomatis: Akan menggunakan server terminal MT5 yang aktif.")
            mt5_utils.initialize_mt5()

        print("Mengambil data historis dari MT5...")
        df = mt5_utils.get_candles(symbol, timeframe, bars=500)
        
        if df is None or df.empty:
            raise RuntimeError("Gagal mengambil data dari MT5 atau data kosong.")

        if is_performance_anomaly_detected() or is_periodic_check_due():
            print("\nTrigger Tuning: Kondisi anomali atau periodik terpenuhi.")
            best_config, performance = evaluator.find_best_config(config, df)
            mt5_utils.shutdown_mt5()

            if best_config and performance:
                print("\nProses tuning selesai! Konfigurasi terbaik telah ditemukan.")
                print("----------------------------------------------------------")
                for key, value in performance.items():
                    print(f"- {key.replace('_', ' ').title()}: {value}")
                
                new_version_number = evaluator.save_best_config_version(best_config, performance)
                
                source_file = os.path.join('history', f'config_v{new_version_number}.yaml')
                shutil.copyfile(source_file, 'config.yaml')
                print("\nconfig.yaml berhasil diperbarui dengan versi terbaik!")
            else:
                print("Tidak ada konfigurasi yang lebih baik ditemukan.")

        else:
            print("\nMode Normal: Tidak ada tuning yang diperlukan saat ini.")
            
            reports = synthesizer.synthesize_reports(df, config)
            decision = analyst.analyze_reports(reports, config)
            
            mt5_utils.shutdown_mt5()
            
            print("\nKeputusan Trading:")
            print("-------------------")
            print(f"Time: {decision['time']:%Y-%m-%d %H:%M:%S}")
            print(f"Decision: {decision['decision']}")
            print(f"Confidence Score: {decision['confidence_score']:.2f}%")
            print(f"Rationale: {decision['rationale']}")
            print("-------------------")

    except RuntimeError as e:
        print(f"Error: {e}")
    except FileNotFoundError as e:
        print(f"Error: {e}")
    except ValueError as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()