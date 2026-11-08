"""
Live Multi-Asset ICT Scanner (NQ & BTC)
Executes via GitHub Actions cron schedule every 15 minutes.
"""
import os
import pandas as pd
import yfinance as yf
from fetch_data import _binance
from ict_strategy_v2 import ICTStrategyV2, send_discord_alert

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

def fetch_latest_data(symbol: str) -> pd.DataFrame:
    """Fetches recent data for live signal checking."""
    if symbol == "BTCUSDT":
        # Pull recent Binance data (last ~5 days of 15m bars)
        import time
        end_ms = int(time.time() * 1000)
        start_ms = end_ms - (5 * 24 * 60 * 60 * 1000)
        return _binance(symbol, "15m", start_ms, end_ms)
    elif symbol == "NQ=F":
        # Pull recent Yahoo Finance data for Nasdaq futures
        df = yf.download(symbol, period="5d", interval="15m", progress=False)
        if df.empty:
            return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']].rename(
            columns=lambda x: x.lower()
        )
        return df.dropna()
    return pd.DataFrame()

def run_scanner():
    assets = [
        {"symbol": "BTCUSDT", "name": "Bitcoin (BTC)"},
        {"symbol": "NQ=F", "name": "Nasdaq 100 (NQ)"}
    ]
    
    print("🔍 Running ICT Strategy V2 Scan for NQ & BTC...")
    
    for asset in assets:
        sym = asset["symbol"]
        df = fetch_latest_data(sym)
        
        if df.empty:
            print(f"⚠️ Could not fetch live data for {asset['name']}")
            continue
            
        strategy = ICTStrategyV2(df, asset['name'])
        setups = strategy.analyze()
        
        if setups:
            # Check if the latest setup happened on the very last candle (active now)
            latest_setup = setups[-1]
            print(f"🚨 Setup found on {asset['name']}! Time: {latest_setup['time']}")
            
            if DISCORD_WEBHOOK_URL:
                send_discord_alert(latest_setup, DISCORD_WEBHOOK_URL)
            else:
                print("⚠️ DISCORD_WEBHOOK_URL environment variable not set.")
        else:
            print(f"✔️ No active setup for {asset['name']}.")

if __name__ == "__main__":
    run_scanner()