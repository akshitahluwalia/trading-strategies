import os
import sys
import time
import logging
import datetime
import argparse
import traceback
import pandas as pd
import numpy as np
import upstox_client
import pandas_ta as ta
from datetime import date
from pytz import timezone
from upstox_client.rest import ApiException
from decimal import Decimal

class AutoAccumulator(object):
    def __init__(
            self,
            access_token,
            lots,
            option,
            underlying,
            instrument_master_path,
            expiry
    ):
        self.access_token = access_token
        self.lots = int(lots)
        self.option = option
        self.underlying = underlying
        self.instrument_master_path = instrument_master_path
        self.logfile_name = None
        self.logfile_path = None
        self.instruments_master = None
        self.expiry = expiry
        self.options_master = None
        self.last_traded_option = None
        self.selected_option = None
        self.api_version = "v2"
        self.positions = None # Overall account level positions
        self.position = None # Position tracker for last selected instrument
        self.is_position_active = False # Position tracker for last selected instrument
        self.order_book = None
        self.ticks_since_underlying_refresh = 0
        self.underlying_price = None
        self.intraday_data = None
        self.historical_data = None
        self.data = None

    def parse_instruments(self):
        data = pd.read_csv(self.instrument_master_path)
        self.instruments_master = data
        self.output(f"Instrument master parsing successful :: {self.instruments_master.shape}")
        return self.instruments_master
    
    def fetch_position_from_broker(self, instrument_token):
        positions = self.fetch_positions_from_broker()
        for position in positions:
            if (position.instrument_token == instrument_token):
                if int(position.quantity) == 0:
                    return position, False
                else:
                    return position, True
        # Return None if instrument token provided not in positions
        return None, False
        
    def fetch_positions_from_broker(self):
        configuration = upstox_client.Configuration()
        configuration.access_token = self.access_token
        api_instance = upstox_client.PortfolioApi(upstox_client.ApiClient(configuration))
        try:
            api_response = api_instance.get_positions(self.api_version)
            positions = api_response.data
            self.positions = positions
            return positions
        except ApiException as e:
            self.output(f"Exception occoured when fetching position from broker :: e")
            return e
        
    def get_orderbook_from_broker(self):
        configuration = upstox_client.Configuration()
        configuration.access_token = self.access_token
        api_instance = upstox_client.OrderApi(upstox_client.ApiClient(configuration))
        try:
            # Get order book
            api_response = api_instance.get_order_book(self.api_version)
            order_book = api_response.data
            self.order_book = order_book
            return order_book
        except ApiException as e:
            self.output(f"Encountered exception while fetching orderbook :: {e}")
        
    def cancel_order(self, order_id):
        configuration = upstox_client.Configuration()
        configuration.access_token = self.access_token
        try:
            api_instance = upstox_client.OrderApi(upstox_client.ApiClient(configuration))
            api_response = api_instance.cancel_order(order_id, self.api_version)
            self.output(f"Cancelling Order {order_id} is successful")
        except ApiException as e:
            self.output(f"Exception while cancelling order :: {order_id} - {e}")
    
    def build_options_master(self):
        if self.underlying == "NSE_INDEX|Nifty Bank":
            sub_string = "BANKNIFTY"
        elif self.underlying == "NSE_INDEX|Nifty 50":
            sub_string = "NIFTY"
        options_master = self.instruments_master[
            (self.instruments_master['tradingsymbol'].str.contains(sub_string)) & 
            (self.instruments_master['expiry'] == str(self.expiry))
        ]
        self.options_master = options_master
        self.output(f"Options master parsing successful :: {self.options_master.shape}")
        return options_master
    
    def select_option(self, strike):
        option = self.options_master[
            (self.options_master['strike'] == strike) & 
            (self.options_master['option_type'] == self.option)
        ].iloc[0]
        return option

    def setup_logging(self):
        logs_dir = "logs"
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)
        self.logfile_name = datetime.datetime.now().strftime(f'ACCUMULATOR-{self.underlying}-{self.option}-%d%m%Y@%H_%M').upper() + ".log"
        self.logfile_path = os.path.join(logs_dir, self.logfile_name)
        targets = logging.StreamHandler(sys.stdout), logging.FileHandler(self.logfile_path)
        logging.basicConfig(format='%(message)s', level=logging.INFO, handlers=targets)
        logging.basicConfig(format='%(message)s', level=logging.ERROR, handlers=targets)
        logging.basicConfig(format='%(message)s', level=logging.CRITICAL, handlers=targets)
        self.output("Logging setup successful")

    def output(self, message, type= "INFO"):
        tz = timezone('Asia/Kolkata')
        formatted_message = f">>> {datetime.datetime.now(tz)} >>> {message}"
        if type.upper() == "ERROR":
            logging.error(formatted_message)
        elif type.upper() == "CRITICAL":
            logging.critical(formatted_message)
        else:
            logging.info(formatted_message)

    def round_nearest(self, x, a):
        # TODO: ensure precision
        return round(x / a) * a
    
    def fetch_instrument_quote(self, instrument_token):
        configuration = upstox_client.Configuration()
        configuration.access_token = self.access_token
        api_instance = upstox_client.MarketQuoteApi(upstox_client.ApiClient(configuration))
        try:
            api_response = api_instance.ltp(instrument_token, self.api_version)
            return api_response.data
        except ApiException as e:
            self.output(f"Encountered exception while fetching MarketQuoteApi -> ltp: {e}")
    
    def fetch_intraday_data(self, interval= "1minute"):
        try:
            api_instance = upstox_client.HistoryApi()
            api_response = api_instance.get_intra_day_candle_data(self.selected_option.instrument_key, interval, self.api_version)
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
            api_response = api_instance.get_historical_candle_data(self.selected_option.instrument_key, interval, to_date, self.api_version)
            candles = api_response.data.candles
            columns = ["Timestamp","Open","High","Low","Close","Volume","Open Interest"]
            self.historical_data = pd.DataFrame(data=candles, columns=columns)
            self.historical_data["Timestamp"] = pd.to_datetime(self.historical_data["Timestamp"])
            self.historical_data = self.historical_data.sort_values(by='Timestamp')
            return self.historical_data
        except ApiException as e:
            print("Exception when calling HistoryApi->get_historical_candle_data: %s\n" % e)

    def assemble_data(self):
        self.data = pd.concat([self.historical_data, self.intraday_data])
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

        self.data["Heikin Ashi - Open"] = ha_open.apply(lambda x: self.round_nearest(x,0.05))
        self.data["Heikin Ashi - High"] = ha_high
        self.data["Heikin Ashi - Low"] = ha_low
        self.data["Heikin Ashi - Close"] = ha_close.apply(lambda x: self.round_nearest(x,0.05))
        return self.data
    
    def build_auxillary_signal_data(self):
        # Calculate supporting values
        price_change_heiken_ashi = (self.data["Heikin Ashi - Close"] - self.data["Heikin Ashi - Open"]).apply(lambda x: self.round_nearest(x,0.05))
        self.data["Heikin Ashi - T Change"] = price_change_heiken_ashi
        self.data['Heikin Ashi - T-1 Change'] = price_change_heiken_ashi.shift(1).fillna(0)
        self.data['Heikin Ashi - T-2 Change'] = price_change_heiken_ashi.shift(2).fillna(0)
        self.data['Heikin Ashi - T-3 Change'] = price_change_heiken_ashi.shift(3).fillna(0)
        self.data["Heikin Ashi - T Change - Positive"] = self.data["Heikin Ashi - T Change"] >= 0.0
        self.data['Heikin Ashi - T-1 Change - Positive'] = self.data['Heikin Ashi - T-1 Change'] >= 0.0
        self.data['Heikin Ashi - T-2 Change - Negative'] = self.data['Heikin Ashi - T-2 Change'] < 0.0
        self.data['Heikin Ashi - T-3 Change - Negative'] = self.data['Heikin Ashi - T-3 Change'] < 0.0
        self.data['Heikin Ashi - Buy Signal'] = self.data["Heikin Ashi - T Change - Positive"] & self.data['Heikin Ashi - T-1 Change - Positive'] & self.data['Heikin Ashi - T-2 Change - Negative'] & self.data['Heikin Ashi - T-3 Change - Negative']
        return self.data
    
    def build_indicator_data(self,supertrend_period= 10,supertrend_multiplier= 2):
        sti = ta.supertrend(self.data['Heikin Ashi - High'], self.data['Heikin Ashi - Low'], self.data['Heikin Ashi - Close'], length= supertrend_period, multiplier=supertrend_multiplier)
        sti.columns = ["Supertrend","Supertrend Direction","Supertrend Lowerband","Supertrend Upperband"]
        self.data["Supertrend"] = sti["Supertrend"]
        self.data["Supertrend Direction"] = sti["Supertrend Direction"]
        self.data["Supertrend Lowerband"] = sti["Supertrend Lowerband"]
        self.data["Supertrend Upperband"] = sti["Supertrend Upperband"]
        return self.data

    def cancel_orders_for_instrument(self, instrument):
        configuration = upstox_client.Configuration()
        configuration.access_token = self.access_token
        order_book = self.fetch_open_orders_for_instrument(instrument)
        for order in order_book:
            if order.instrument_token == instrument:
                try:
                    api_instance = upstox_client.OrderApi(upstox_client.ApiClient(configuration))
                    api_response = api_instance.cancel_order(order.order_id, self.api_version)
                    self.output(f"Cancelling Order :: {order.order_id} is {api_response.status.upper()}")
                except Exception as e:
                    self.output(f"Encountered exception while cancelling order {order.order_id}")

    def fetch_open_orders_for_instrument(self, instrument):
        order_book = self.get_orderbook_from_broker()
        filtered_orders = []
        for order in order_book:
             if(order.instrument_token == instrument and order.status != "rejected" and order.status != "complete" and order.status != "cancelled" ):
                 filtered_orders.append(order)
        return filtered_orders
    
    def place_stop_loss_order(self, instrument_key, quantity, price, trigger_price, transaction_type):
        configuration = upstox_client.Configuration()
        configuration.access_token = self.access_token
        api_instance = upstox_client.OrderApi(upstox_client.ApiClient(configuration))
        body = upstox_client.PlaceOrderRequest(
            quantity= quantity,
            product="I",
            validity="DAY",
            instrument_token= instrument_key,
            price= price,
            tag= f"ACCUMULATOR-STOP-LOSS-ORDER-{instrument_key}",
            order_type="SL",
            transaction_type= transaction_type,
            disclosed_quantity= 0,
            trigger_price= trigger_price,
            is_amo=False
        )

        try:
            api_response = api_instance.place_order(body, self.api_version)
            order_id = api_response.data.order_id
            self.output(f"Stop loss order {order_id} placed successfully :: {transaction_type} :: {quantity}")
            return order_id
        except ApiException as e:
            print("Encountered exception while placing stop loss order :: %s\n" % e)

    def place_market_order(self, instrument, quantity, transaction_type):
        configuration = upstox_client.Configuration()
        configuration.access_token = self.access_token
        api_instance = upstox_client.OrderApi(upstox_client.ApiClient(configuration))
        body = upstox_client.PlaceOrderRequest(
            quantity= quantity,
            product="I",
            validity="DAY",
            instrument_token= instrument,
            price= 0,
            tag= f"ACCUMULATOR-MARKET-ORDER-{instrument}",
            order_type="MARKET",
            transaction_type= transaction_type,
            disclosed_quantity= 0,
            trigger_price=0,
            is_amo=False
        )

        try:
            api_response = api_instance.place_order(body, self.api_version)
            order_id = api_response.data.order_id
            self.output(f"Market order {order_id} placed successfully :: {transaction_type} :: {quantity}")
            return order_id
        except ApiException as e:
            self.output("Encountered error while placing Market order :: %s\n" % e)

    def run(self):
        run_start_time = datetime.datetime.now(timezone("Asia/Kolkata"))
        self.output(f"Run started at {run_start_time}")

        if self.ticks_since_underlying_refresh >= 10 or self.underlying_price is None:
            # Refresh the last traded price of the underlying every 10 mins
            underlying_quote =  self.fetch_instrument_quote(self.underlying)
            root_key = list(underlying_quote.keys())[0]
            underlying_quote_ltp = underlying_quote[root_key].last_price
            self.underlying_price = underlying_quote_ltp
            self.output(f"Updated {self.underlying} price :: {underlying_quote_ltp} :: Turn :: {self.ticks_since_underlying_refresh}")
            self.ticks_since_underlying_refresh = 0
        else:
            self.ticks_since_underlying_refresh += 1
            self.output(f"{self.underlying} price considered for computation :: {self.underlying_price} :: Turn :: {self.ticks_since_underlying_refresh}")

        # Sync position state on every run
        if self.last_traded_option is not None or self.is_position_active is True:
            self.output(f"Fetching position state for last traded option :: {self.last_traded_option.tradingsymbol}")
            last_traded_option_position, is_last_traded_option_position_active = self.fetch_position_from_broker(self.last_traded_option.instrument_key)
            self.position = last_traded_option_position
            self.is_position_active = is_last_traded_option_position_active
            self.output(f"Position Status :: {self.last_traded_option.tradingsymbol} :: IsPositionActive :: {self.is_position_active}")
        
        if self.is_position_active == False:
            # Position :: Inactive, Select the option instrument based on underlying price
            nearest_strike = self.round_nearest(self.underlying_price,100)
            selected_option = self.select_option(nearest_strike)
            self.selected_option = selected_option
            self.output(f"Selected Option :: {selected_option.tradingsymbol} :: {selected_option.instrument_key} :: {selected_option.strike} :: {selected_option.option_type}")
        else:
            # Position :: Active
            self.output(f"Maintaining Previously Selected Option :: {self.selected_option.tradingsymbol} :: {self.selected_option.instrument_key} :: {self.selected_option.strike} :: {self.selected_option.option_type}")
        
        # Todays Date for hsitorical data
        today = date.today()
        today_date_string = today.strftime("%Y-%m-%d")
        self.output(f"Processing Price Data :: {self.selected_option.tradingsymbol} :: {self.selected_option.instrument_key} :: {self.selected_option.strike} :: {self.selected_option.option_type}")
        # Fetching Data for the selected option
        self.fetch_intraday_data()
        self.fetch_historical_data(to_date=today_date_string)
        self.assemble_data()
        self.build_heikin_ashi_data()
        self.build_indicator_data()
        self.build_auxillary_signal_data()

        last_candle_df = self.data.tail(1)
        last_candle = last_candle_df.iloc[0].to_dict()

        for k, v in last_candle.items():
            self.output(f"{k} :: {v}")

        delay = datetime.datetime.now() - datetime.datetime.fromtimestamp(last_candle["Timestamp"].timestamp())
        self.output(f"Last Candle Timestamp to Execution Time Delay :: {delay}")

        # Check Entry and Exit Conditions Based on the Position Status
        if self.is_position_active == False:
            # Position :: Inactive
            buy_signal = last_candle["Heikin Ashi - Buy Signal"]
            if buy_signal == True:
                self.output(f"****** Buy Signal Encountered | Placing Orders ******")
                self.place_market_order(
                    instrument= self.selected_option.instrument_key,
                    quantity= int(self.lots) * int(self.selected_option["lot_size"]),
                    transaction_type= "BUY"
                )
                stop_loss_price = self.round_nearest(last_candle["Close"] - (0.15 * last_candle["Close"]),0.05)
                stop_loss_trigger_price = stop_loss_price + 0.05
                self.place_stop_loss_order(
                    instrument_key= self.selected_option.instrument_key, 
                    quantity= int(self.lots) * int(self.selected_option["lot_size"]), 
                    price= stop_loss_price, 
                    trigger_price= stop_loss_trigger_price,                         
                    transaction_type= "SELL"
                )
                self.last_traded_option = self.selected_option
                time.sleep(10)
                self.position, self.is_position_active = self.fetch_position_from_broker(self.last_traded_option.instrument_key)
            else:
                self.output(f"Buy Signal is not yet encountered")
        else:
            # Position :: Active
            current_candle_change = last_candle["Heikin Ashi - T Change"]
            last_candle_change = last_candle["Heikin Ashi - T-1 Change"]
            if(current_candle_change <= 0.0 and last_candle_change <=0):
                self.output(f"****** Exit-condition encountered :: CurrentCandleNegative({current_candle_change < 0.0}) = {current_candle_change}  :: PreviousCandleNegative({last_candle_change < 0.0})  = {last_candle_change} ******")
                self.cancel_orders_for_instrument(self.selected_option.instrument_key)
                self.place_market_order(
                        instrument= self.selected_option.instrument_key,
                        quantity= int(self.lots) * int(self.selected_option["lot_size"]),
                        transaction_type= "SELL"
                    ) 
                self.data = None
                self.historical_data = None
                self.intraday_data = None
                self.position_active =  False
                self.last_traded_option = self.selected_option
                self.position, self.is_position_active = self.fetch_position_from_broker(self.last_traded_option.instrument_key)
                self.underlying_price = None
            else:
                self.output(f"Exit-condition is not yet encountered :: CurrentCandleNegative({current_candle_change < 0.0}) = {current_candle_change}  :: PreviousCandleNegative({last_candle_change < 0.0})  = {last_candle_change}")

        run_end_time = datetime.datetime.now(timezone("Asia/Kolkata"))
        self.output(f"Run ended at {run_end_time} taking {run_end_time - run_start_time} seconds for execution \n\n")

    def defer_execution(self, buffer= 0):
        now = time.time()
        seconds = now % 60
        sleep_time = 60 - seconds + buffer
        self.output(f"Deferred execution for {sleep_time} seconds.")
        time.sleep(sleep_time)

