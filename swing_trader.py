import numpy as np
import upstox_client
import pandas as pd
import pandas_ta as ta
import datetime
from upstox_client.rest import ApiException
from datetime import date

API_VERSION = "v2"
INSTRUMENT_TOKEN = "NSE_EQ|INE237A01028" # Kotak Bank
# INSTRUMENT_TOKEN = "NSE_EQ|INE002A01018" # Reliance
ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJrZXlfaWQiOiJza192MS4wIiwiYWxnIjoiSFMyNTYifQ.eyJzdWIiOiIxMDQ1NzEiLCJqdGkiOiI2NmFiMjk0MDdmODFmZjIyODYwNjAzYmMiLCJpc011bHRpQ2xpZW50IjpmYWxzZSwiaWF0IjoxNzIyNDkzMjQ4LCJpc3MiOiJ1ZGFwaS1nYXRld2F5LXNlcnZpY2UiLCJleHAiOjE3MjI1NDk2MDB9.JIDEa3DVTBSHrsZEGl2hzhil6Jd5qBWqNtfhQzvzLBU"


def round_nearest(x, a):
        return round(x / a) * a

def build_heikin_ashi_data(data):
    # Calculate Heikin-Ashi elements
    ha_open = pd.Series(np.nan, index=data.index)
    ha_close = (data['Open'] + data['High'] + data['Low'] + data['Close']) / 4.0
    ha_high = pd.Series(np.nan, index=data.index)
    ha_low = pd.Series(np.nan, index=data.index)
    # Special case for the first row (no previous Heikin-Ashi data)
    ha_open.iloc[0] = (data['Open'].iloc[0] + data['Close'].iloc[0]) / 2
    ha_low.iloc[0] = data['Low'].iloc[0]
    ha_high.iloc[0] = data['High'].iloc[0]
    # Calculate Heikin-Ashi elements for subsequent rows
    for i in range(1, len(data)):
        prev_ha_close = ha_close.iloc[i-1]
        prev_ha_open = ha_open.iloc[i-1]
        ha_open.iloc[i] = (prev_ha_open + prev_ha_close) / 2
        ha_high.iloc[i] = max(ha_open.iloc[i], ha_close.iloc[i], data['High'].iloc[i])
        ha_low.iloc[i] = min(ha_open.iloc[i], ha_close.iloc[i], data['Low'].iloc[i])
    data["Heikin Ashi - Open"] = ha_open
    data["Heikin Ashi - High"] = ha_high
    data["Heikin Ashi - Low"] = ha_low
    data["Heikin Ashi - Close"] = ha_close
    data["Heikin Ashi - Change"]= (data["Heikin Ashi - Close"] - data["Heikin Ashi - Open"]).apply(lambda x: round_nearest(x,0.05))
    return data

def fetch_historical_data(instrument, interval= "1minute", to_date= None, api_version="v2"):
    try:
        api_instance = upstox_client.HistoryApi()
        api_response = api_instance.get_historical_candle_data(instrument, interval, to_date, api_version)
        candles = api_response.data.candles
        columns = ["Timestamp","Open","High","Low","Close","Volume","Open Interest"]
        historical_data = pd.DataFrame(data=candles, columns=columns)
        historical_data["Timestamp"] = pd.to_datetime(historical_data["Timestamp"])
        historical_data = historical_data.sort_values(by='Timestamp')
        return historical_data
    except ApiException as e:
        print("Exception when calling HistoryApi->get_historical_candle_data: %s\n" % e)

today = date.today()
today_date_string = today.strftime("%Y-%m-%d")

data = fetch_historical_data(INSTRUMENT_TOKEN, interval= "day",to_date=today_date_string)


data = build_heikin_ashi_data(data)
data.to_csv("candle_data.csv")

data["Heikin Ashi - T-1 Change"]= data["Heikin Ashi - Change"].shift(1).fillna(0)
data["Heikin Ashi - T-2 Change"]= data["Heikin Ashi - Change"].shift(2).fillna(0)
data["Heikin Ashi - T+1 Change"]= data["Heikin Ashi - Change"].shift(-1).fillna(0)
data["Heikin Ashi - T+2 Change"]= data["Heikin Ashi - Change"].shift(-2).fillna(0)

data["Heikin Ashi - Change is Positive"] = data["Heikin Ashi - Change"] >= 0.0
data["Heikin Ashi - Change is Negative"] = data["Heikin Ashi - Change"] < 0.0
data['Heikin Ashi - T-1 Change is Negative'] = data["Heikin Ashi - T-1 Change"] < 0.0
data['Heikin Ashi - T-2 Change is Negative'] = data["Heikin Ashi - T-2 Change"] < 0.0

data['Entry Signal'] = data["Heikin Ashi - Change is Positive"] & data['Heikin Ashi - T-1 Change is Negative']
# data['Exit Signal'] = data["Heikin Ashi - Change is Negative"] & data['Heikin Ashi - T-1 Change is Negative']
data['Exit Signal'] = data["Heikin Ashi - Change is Negative"]

trades = []
trade = dict()
trade_active = False
trade_active_candles = 0
for index, row in data.iterrows():
    if trade_active is True:
        if row["Exit Signal"] is True:
            # Exit Condition is met
            trade["exit_timestamp"] = row["Timestamp"]
            trade["sell_price"] = row["Close"]
            trade["profit_and_loss"] = trade["sell_price"] - trade["buy_price"]
            trade["active_duration"] = trade_active_candles
            trades.append(trade)
            trade = dict()
            trade_active = False
            trade_active_candles = 0
            print(f"Exited Trade at {row["Timestamp"]}")
            continue
        trade_active_candles += 1
    else:
        if row["Entry Signal"] is True:
            trade["entry_timestamp"] = row["Timestamp"]
            trade["buy_price"] = row["Close"]
            trade_active = True
            trade_active_candles += 1
            print(f"Entered Trade at {row["Timestamp"]}")

trades_dataframe = pd.DataFrame(data=trades)

trades_dataframe["Profitable"] = trades_dataframe["profit_and_loss"] > 0.0

print(f"Overall Profit :: {trades_dataframe["profit_and_loss"].sum()}")

trades_dataframe.to_csv("trades.csv")
print(data)


