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
from strategy import Strategy

# Setting-up Command-line Parameters
parser = argparse.ArgumentParser(description='Optional app description')
parser.add_argument('--accesstoken', type= str, help= 'Upstox Access Token')
parser.add_argument('--instrument', type= str, help= 'Upstox Instrument Identifier')

def clear(): 
    if name == 'nt': 
        x = system('cls') 
    else: 
        x = system('clear') 

def main():
    pass

main()