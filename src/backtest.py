"""
Multi-Asset Backtest Engine & Performance Simulator for ICT Strategy V2
"""
import pandas as pd
from fetch_data import _binance
import yfinance as yf
from datetime import datetime, timedelta
from ict_strategy_v2 import ICTStrategyV2

def fetch_asset_data(symbol: str) -> pd.DataFrame:
    """Fetches data, automatically handling Binance history vs Yahoo Finance 60-day intraday limit."""
    if "USDT" in symbol or "BTC" in symbol:
        # Binance deep history (Jan 2024 - May 2024)
        return _binance(symbol, "15m", 1704067200000, 1717199999000)
    else:
        # Yahoo Finance limits 15m intraday data to the last 60 days max
        print(f"⏳ Fetching last 60 days of 15M data for {symbol} from Yahoo Finance...")
        df = yf.download(symbol, period="60d", interval="15m", progress=False)
        if df.empty:
            return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']].rename(
            columns=lambda x: x.lower()
        )
        return df.dropna()

def simulate_trades(df: pd.DataFrame, setups: list):
    results = []
    for setup in setups:
        entry_time = setup['time']
        direction = setup['direction']
        stop_loss = setup['stop']
        target_price = setup['target']
        
        future_candles = df.loc[df.index > entry_time]
        outcome = "OPEN"
        pnl_r = 0.0
        
        for idx, candle in future_candles.iterrows():
            high = candle['high']
            low = candle['low']
            
            if direction == 'LONG':
                if low <= stop_loss:
                    outcome = "LOSS"
                    pnl_r = -1.0
                    break
                elif high >= target_price:
                    outcome = "WIN"
                    pnl_r = 2.0
                    break
            elif direction == 'SHORT':
                if high >= stop_loss:
                    outcome = "LOSS"
                    pnl_r = -1.0
                    break
                elif low <= target_price:
                    outcome = "WIN"
                    pnl_r = 2.0
                    break
                    
        if outcome != "OPEN":
            results.append({'outcome': outcome, 'pnl_r': pnl_r})
            
    return pd.DataFrame(results)

def calculate_streaks(results_df: pd.DataFrame):
    max_win_streak = 0
    max_loss_streak = 0
    curr_win = 0
    curr_loss = 0
    
    for outcome in results_df['outcome']:
        if outcome == 'WIN':
            curr_win += 1
            curr_loss = 0
            max_win_streak = max(max_win_streak, curr_win)
        else:
            curr_loss += 1
            curr_win = 0
            max_loss_streak = max(max_loss_streak, curr_loss)
            
    return max_win_streak, max_loss_streak

def run_multi_asset_backtest():
    assets = [
        {"symbol": "BTCUSDT", "name": "Bitcoin (BTC)"},
        {"symbol": "ETHUSDT", "name": "Ethereum (ETH)"},
        {"symbol": "NQ=F", "name": "Nasdaq 100 Futures (NQ)"},
        {"symbol": "GC=F", "name": "Gold Futures"}
    ]
    
    for asset in assets:
        sym = asset["symbol"]
        print(f"\n=========================================")
        print(f" Testing Asset: {asset['name']} ({sym})")
        print(f"=========================================")
        
        df = fetch_asset_data(sym)
        if df.empty:
            print(f"❌ Could not retrieve data for {sym}. Skipping.")
            continue
            
        strategy = ICTStrategyV2(df, sym)
        setups = strategy.analyze()
        print(f"📊 Signals Triggered: {len(setups)}")
        
        if not setups:
            print("No setups found.")
            continue
            
        results_df = simulate_trades(df, setups)
        if results_df.empty:
            print("No completed trades.")
            continue
            
        total = len(results_df)
        wins = len(results_df[results_df['outcome'] == 'WIN'])
        losses = len(results_df[results_df['outcome'] == 'LOSS'])
        win_rate = (wins / total) * 100
        pf = (wins * 2.0) / (losses * 1.0) if losses > 0 else 999
        expectancy = ((wins * 2.0) - losses) / total
        max_win, max_loss = calculate_streaks(results_df)
        
        print(f" Trades Executed   : {total}")
        print(f" Win Rate          : {win_rate:.2f}% ({wins}W / {losses}L)")
        print(f" Profit Factor     : {pf:.2f}")
        print(f" Net Expectancy    : {expectancy:+.3f} R per trade")
        print(f" Max Winning Streak: {max_win}")
        print(f" Max Losing Streak : {max_loss}")
        print(f" Total Net Return  : {results_df['pnl_r'].sum():+.2f} R")

if __name__ == "__main__":
    run_multi_asset_backtest()