import time
import pandas as pd

class Strategy(object):

    def __init__(self):
        self.position_active = False
        self.fresh_run = False
        self.price_data = None
        self.whitelisted_trade_execution_timeslots = None
        self.blacklisted_execution_timeslots = None
        pass

    def whitelisted_period(self):
        pass

    def blacklisted_period(self):
        pass

    def filter_price_data(self):
        pass
    
    def fetch_state_from_redis(self):
        pass
    
    def push_state_to_redis(self):
        pass

    def assemble_data(self):
        pass

    def fetch_intraday_data(self, interval= "1minute"):
        api_instance = upstox_client.HistoryApi()
        api_response = api_instance.get_intra_day_candle_data(INSTRUMENT_KEY, "1minute", API_VERSION)
        response_candles = api_response.data.candles
        columns = ["Timestamp","Open","High","Low","Close","Volume","Open Interest"]
        df = pd.DataFrame(data=candles, columns=columns)
        df["Timestamp"] = pd.to_datetime(df["Timestamp"])
        df = df.sort_values(by='Timestamp')
    
    def fetch_historical_data(self, interval= "1minute"):
        pass

    def indicator_data(self):
        pass

    def build_auxillary_signal_data(self):
        pass

    def build_heikin_ashi(self):
        pass
    
    def defer_execution(self, minutes=1, buffer=5):
        now = time.time()
        next_slot = int(now // 60 + minutes) * 60
        sleep_duration = int(next_slot - now)
        time.sleep(sleep_duration + buffer)

    def print_status(self):
        pass

    def setup_redis_connection(self):
        pass

    def sync_from_redis(self):
        pass

    def update_redis_data(self):
        pass

    def run(self):
        pass