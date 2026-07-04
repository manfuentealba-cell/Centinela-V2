import os
import time
import requests
import pandas as pd
import ta
from datetime import datetime

TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
MONEDAS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": mensaje}
    requests.post(url, data=data)

def obtener_velas(symbol="BTCUSDT"):
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=5m&limit=50"
        data = requests.get(url, timeout=10).json()
        if not data: 
            return None
        df = pd.DataFrame(data, columns=['time','open','high','low','close','volume','close_time','qav','trades','taker_base','taker_quote','ignore'])
        df['close'] = df['close'].astype(float)
        df['open'] = df['open'].astype(float)
        return df
    except:
        return None

def analizar(df, symbol):
    if df is None or len(df) < 20:
        return None
        
    df['rsi'] = ta.momentum.RSIIndicator(df['close']).rsi()
    df['ema20'] = ta.trend.EMAIndicator(df['close'], 20).ema_indicator()
    df['ema50'] = ta.trend.EMAIndicator(df['close'], 50).ema_indicator()
    
    df = df.dropna()
    if len(df) < 3:
        return None
    
    ultima = df.iloc[-1]
    ultimas_3 = df.tail(3)
    
    # LONG: RSI bajo + Tendencia alcista + Vela verde
    long_cond = (ultima['rsi'] < 35) and (ultima['ema20'] > ultima['ema50']) and (ultima['close'] > ultima['open'])
    
    # SHORT: RSI alto + 3 velas rojas + Caída >1.5%
    caida_pct = ((ultimas_3.iloc[-1]['close'] - ultimas_3.iloc[0]['open']) / ultimas_3.iloc[0]['open']) * 100
    short_cond = (ultima['rsi'] > 65) and all(ultimas_3['close'] < ultimas_3['open']) and (caida_pct < -1.5)
    
    if long_cond:
        return f"🚀 ALERTA LONG 🚀\nMoneda: {symbol}\nPrecio: ${ultima['close']:,.2f}\nRSI: {ultima['rsi']:.1f}\nEMA20 > EMA50"
    
    if short_cond:
        return f"🔻 ALERTA SHORT 🔻\nMoneda: {symbol}\nPrecio: ${ultima['close']:,.2f}\nCaída 15min: {caida_pct:.2f}%"
    
    return None

import time
from datetime import datetime

while True:
    try:
        for moneda in MONEDAS:
            df = obtener_velas(moneda)
            alerta = analizar(df, moneda)
            if alerta:
                enviar_telegrama(alerta)
                time.sleep(10)
        
        ahora = datetime.now().strftime("%H:%M")
        print(f"Vigilando OK... {ahora}") # Railway necesita ver esto cada minuto
        
        time.sleep(60) # Espera 1 minuto. Asi Railway no lo mata

    except Exception as e:
        print(f"Error general: {e}")
        time.sleep(60)
