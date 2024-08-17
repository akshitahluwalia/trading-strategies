import pytz
import time
import datetime
import pandas as pd
import numpy as np
import upstox_client
import pandas_ta as ta
from datetime import date
from upstox_client.rest import ApiException

UPSTOX_API_SECRET = "hwijgmi6cs"
UPSTOX_API_KEY = "45a560fd-65cc-46df-bf70-82c692698188"
NSE_INSTRUMENT_MASTER_PATH = "nse-500-equity-instruments.csv"
UPSTOX_INSTRUMENTS_MASTER_PATH = "upstox-nse-instrument-list.csv"
UPSTOX_ACCESS_TOKEN = ""

def round_nearest(x, a):
    return round(x / a) * a

def fetch_instrument_data(instrument_key, data_type= "historical", interval= "day", to_date= None, api_version='v2'):
    try:
        api_instance = upstox_client.HistoryApi()
        api_response = None
        if data_type == "historical":
            api_response = api_instance.get_historical_candle_data(instrument_key, interval, to_date, api_version)
        elif data_type == "intraday":
            api_response = api_instance.get_intra_day_candle_data(instrument_key, interval, api_version)
        candles = api_response.data.candles
        columns = ["Timestamp","Open","High","Low","Close","Volume","Open Interest"]
        historical_data = pd.DataFrame(data=candles, columns=columns)
        historical_data["Timestamp"] = pd.to_datetime(historical_data["Timestamp"])
        historical_data = historical_data.sort_values(by='Timestamp')
        return historical_data
    except ApiException as e:
        print("Exception when calling HistoryApi->get_historical_candle_data: %s\n" % e)

def construct_candle(intraday_data, date):
    open = 0
    high = 0
    close = 0
    low = 9999999999
    volume = 0 
    open_interest = 0

    for idx, row in intraday_data.iterrows():
        if idx == 0:
            open = int(row["Open"])
        if int(row["High"]) > high:
            high = int(row["High"])
        if int(row["Low"]) < low:
            low = int(row["Low"])
        close = int(row["Close"])
        volume += int(row["Volume"])
    
    return {
        "Timestamp" : date,
        "Open" : open,
        "High" : high,
        "Low" : low,
        "Close" : close,
        "Volume" : volume,
        "Open Interest" : open_interest
    }
        
def build_heikin_ashi_data(data):
    # Calculate Heikin-Ashi elements
    ha_open = pd.Series(np.nan, index=data.index)
    ha_close = (data['Open'] + data['High'] + data['Low'] + data['Close']) / 4.0
    ha_high = pd.Series(np.nan, index=data.index)
    ha_low = pd.Series(np.nan, index=data.index)

    # Special case for the first row (no previous Heikin-Ashi data)
    ha_open.iloc[0] = (data['Open'].iloc[0] + data['Close'].iloc[0]) / 2.0
    ha_low.iloc[0] = data['Low'].iloc[0]
    ha_high.iloc[0] = data['High'].iloc[0]

    # Calculate Heikin-Ashi elements for subsequent rows
    for i in range(1, len(data)):
        prev_ha_close = ha_close.iloc[i-1]
        prev_ha_open = ha_open.iloc[i-1]
        ha_open.iloc[i] = (prev_ha_open + prev_ha_close) / 2
        ha_high.iloc[i] = max(ha_open.iloc[i], ha_close.iloc[i], data['High'].iloc[i])
        ha_low.iloc[i] = min(ha_open.iloc[i], ha_close.iloc[i], data['Low'].iloc[i])

    data["Heikin Ashi - Open"] = ha_open.apply(lambda x: round_nearest(x,0.05))
    data["Heikin Ashi - High"] = ha_high
    data["Heikin Ashi - Low"] = ha_low
    data["Heikin Ashi - Close"] = ha_close.apply(lambda x: round_nearest(x,0.05))
    return data

