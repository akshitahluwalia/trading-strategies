import sys
import time
import datetime
import argparse
import numpy as np
import pandas as pd
import upstox_client
import pandas_ta as ta
from os import system, name
from upstox_client.rest import ApiException
import datetime
from pytz import timezone
from strategy import Strategy
from broker_account import BrokerAccount


def print_output(message):
    tz = timezone('Asia/Kolkata')
    print(f">>>> {datetime.datetime.now(tz)} >>>> {message}")

def main():
    # Setting-up Command-line Parameters
    parser = argparse.ArgumentParser(description='Optional app description')
    parser.add_argument('--accesstoken', type= str, help= 'Upstox Access Token')
    parser.add_argument('--instrument', type= str, help= 'Upstox Instrument Identifier')
    parser.add_argument('--numberoflots', type= int, help= 'Upstox Instrument Identifier')
    parser.add_argument('--lotsize', type= int, help= 'Upstox Instrument Identifier')
    
    print_output("Parsing Arguments")
    args = parser.parse_args()

    print_output("Creating Broker Instance")
    broker_account = BrokerAccount(
        access_token= args.accesstoken,
        api_version= "v2"
    )

    print_output("Creating Strategy Instance")
    strategy = Strategy(
        instrument= args.instrument,
        broker_account= broker_account,
        number_of_lots= args.numberoflots,
        lot_size= args.lotsize
    )

    print_output("Initialization is successful and now spawning execution loop")
    run_next = True
    while run_next:
        print_output("Strategy is executed")
        strategy.run()
        print_output("Strategy is deferred for execution")
        strategy.defer_execution()

# Run main function 
main()