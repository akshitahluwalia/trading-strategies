import os
import sys
import time
import logging
import datetime
import argparse
import pandas as pd
import numpy as np
import upstox_client
import pandas_ta as ta
from datetime import date
from pytz import timezone
from upstox_client.rest import ApiException

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
        self.lots = lots
        self.option = option
        self.underlying = underlying
        self.instrument_master_path = instrument_master_path
        self.logfile_name = None
        self.logfile_path = None
        self.instruments_master = None
        self.expiry = expiry
        self.options_master = None

    def parse_instruments(self):
        data = pd.read_csv(self.instrument_master_path)
        self.instruments_master = data
        self.output(f"Instrument master parsing successful :: {self.instruments_master.shape}")
        return self.instruments_master
    
    def build_options_master(self):
        options_master = self.instruments_master[
            (self.instruments_master['tradingsymbol'].str.contains(self.underlying.upper()))
            & (self.instruments_master['expiry'] == str(self.expiry))
        ]
        self.options_master = options_master
        self.output(f"Options master parsing successful :: {self.options_master.shape}")
        return options_master
    
    def fetch_strike_option(self, strike):
        option = self.options_master[
            (self.options_master['strike'] == strike) & 
            (self.options_master['option_type'] == self.option)
        ].iloc[0]
        self.output(f"Selected Option :: {option.instrument_key} :: {option.strike} :: {option.option_type} :: {option.tradingsymbol}", "CRITICAL")

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

    def run(self):
        self.fetch_strike_option(52500)

    def defer_execution(self, buffer= 0):
        now = time.time()
        seconds = now % 60
        sleep_time = 60 - seconds + buffer
        self.output("Execution deferred")
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
        auto_accumulator.run()
        auto_accumulator.defer_execution(buffer=10)

main()