def main():
    # Setting-up logging to write to log-file and console both at the simultaneously
    parser = argparse.ArgumentParser(description='Optional app description')
    parser.add_argument('--token', type= str, help= 'Upstox Access Token')
    parser.add_argument('--lots', type= int, help= 'Number of lots to trade')
    parser.add_argument('--option', type= str, help= 'CALL or PUT')
    parser.add_argument('--underlying', type= str, help= 'Index Tracker')
    parser.add_argument('--instrumentmasterpath', type= str, help= 'Upstox Instrument Identifier')
    parser.add_argument('--expiry', type= str, help= 'Upstox Instrument Identifier')
    args = parser.parse_args()

    auto_accumulator = AutoAccumulator(
        access_token= args.token,
        lots= args.lots,
        option= args.option,
        underlying= args.underlying,
        instrument_master_path= args.instrumentmasterpath,
        expiry= args.expiry
    )
    auto_accumulator.setup_logging()
    auto_accumulator.parse_instruments()
    auto_accumulator.build_options_master()
    
    while True:
        try:
            auto_accumulator.run()
            auto_accumulator.defer_execution(buffer=15)
        except Exception as e:
            auto_accumulator.output(f"******** EXCEPTION ENCOUNTERED WHILE RUNNING  *******\n{e}")
            traceback.print_exc()
main()