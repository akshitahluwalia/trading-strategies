import numpy as np
import pandas as pd
import upstox_client
from datetime import date
import pandas_ta as ta
from upstox_client.rest import ApiException

INSTRUMENT_TOKEN = "NSE_FO|55225"
API_VERSION = "v2"
API_KEY = "45a560fd-65cc-46df-bf70-82c692698188"
API_SECRET = "hwijgmi6cs"
REDIRECT_URL = "https://testadbfo.com/upstox/login/callback"
POSTBACK_URL = "https://testadbfo.com/upstox/postback"
CUSTOM_STATE = "CUSTOM-STATE-VALUE"
ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJrZXlfaWQiOiJza192MS4wIiwiYWxnIjoiSFMyNTYifQ.eyJzdWIiOiIxMDQ1NzEiLCJqdGkiOiI2NjhlMWExMmNjYWE1MjNhNjEzNWJiNDMiLCJpc011bHRpQ2xpZW50IjpmYWxzZSwiaWF0IjoxNzIwNTg4ODE4LCJpc3MiOiJ1ZGFwaS1nYXRld2F5LXNlcnZpY2UiLCJleHAiOjE3MjA2NDg4MDB9.JZnTya0dwpaMWgKW_M7_tE2z8cCuNuLiLck-tKVdD2Y"

