import time
import redis
import json
import numpy as np
import pandas as pd
import upstox_client
import pandas_ta as ta
import datetime
from upstox_client.rest import ApiException
from broker_account import BrokerAccount
from datetime import date
from pytz import timezone


class Strategy(object):

    def __init__(self, instrument, broker_account, number_of_lots, lot_size):
        self.api_version = "v2"
        self.instrument = instrument
        self.number_of_lots = number_of_lots
        self.lot_size = lot_size
        self.positions = None
        self.order_book = None
        self.open_entry_orders = None
        self.open_exit_orders = None
        self.fresh_run = False
        self.price_data = None
        self.whitelisted_trade_execution_timeslots = None
        self.blacklisted_execution_timeslots = None
        self.data = None
        self.historical_data  = None
        self.intraday_data  = None
        self.broker_account = broker_account
        self.cached_entry_order = None
        self.cached_exit_order = None

    def write_to_redis(self, key, value):
        try:
            self.redis_connection.set(key, json.dumps(value))
        except redis.RedisError as e:
            print(f"Redis error: {e}")

    def read_from_redis(self, key):
        try:
            retrieved_data = json.loads(self.redis_connection.get(key))
            return retrieved_data
        except redis.RedisError as e:
            print(f"Redis error: {e}")
            return None
        
    def filter_data(self, start_datetime, end_datetime):
        self.data = self.data.query(f"Timestamp > '{start_datetime}' and Timestamp < '{end_datetime}'")
        return self.data
    
    def print_output(self, message):
        tz = timezone('Asia/Kolkata')
        print(f">>>> {datetime.datetime.now(tz)} >>>> {message}")

    def whitelisted_period(self):
        pass

    def blacklisted_period(self):
        pass

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

    def build_indicator_data(self):
        sti = ta.supertrend(self.data['Heikin Ashi - High'], self.data['Heikin Ashi - Low'], self.data['Heikin Ashi - Close'], length=10, multiplier=2)
        sti.columns = ["Supertrend","Supertrend Direction","Supertrend Lowerband","Supertrend Upperband"]
        self.data = self.data.join(sti)
        return self.data

    def build_auxillary_signal_data(self):
        # Calculate supporting values
        self.data["Heikin Ashi - Change"] = self.data["Heikin Ashi - Close"] - self.data["Heikin Ashi - Open"]
        self.data['Heikin Ashi - Previous Change'] = self.data["Heikin Ashi - Change"].shift(1).fillna(0)
        self.data['Heikin Ashi - Next Change'] = self.data["Heikin Ashi - Change"].shift(-1).fillna(0)
        self.data["Price Change"] = self.data["Close"] - self.data["Open"]
        self.data["Price Change - Current Close to Next Close"] = self.data["Close"] - self.data["Close"].shift(-1)
        self.data['Heikin Ashi - Direction Change'] = (self.data["Heikin Ashi - Change"] * self.data['Heikin Ashi - Previous Change']) < 0
        # self.data['Supertrend - Direction Change'] = (self.data["Heikin Ashi - Change"] * self.data['Heikin Ashi - Previous Change']) < 0
        return self.data

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
    
    def defer_execution(self, minutes=1, buffer=5):
        now = time.time()
        next_slot = int(now // 60 + minutes) * 60
        sleep_duration = int(next_slot - now)
        time.sleep(sleep_duration + buffer)

    def sync_broker_state(self):
        self.positions = self.broker_account.get_positions_from_broker()
        self.order_book = self.broker_account.get_orderbook_from_broker()

    def run(self):
        today = date.today()
        today_date_string = today.strftime("%Y-%m-%d")
        if self.historical_data is None:
            self.fetch_historical_data(to_date=today_date_string)
        self.fetch_intraday_data()
        self.assemble_data()
        self.build_heikin_ashi_data()
        self.build_indicator_data()
        self.build_auxillary_signal_data()
        last_candle_df = self.data.tail(1)
        last_candle = last_candle_df.iloc[0].to_dict()
        self.sync_broker_state()
        print(last_candle)

        if last_candle["Supertrend Direction"] == -1.0 :
            # Supertrend Short Zone
            pass
        elif last_candle["Supertrend Direction"] == -1.0:
            # Supertrend Short Zone
            pass