def build_signals(data):
    price_change_heiken_ashi = (data["Heikin Ashi - Close"] - data["Heikin Ashi - Open"]).apply(lambda x: round_nearest(x,0.05))
    data["Heikin Ashi - T Change"] = price_change_heiken_ashi
    data['Heikin Ashi - T-1 Change'] = price_change_heiken_ashi.shift(1).fillna(0)
    data['Heikin Ashi - T-2 Change'] = price_change_heiken_ashi.shift(2).fillna(0)
    data["Heikin Ashi - T Change is Positive"] = data["Heikin Ashi - T Change"] >= 0.0
    data['Heikin Ashi - T-1 Change is Negative'] = data['Heikin Ashi - T-1 Change'] <= 0.0
    data['Heikin Ashi - T-2 Change is Negative'] = data['Heikin Ashi - T-2 Change'] <= 0.0
    data['Heikin Ashi - Buy Signal'] = data["Heikin Ashi - T Change is Positive"] & data['Heikin Ashi - T-1 Change is Negative'] & data['Heikin Ashi - T-2 Change is Negative']
    data['Heikin Ashi - Candle Category - BEARISH'] = data["Heikin Ashi - High"] <= data["Heikin Ashi - Open"]
    data['Heikin Ashi - Candle Category - BULLISH'] = data["Heikin Ashi - Open"] <= data["Heikin Ashi - Low"]
    return data

def execute(row):
    try:    
        trading_symbol = row["Symbol"]
        BROKER_INSTRUMENT = UPSTOX_ISNTRUMENTS[UPSTOX_ISNTRUMENTS["tradingsymbol"] == row["Symbol"]]
        instrument_key = BROKER_INSTRUMENT["instrument_key"].iloc[0]
        historical_data = fetch_instrument_data(instrument_key, data_type="historical", to_date= CURRENT_DATE)
        intraday_data = fetch_instrument_data(instrument_key, data_type="intraday", interval="1minute", to_date= CURRENT_DATE)
        current_day_candle = construct_candle(intraday_data, CURRENT_DATE_FORMATTED)
        historical_data.loc[len(historical_data)] = current_day_candle

        heikin_ashi_data = build_heikin_ashi_data(historical_data)
        heikin_ashi_data = build_signals(heikin_ashi_data)

        last_candle_df = heikin_ashi_data.tail(1)
        last_candle = last_candle_df.iloc[0].to_dict()

        if last_candle['Heikin Ashi - Buy Signal'] == True:
            last_candle["Instrument Name"] = trading_symbol
            TRADE_ACTIVE_SCRIPTS.append(last_candle)
    except Exception as e:
        print("Encountered Exception")

DATA = dict()
IST_TIMEZONE = pytz.timezone('Asia/Kolkata')
CURRENT_DATE = date.today().strftime("%Y-%m-%d")
CURRENT_SNAPSHOT = datetime.datetime.now(tz=IST_TIMEZONE)
NSE_EQUITY_INSTRUMENTS = pd.read_csv(NSE_INSTRUMENT_MASTER_PATH)
UPSTOX_ISNTRUMENTS = pd.read_csv(UPSTOX_INSTRUMENTS_MASTER_PATH)
CURRENT_DATE_FORMATTED = CURRENT_SNAPSHOT.strftime('%Y-%m-%d 00:00:00+05:30')
TRADE_ACTIVE_SCRIPTS = list()

for idx, row in NSE_EQUITY_INSTRUMENTS.iterrows():
    try:    
        print(f">>>> PROCESSING ({idx} of {len(NSE_EQUITY_INSTRUMENTS)}) >>>> ", row["Symbol"])
        execute(row)
    except Exception as e:
        time.sleep(60)
        execute(row)
        
ACTIVE_TRADES = pd.DataFrame(TRADE_ACTIVE_SCRIPTS)
ACTIVE_TRADES.to_csv(f"ACTIVE TRADES - {CURRENT_DATE}.csv", index=False)