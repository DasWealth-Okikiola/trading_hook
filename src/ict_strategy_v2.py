"""
ICT Multi-Timeframe Strategy Engine (v2.0)
Rules:
- 4H Trend Filter (EMA 50)
- Kill Zone Filter (London 07:00-10:00 UTC, NY 13:00-16:00 UTC)
- 15M CHoCH + Trend Continuation Entry Model
- Dynamic Stop (Swing High/Low) & Target (1:2 R:R)
"""

import pandas as pd
import numpy as np
import requests

def apply_htf_trend_filter(df_15m: pd.DataFrame, htf_ema_period: int = 50) -> pd.DataFrame:
    """Resamples 15m data to 4H to compute HTF Trend Bias."""
    df = df_15m.copy()
    
    # Resample to 4-Hour candles
    df_4h = df.resample('4h').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()

    # Calculate 4H EMA
    df_4h['htf_ema'] = df_4h['close'].ewm(span=htf_ema_period, adjust=False).mean()
    df_4h['htf_bias'] = np.where(df_4h['close'] > df_4h['htf_ema'], 'bullish', 'bearish')

    # Forward fill 4H bias back into 15m dataframe
    df['htf_bias'] = df_4h['htf_bias'].reindex(df.index, method='ffill')
    return df

def is_kill_zone(dt) -> str:
    """Checks if timestamp falls within institutional Kill Zones (UTC)."""
    hour = dt.hour
    if 7 <= hour < 10:
        return 'london'
    elif 13 <= hour < 16:
        return 'ny_am'
    return 'none'

class ICTStrategyV2:
    def __init__(self, df: pd.DataFrame, symbol: str):
        self.df = apply_htf_trend_filter(df)
        self.symbol = symbol

    def analyze(self):
        setups = []
        df = self.df

        for i in range(20, len(df)):
            current_time = df.index[i]
            zone = is_kill_zone(current_time)
            
            # Skip if outside Kill Zones
            if zone == 'none':
                continue

            bias = df['htf_bias'].iloc[i]
            close = df['close'].iloc[i]
            prev_high = df['high'].iloc[i-10:i].max()
            prev_low = df['low'].iloc[i-10:i].min()

            # Bullish Setup
            if bias == 'bullish' and close > prev_high:
                entry = close
                stop_loss = prev_low
                risk = entry - stop_loss
                if risk <= 0:
                    continue
                target = entry + (2.0 * risk)

                setups.append({
                    'symbol': self.symbol,
                    'direction': 'LONG',
                    'zone': zone,
                    'entry': entry,
                    'stop': stop_loss,
                    'target': target,
                    'time': current_time,
                    'reason': f"HTF Bullish Bias + Breakout in {zone.upper()} Kill Zone"
                })

            # Bearish Setup
            elif bias == 'bearish' and close < prev_low:
                entry = close
                stop_loss = prev_high
                risk = stop_loss - entry
                if risk <= 0:
                    continue
                target = entry - (2.0 * risk)

                setups.append({
                    'symbol': self.symbol,
                    'direction': 'SHORT',
                    'zone': zone,
                    'entry': entry,
                    'stop': stop_loss,
                    'target': target,
                    'time': current_time,
                    'reason': f"HTF Bearish Bias + Breakdown in {zone.upper()} Kill Zone"
                })

        return setups

def send_discord_alert(setup: dict, webhook_url: str):
    """Formats and dispatches rich trade signals to Discord."""
    color = 5763719 if setup['direction'] == 'LONG' else 15548997
    
    embed = {
        "title": f"🚨TRADE ALERT: {setup['symbol']} ({setup['direction']})",
        "description": f"**Reason:** {setup['reason']}",
        "color": color,
        "fields": [
            {"name": "Symbol", "value": setup['symbol'], "inline": True},
            {"name": "Direction", "value": setup['direction'], "inline": True},
            {"name": "Kill Zone", "value": setup['zone'].upper(), "inline": True},
            {"name": "Entry Price", "value": f"${setup['entry']:.2f}", "inline": True},
            {"name": "Stop Loss", "value": f"${setup['stop']:.2f}", "inline": True},
            {"name": "Take Profit (1:2)", "value": f"${setup['target']:.2f}", "inline": True},
            {"name": "Timestamp", "value": str(setup['time']), "inline": False}
        ],
        "footer": {"text": "KIKI Trading Scanner Bot v2.0 🤞💰"}
    }
    
    payload = {"embeds": [embed]}
    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()
        print(f"✅ Alert sent for {setup['symbol']} {setup['direction']}")
    except Exception as e:
        print(f"❌ Failed to send Discord alert: {e}")