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
    
    def defer_execution(self):
        # 1,5
        # now = time.time()
        # next_slot = int(now // 60 + minutes) * 60
        # sleep_duration = int(next_slot - now)
        # time.sleep(sleep_duration + buffer)
        t = datetime.datetime.utcnow()
        sleeptime = 60 - (t.second + t.microsecond/1000000.0) + 10
        time.sleep(sleeptime)

    def sync_broker_state(self):
        self.positions = self.broker_account.get_positions_from_broker()
        self.order_book = self.broker_account.get_orderbook_from_broker()
    
    def round_nearest(self, x, a):
        return round(x / a) * a

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
        self.print_output("Last Candle Data")
        for k, v in last_candle.items():
            self.print_output(f"{k} :: {v}")

        if last_candle["Supertrend Direction"] == 1.0 :
            # Supertrend Buy Zone
            # Cases to cover : 
            # - If there is an existing position then exit it and cancel the stp loss order if not filled
            # - Place Stop Loss Entry orders for next trade only after the first one is met
            # - Output the status of the stop loss order

            # Exiting standing short options positions
            len_standing_position, standing_position = self.broker_account.get_positions_for_instrument(self.instrument)
            if len_standing_position > 0 and standing_position[0].quantity < 0 :
                self.broker_account.place_market_exit_order(self.instrument, abs(standing_position[0].quantity))
                self.print_output(f"Exited positions for {self.instrument}")

            # Cancelling all open orders
            self.print_output(f"Cancelling current orders")
            self.broker_account.cancel_orders_for_instrument(self.instrument)

            # Place entry order for next price fall
            self.print_output(f"Placing fresh entry order at {self.round_nearest(last_candle["Supertrend"],0.05) - 0.05}")
            self.cached_entry_order = self.broker_account.place_entry_order(
                instrument_key= self.instrument,
                quantity= self.lot_size * self.number_of_lots,
                price= self.round_nearest(last_candle["Supertrend"],0.05) - 0.05,
                trigger_price= self.round_nearest(last_candle["Supertrend"],0.05)
            )

        elif last_candle["Supertrend Direction"] == -1.0:
            # Supertrend Short Zone
            # Cases to cover :
            # - Check if the entry order is fulfilled and/or the position is active
            # - If yes, Place stop loss order at 1.5 times the difference between supertrend and price value 
            # - Place target order at 3 times the loss

            # Check if the position is active
            len_standing_position, standing_position = self.broker_account.get_positions_for_instrument(self.instrument)
            if len_standing_position <= 0:
                self.print_output("No standing position found in the selling zone")
                self.print_output("Already in the selling zone so no active trade")
            else:
                self.broker_account.cancel_orders_for_instrument(self.instrument)
                buffer_percentage = 0.02
                stop_loss_price = self.round_nearest(last_candle["Supertrend"] + (buffer_percentage * last_candle["Supertrend"]),0.05) 
                self.print_output(f"Placing stop loss order at {stop_loss_price}")
                self.broker_account.place_stop_loss_order(
                    instrument_key= self.instrument,
                    quantity= self.lot_size * self.number_of_lots,
                    price= stop_loss_price + 0.05,
                    trigger_price= stop_loss_price
                )

        else:
            self.print_output("Invalid Supertrend Value")