import os
from dotenv import load_dotenv
import requests
import time
import pandas as pd

load_dotenv()

TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
SYMBOL = "BTCUSDT"

def send_telegram(message):
    url = "https://api.telegram.org/bot" + TOKEN + "/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}
    r = requests.post(url, data=data)
    print("Estado:", r.status_code)

def get_klines():
    # OJO: Esta es la API REAL. Para DEMO usa: https://testnet.binance.vision/api/v3/klines
    url = "https://api.binance.com/api/v3/klines?symbol=" + SYMBOL + "&interval=5m&limit=50"
    data = requests.get(url).json()
    df = pd.DataFrame(data, columns=['time','o','h','l','c','v','x','q','n','t','Q','B'])
    df[['o','h','l','c','v']] = df[['o','h','l','c','v']].astype(float)
    return df

def calcular_indicadores(df):
    # RSI 14
    delta = df['c'].diff()
    gain = delta.where(delta > 0, 0).rolling(window=14).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # Bandas de Bollinger 20
    df['ma20'] = df['c'].rolling(window=20).mean()
    df['std'] = df['c'].rolling(window=20).std()
    df['bb_alta'] = df['ma20'] + (df['std'] * 2)
    df['bb_baja'] = df['ma20'] - (df['std'] * 2)
    
    # Volumen Promedio 20
    df['vol_prom'] = df['v'].rolling(window=20).mean()
    return df

def detectar_patron_vela(df):
    ultima = df.iloc[-1]
    anterior = df.iloc[-2]
    # Martillo Alcista
    cuerpo = abs(ultima['c'] - ultima['o'])
    mecha_baja = min(ultima['o'], ultima['c']) - ultima['l']
    if ultima['c'] > ultima['o'] and mecha_baja > cuerpo * 2:
        return "MARTILLO ALCISTA"
    return "NINGUNO"

send_telegram("CENTINELA TRADER V1 ACTIVO\nBuscando Scalp LONG en BTC 5min")

while True:
    try:
        df = get_klines()
        df = calcular_indicadores(df)
        patron = detectar_patron_vela(df)
        ultima = df.iloc[-1]
        
        # FILTRO DE COMPRA: RSI Bajo + Toca BB Baja + Volumen Alto + Patron
        compra = (ultima['rsi'] < 35 and 
                  ultima['c'] < ultima['bb_baja'] and 
                  ultima['v'] > ultima['vol_prom'] * 1.8 and
                  patron != "NINGUNO")
        
        if compra:
            sl = ultima['bb_baja'] * 0.998
            tp = ultima['ma20']
            
            mensaje = "🚨 OPORTUNIDAD SCALP LONG 🚨\n\n"
            mensaje = mensaje + "Precio: $" + str(round(ultima['c'],2)) + "\n"
            mensaje = mensaje + "Patron: " + patron + "\n"
            mensaje = mensaje + "RSI: " + str(round(ultima['rsi'],2)) + "\n"
            mensaje = mensaje + "Vol: +" + str(round((ultima['v']/ultima['vol_prom']-1)*100,0)) + "%\n\n"
            mensaje = mensaje + "SL: $" + str(round(sl,2)) + "\n"
            mensaje = mensaje + "TP: $" + str(round(tp,2)) + "\n"
            mensaje = mensaje + "RIESGO MAX: $1.5 USD"
            send_telegram(mensaje)
        
        print("Vigilando... RSI:" + str(round(ultima['rsi'],1)) + " Precio:$" + str(round(ultima['c'],2)))
        time.sleep(60) # Revisa cada 1 minuto
        
    except Exception as e:
        print("Error:", e)
        time.sleep(60)