class Omega(object):
    def __init__(self,instrument):
        self.instrument = instrument
        self.api_version = "v2"
        self.historical_data = None
        self.intraday_data = None
        self.data = None

    def assemble_data(self):
        self.data = pd.concat([self.historical_data, self.intraday_data])
        return self.data

    def fetch_intraday_data(self, interval= "1minute"):
        try:
            api_instance = upstox_client.HistoryApi()
            api_response = api_instance.get_intra_day_candle_data(self.instrument, interval, self.api_version)
            candles = api_response.data.candles
            columns = ["Timestamp","Open","High","Low","Close","Volume","Open Interest"]
            self.intraday_data = pd.DataFrame(data=candles, columns=columns)
            self.intraday_data["Timestamp"] = pd.to_datetime(self.intraday_data["Timestamp"])
            self.intraday_data = self.intraday_data.sort_values(by='Timestamp')
            return self.intraday_data
        except ApiException as e:
            print("Exception when calling HistoryApi->get_intraday_candle_data: %s\n" % e)
    
    def fetch_historical_data(self, interval= "1minute", to_date= None):
        try:
            api_instance = upstox_client.HistoryApi()
            api_response = api_instance.get_historical_candle_data(self.instrument, interval, to_date, self.api_version)
            candles = api_response.data.candles
            columns = ["Timestamp","Open","High","Low","Close","Volume","Open Interest"]
            self.historical_data = pd.DataFrame(data=candles, columns=columns)
            self.historical_data["Timestamp"] = pd.to_datetime(self.historical_data["Timestamp"])
            self.historical_data = self.historical_data.sort_values(by='Timestamp')
            return self.historical_data
        except ApiException as e:
            print("Exception when calling HistoryApi->get_historical_candle_data: %s\n" % e)

    def build_heikin_ashi_data(self):
        # Calculate Heikin-Ashi elements
        ha_open = pd.Series(np.nan, index=self.data.index)
        ha_close = (self.data['Open'] + self.data['High'] + self.data['Low'] + self.data['Close']) / 4.0
        ha_high = pd.Series(np.nan, index=self.data.index)
        ha_low = pd.Series(np.nan, index=self.data.index)

        # Special case for the first row (no previous Heikin-Ashi data)
        ha_open.iloc[0] = (self.data['Open'].iloc[0] + self.data['Close'].iloc[0]) / 2
        ha_low.iloc[0] = self.data['Low'].iloc[0]
        ha_high.iloc[0] = self.data['High'].iloc[0]

        # Calculate Heikin-Ashi elements for subsequent rows
        for i in range(1, len(self.data)):
            prev_ha_close = ha_close.iloc[i-1]
            prev_ha_open = ha_open.iloc[i-1]
            ha_open.iloc[i] = (prev_ha_open + prev_ha_close) / 2
            ha_high.iloc[i] = max(ha_open.iloc[i], ha_close.iloc[i], self.data['High'].iloc[i])
            ha_low.iloc[i] = min(ha_open.iloc[i], ha_close.iloc[i], self.data['Low'].iloc[i])

        self.data["Heikin Ashi - Open"] = ha_open
        self.data["Heikin Ashi - High"] = ha_high
        self.data["Heikin Ashi - Low"] = ha_low
        self.data["Heikin Ashi - Close"] = ha_close
        
        return self.data
    
    def build_auxillary_signal_data(self):
        # Calculate supporting values
        self.data["Heikin Ashi - T Change"] = self.data["Heikin Ashi - Close"] - self.data["Heikin Ashi - Open"]
        self.data['Heikin Ashi - T-1 Change'] = self.data["Heikin Ashi - T Change"].shift(1).fillna(0)
        self.data['Heikin Ashi - T-2 Change'] = self.data["Heikin Ashi - T Change"].shift(2).fillna(0)
        self.data['Heikin Ashi - T-3 Change'] = self.data["Heikin Ashi - T Change"].shift(3).fillna(0)
        self.data["Heikin Ashi - T Change - Positive"] = self.data["Heikin Ashi - T Change"] > 0
        self.data['Heikin Ashi - T-1 Change - Positive'] = self.data['Heikin Ashi - T-1 Change'] > 0
        self.data['Heikin Ashi - T-2 Change - Negative'] = self.data['Heikin Ashi - T-2 Change'] <= 0
        self.data['Heikin Ashi - T-3 Change - Negative'] = self.data['Heikin Ashi - T-3 Change'] <= 0

        self.data['Heikin Ashi - Buy Signal'] = self.data["Heikin Ashi - T Change - Positive"] & self.data['Heikin Ashi - T-1 Change - Positive'] & self.data['Heikin Ashi - T-2 Change - Negative'] & self.data['Heikin Ashi - T-3 Change - Negative']

        self.data["ENTRY_PRICE_AT_HIGH"] = self.data["High"].shift(-1).fillna(0)
        self.data["ENTRY_PRICE_AT_OPEN"] = self.data["Open"].shift(-1).fillna(0)

        self.data["2ND CANDLE EXIT PRICE"] = self.data["Close"].shift(-2).fillna(0)
        self.data["3RD CANDLE EXIT PRICE"] = self.data["Close"].shift(-3).fillna(0)
        self.data["4TH CANDLE EXIT PRICE"] = self.data["Close"].shift(-4).fillna(0)
        self.data["5TH CANDLE EXIT PRICE"] = self.data["Close"].shift(-5).fillna(0)
        self.data["6TH CANDLE EXIT PRICE"] = self.data["Close"].shift(-6).fillna(0)
        self.data["7TH CANDLE EXIT PRICE"] = self.data["Close"].shift(-7).fillna(0)
        self.data["8TH CANDLE EXIT PRICE"] = self.data["Close"].shift(-8).fillna(0)
        self.data["9TH CANDLE EXIT PRICE"] = self.data["Close"].shift(-9).fillna(0)
        self.data["10TH CANDLE EXIT PRICE"] = self.data["Close"].shift(-10).fillna(0)

        self.data["RESULT_OPEN_2ND"] = self.data["2ND CANDLE EXIT PRICE"] - self.data["ENTRY_PRICE_AT_OPEN"]
        self.data["RESULT_OPEN_3ND"] = self.data["3RD CANDLE EXIT PRICE"] - self.data["ENTRY_PRICE_AT_OPEN"]
        self.data["RESULT_OPEN_4ND"] = self.data["4TH CANDLE EXIT PRICE"] - self.data["ENTRY_PRICE_AT_OPEN"]
        self.data["RESULT_OPEN_5ND"] = self.data["5TH CANDLE EXIT PRICE"] - self.data["ENTRY_PRICE_AT_OPEN"]
        self.data["RESULT_OPEN_6ND"] = self.data["6TH CANDLE EXIT PRICE"] - self.data["ENTRY_PRICE_AT_OPEN"]
        self.data["RESULT_OPEN_7ND"] = self.data["7TH CANDLE EXIT PRICE"] - self.data["ENTRY_PRICE_AT_OPEN"]
        self.data["RESULT_OPEN_8ND"] = self.data["8TH CANDLE EXIT PRICE"] - self.data["ENTRY_PRICE_AT_OPEN"]
        self.data["RESULT_OPEN_9ND"] = self.data["9TH CANDLE EXIT PRICE"] - self.data["ENTRY_PRICE_AT_OPEN"]
        self.data["RESULT_OPEN_10ND"] = self.data["10TH CANDLE EXIT PRICE"] - self.data["ENTRY_PRICE_AT_OPEN"]

        return self.data
    
    def build_indicator_data(self):
        sti = ta.supertrend(self.data['Heikin Ashi - High'], self.data['Heikin Ashi - Low'], self.data['Heikin Ashi - Close'], length=10, multiplier=2)
        sti.columns = ["Supertrend","Supertrend Direction","Supertrend Lowerband","Supertrend Upperband"]
        self.data = self.data.join(sti)
        return self.data
    
today = date.today()
today_date_string = today.strftime("%Y-%m-%d")
o = Omega(instrument=INSTRUMENT_TOKEN)
o.fetch_intraday_data()
o.fetch_historical_data(to_date=today_date_string)
o.assemble_data()
o.build_heikin_ashi_data()
o.build_indicator_data()
o.build_auxillary_signal_data()
signals = o.data[o.data["Heikin Ashi - Buy Signal"] == True]
signals = signals[signals["Supertrend Direction"] < 0].tail(30)

result_columns = [
            "Timestamp",
            "RESULT_OPEN_2ND",
            "RESULT_OPEN_3ND",
            "RESULT_OPEN_4ND",
            "RESULT_OPEN_5ND",
            "RESULT_OPEN_6ND",
            "RESULT_OPEN_7ND",
            "RESULT_OPEN_8ND",
            "RESULT_OPEN_9ND",
            "RESULT_OPEN_10ND"
        ]

for column in result_columns[1:]:
    print(f"--- Column --- {column}")
    print(signals[column].describe())
    print(f"Sum : {signals[column].sum()}")
    print(f"Median : {signals[column].median()}")
    print("----------------\n")

print(
    signals[
        result_columns
    ].tail(50)
)
