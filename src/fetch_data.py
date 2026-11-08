"""
Data Fetcher Module for Binance
"""
import pandas as pd
import requests

def _binance(symbol: str, timeframe: str, start_time: int, end_time: int) -> pd.DataFrame:
    """Fetches historical OHLCV klines from Binance Public API."""
    url = "https://api.binance.com/api/v3/klines"
    all_data = []
    
    current_start = start_time
    while current_start < end_time:
        params = {
            "symbol": symbol,
            "interval": timeframe,
            "startTime": current_start,
            "endTime": end_time,
            "limit": 1000
        }
        response = requests.get(url, params=params)
        if response.status_code != 200:
            print(f"❌ Error fetching data from Binance: {response.text}")
            break
            
        data = response.json()
        if not data:
            break
            
        all_data.extend(data)
        # Move start time forward to the close time of the last candle + 1ms
        current_start = data[-1][6] + 1

    if not all_data:
        return pd.DataFrame()

    df = pd.DataFrame(all_data, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'number_of_trades',
        'taker_buy_base', 'taker_buy_quote', 'ignore'
    ])
    
    # Clean up data types and index
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)
        
    df = df[['open', 'high', 'low', 'close', 'volume']]
    return df