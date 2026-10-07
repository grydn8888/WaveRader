import os
import time
import requests
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime

def fetch_live_market_data():
    df = yf.download(tickers='EURUSD=X', period='1d', interval='1m', progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df.dropna().reset_index()

def calculate_setup_scores(df):
    window = 20
    df['hl_range'] = df['High'] - df['Low']
    rolling_range = df['hl_range'].rolling(window).mean()
    df['compression'] = 1.0 / (rolling_range + 1e-6)
    df['compression_pctl'] = df['compression'].rolling(100).rank(pct=True) * 100
    df['ema50'] = df['Close'].ewm(span=50, adjust=False).mean()
    df['gravity'] = (df['Close'] - df['ema50']) / (df['hl_range'] + 1e-6)
    
    latest = df.iloc[-2] # fully closed candle
    timestamp = str(latest['Datetime']) if 'Datetime' in latest else datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    return timestamp, latest['Close'], latest['compression_pctl'], latest['gravity']

def log_scan_result(timestamp, price, comp_score, gravity_score, triggered):
    log_file = "scan_history.csv"
    file_exists = os.path.isfile(log_file)
    new_row = pd.DataFrame([{
        'Timestamp': timestamp,
        'Price': price,
        'Compression_Pctl': comp_score,
        'Gravity': gravity_score,
        'Triggered': triggered
    }])
    new_row.to_csv(log_file, mode='a', header=not file_exists, index=False)
    print(f"[{timestamp}] Logged scan -> Price: {price:.5f} | Comp Pctl: {comp_score:.1f}%")

def broadcast_alert(message):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if token and chat_id:
        try:
            requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"})
        except Exception as e:
            print(f"Telegram error: {e}")

    discord_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if discord_url:
        try:
            requests.post(discord_url, json={"content": message})
        except Exception as e:
            print(f"Discord error: {e}")

def main_loop():
    print("🚀 Playa' Swurv Fly.io Engine Initialized. Running continuous scan loop...")
    while True:
        try:
            df = fetch_live_market_data()
            timestamp, price, comp_score, gravity_score = calculate_setup_scores(df)
            
            triggered = comp_score <= 20.0
            log_scan_result(timestamp, price, comp_score, gravity_score, triggered)
            
            if triggered:
                message = (
                    f"🚨 **PLAYA' SWURV SETUP DETECTED** 🚨\n"
                    f"• **Time**: `{timestamp}`\n"
                    f"• **Pair**: EUR/USD\n"
                    f"• **Price**: `{price:.5f}`\n"
                    f"• **Compression Pctl**: `{comp_score:.1f}%` (Coiled)\n"
                    f"• **Gravity Vector**: `{gravity_score:.2f}`\n"
                    f"• **Status**: *Execution Grid Armed (Fly.io Node Active)*"
                )
                broadcast_alert(message)
                
        except Exception as e:
            print(f"Scan loop error: {e}")
            
        # Sleep for exactly 5 minutes before the next scan
        time.sleep(300)

if __name__ == "__main__":
    main_loop()
