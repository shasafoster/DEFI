#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jan  7 09:45:46 2022

# Objective: Demonstrate ability to use Web3 package, APIs and read Solidity smart contracts. 

@author: Shasa Foster
@email: shasa.foster@protonmail.com 
"""

#%%

import requests
import pprint
import json
import urllib.request

#%% Get cDAI info via API 

request_cToken = requests.get("https://api.compound.finance/api/v2/ctoken")
json_cToken = request_cToken.json()

#% Inspect cDAI
json_cDAI = [v for v in json_cToken['cToken'] if v['symbol'] == 'cDAI'][0]
pp = pprint.PrettyPrinter(indent=4)
#print('Compound API data for cDAI')
#pp.pprint(json_cDAI)

cash = int(float(json_cDAI['cash']['value']))
borrows = int(float(json_cDAI['total_borrows']['value']))
reserves = int(float(json_cDAI['reserves']['value']))
kink = float(json_cDAI['collateral_factor']['value']) * 1e18

#%% Set connection to my Infura 

from web3 import Web3
w3 = Web3(Web3.HTTPProvider('https://mainnet.infura.io/v3/ffe52b14430146c5ab56d02b9ee25ff7')) # My Infura

#%% Get ABI from Etherscan
# ABI is required for interacting with the interest rate model smart contract

address = w3.toChecksumAddress(json_cDAI['interest_rate_model_address']) # format required
api_url = 'https://api.etherscan.io/api?module=contract&action=getabi&address=' + address 

with urllib.request.urlopen(api_url) as url:
    json_response = json.loads(url.read().decode())
    json_data = json_response['result']
    
#%% Read interest rate model smart contract data

contract = w3.eth.contract(address = address, abi=json_data)

# Inspect the functions available
# The smart contract code is viewable on Etherscan
# Specifially for cDAI the URL is: https://etherscan.io/address/0xfb564da37b41b2f6b6edcc3e56fbf523bd9f2012#code

#print('\n')
#print('Functions of the interest rate model:')
#pp.pprint([f for f in dir(contract.functions) if '_' not in f]) 



#%% Verify understanding of smart contract functions

# Generic Constants
eth_mantissa = 1e18
epsilon = 1e-6
blocks_per_day = 6570.0 # (13.15 seconds per block)
days_per_year = 365.0

# Interest Rate Constants from: https://etherscan.io/address/0xfb564da37b41b2f6b6edcc3e56fbf523bd9f2012#events
baseRatePerBlock = 0
multiplierPerBlock = 23782343987
blocksPerYear = 2102400

#% Verify the utilization rate calculation
util = contract.functions.utilizationRate(cash,borrows,reserves).call()
util_calc = eth_mantissa * (borrows / (cash + borrows - reserves))
assert((util - util_calc) / util < 1e-12)

#% Verify the borrow rate (per block) calculation
borrow_rate = float(contract.functions.getBorrowRate(cash,borrows,reserves).call())
if util <= kink:
    borrow_rate_calc = util_calc * multiplierPerBlock / eth_mantissa + baseRatePerBlock
else:
    normal_rate = kink * multiplierPerBlock / 1e18 + baseRatePerBlock
    excess_util = util - kink
    borrow_rate_calc = excess_util * jumpMultiplierPerBlock / 1e18 + normal_rate

assert((borrow_rate - borrow_rate_calc) / borrow_rate < 1e-12)

#% Verify the borrow rate APY calculation
borrow_apy = float(json_cDAI['borrow_rate']['value']) 
borrow_apy_calc = ((((borrow_rate_calc / eth_mantissa * blocks_per_day + 1) ** days_per_year)) - 1) 
assert (borrow_apy - borrow_apy_calc) < epsilon

#%% Print results

print('\n')
print("Calculated borrow rate from smart contract function calls is: ", 100 * round(borrow_apy_calc,8), '%')
print("Borrow rate APY from Compound.Finance API is: ", 100 * round(borrow_apy,8), '%')
# This rate can be verified in the web app: https://app.compound.finance/







