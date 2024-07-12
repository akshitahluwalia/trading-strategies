import time
import datetime
import argparse
import pandas as pd
import numpy as np
import upstox_client
from pytz import timezone
import pandas_ta as ta
from datetime import date
from upstox_client.rest import ApiException

class Accumulator(object):
    def __init__(
            self,
            access_token,
            instrument,
            number_of_lots,
            lot_size
    ):
        self.api_version = "v2"
        self.access_token = access_token
        self.instrument = instrument
        self.number_of_lots = number_of_lots
        self.quantity = number_of_lots * lot_size
        self.lot_size = lot_size
        self.historical_data = None
        self.intraday_data = None
        self.data = None
        self.position_active = False
        self.position_active_since_ticks = 0
    
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
        return self.data
    
    def build_indicator_data(self):
        sti = ta.supertrend(self.data['Heikin Ashi - High'], self.data['Heikin Ashi - Low'], self.data['Heikin Ashi - Close'], length=10, multiplier=2)
        sti.columns = ["Supertrend","Supertrend Direction","Supertrend Lowerband","Supertrend Upperband"]
        self.data = self.data.join(sti)
        return self.data
    
    def defer_execution(self):
        t = datetime.datetime.now(datetime.UTC)
        sleeptime = 60 - (t.second + t.microsecond/1000000.0) + 10
        time.sleep(sleeptime)

    def print_output(self, message):
        tz = timezone('Asia/Kolkata')
        print(f">>>> {datetime.datetime.now(tz)} >>>> {message}")

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
            self.print_output(f"Market order {order_id} placed successfully :: {transaction_type} :: {quantity}")
            return order_id
        except ApiException as e:
            self.print_output("Encountered error while placing Market order :: %s\n" % e)

    def fetch_open_orders_for_instrument(self, instrument):
        order_book = self.get_orderbook_from_broker()
        filtered_orders = []
        for order in order_book:
             if(order.instrument_token == instrument and order.status != "rejected" and order.status != "complete" and order.status != "cancelled" ):
                 filtered_orders.append(order)
        return filtered_orders
    
    def cancel_orders_for_instrument(self, instrument):
        configuration = upstox_client.Configuration()
        configuration.access_token = self.access_token
        order_book = self.fetch_open_orders_for_instrument(instrument)
        for order in order_book:
            if order.instrument_token == instrument:
                try:
                    api_instance = upstox_client.OrderApi(upstox_client.ApiClient(configuration))
                    api_response = api_instance.cancel_order(order.order_id, self.api_version)
                    self.print_output(f"Cancelling Orders {order.order_id} is successful")
                except Exception as e:
                    self.print_output(f"Encountered exception while cancelling order {order.order_id}")
    
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
            self.print_output(f"Stop loss order {order_id} placed successfully :: {transaction_type} :: {quantity}")
            return order_id
        except ApiException as e:
            print("Encountered exception while placing stop loss order :: %s\n" % e)

    def round_nearest(self, x, a):
        return round(x / a) * a
    
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
            print("Exception when calling OrderApi->get_order_book: %s\n" % e)
    
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
        
        if(self.position_active == True):
            current_candle_change = last_candle["Heikin Ashi - T Change"]
            last_candle_change = last_candle['Heikin Ashi - T-1 Change']
            if(current_candle_change <= 0.0 and last_candle_change <=0):
                self.print_output("Exit condition detected hence exiting position")
                self.cancel_orders_for_instrument(self.instrument)
                self.place_market_order(
                        instrument= self.instrument,
                        quantity= self.quantity,
                        transaction_type= "SELL"
                    )
                self.position_active =  False
                self.position_active_since_ticks = 0
            else:
                self.print_output("Maintaining positions")
                self.position_active_since_ticks += 1
        else:
            # No position is active
            buy_signal = last_candle["Heikin Ashi - Buy Signal"]
            if(buy_signal):
                self.print_output("Buy Signal is generated and activated by supertrend")
                self.place_market_order(
                    instrument= self.instrument,
                    quantity= self.quantity,
                    transaction_type= "BUY"
                )
                self.position_active = True
                self.position_active_since_ticks = 0
                # Place stop loss order
                stop_loss_price = self.round_nearest(last_candle["Close"] - (0.15 * last_candle["Close"]),0.05)
                stop_loss_trigger_price = stop_loss_price + 0.05
                self.place_stop_loss_order(
                    instrument_key= self.instrument, 
                    quantity= self.quantity, 
                    price= stop_loss_price, 
                    trigger_price= stop_loss_trigger_price,                         
                    transaction_type= "SELL"
                )

                # # Supertrend Filter
                # if(last_candle["Supertrend Direction"] <= 0.0):
                #     self.print_output("Buy Signal is generated and activated by supertrend")
                #     self.place_market_order(
                #         instrument= self.instrument,
                #         quantity= self.quantity,
                #         transaction_type= "BUY"
                #     )
                #     self.position_active = True
                #     self.position_active_since_ticks = 0
                #     # Place stop loss order
                #     stop_loss_price = self.round_nearest(last_candle["Close"] - (0.15 * last_candle["Close"]),0.05)
                #     stop_loss_trigger_price = stop_loss_price + 0.05
                #     self.place_stop_loss_order(
                #         instrument_key= self.instrument, 
                #         quantity= self.quantity, 
                #         price= stop_loss_price, 
                #         trigger_price= stop_loss_trigger_price, 
                #         transaction_type= "SELL"
                #     )
                # else:
                #     self.print_output("Buy Signal is generated but filtered out by Supertrend")
            else:
                self.print_output("Buy Signal is not generated")

def print_output(message):
    tz = timezone('Asia/Kolkata')
    print(f">>>> {datetime.datetime.now(tz)} >>>> {message}")

def main():
    parser = argparse.ArgumentParser(description='Optional app description')
    parser.add_argument('--accesstoken', type= str, help= 'Upstox Access Token')
    parser.add_argument('--instrument', type= str, help= 'Upstox Instrument Identifier')
    parser.add_argument('--numberoflots', type= int, help= 'Upstox Instrument Identifier')
    parser.add_argument('--lotsize', type= int, help= 'Upstox Instrument Identifier')

    print_output("Parsing Arguments")
    args = parser.parse_args()

    accumulator =  Accumulator(
        access_token= args.accesstoken,
        instrument= args.instrument,
        number_of_lots= args.numberoflots,
        lot_size= args.lotsize
    )
    
    print_output("Initialization is successful and now spawning execution loop")
    run_next = True
    while run_next:
        print_output("Accumulator is running >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
        accumulator.run()
        print_output("Accumulator is deferred for execution >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
        accumulator.defer_execution()

main()
