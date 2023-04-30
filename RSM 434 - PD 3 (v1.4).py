# -*- coding: utf-8 -*-
"""
Created on Fri Oct 25 14:20:02 2019
in_a_dndMixin_drag
@author: trader53
"""

import requests
import time

s = requests.Session()
s.headers.update({'X-API-key': '6Y2YZJPO'})

def get_status():
    resp = s.get('http://localhost:9999/v1/case')
    if resp.ok:
        case = resp.json()
        return case['status']


def bid_ask(ticker):
    payload = {'ticker': ticker}
    resp = s.get('http://localhost:9999/v1/securities/book', params=payload)
    if resp.ok:
        book = resp.json()
        if (len(book['bids'])*len(book['asks']) > 0):
            return book['bids'][0]['price'], book['asks'][0]['price']


def bid_ask_size(ticker):
    payload = {'ticker': ticker}
    resp = s.get('http://localhost:9999/v1/securities/book', params=payload)
    if resp.ok:
        book = resp.json()
        return book['bids'][0]['quantity'] - book['bids'][0]['quantity_filled'], book['asks'][0]['quantity'] - book['asks'][0]['quantity_filled']


def current_position(ticker):
    payload = {'ticker': ticker}
    resp = s.get('http://localhost:9999/v1/securities', params=payload)
    if resp.ok:
        book = resp.json()
        return book[0]['position']


def open_orders(ticker):
    payload = {'ticker': ticker}
    resp = s.get('http://localhost:9999/v1/orders', params=payload)
    if resp.ok:
        orders = resp.json()
        buy_orders = [item for item in orders if item["action"] == "BUY"]
        sell_orders = [item for item in orders if item["action"] == "SELL"]
        return buy_orders, sell_orders


def get_news ():
    resp = s.get('http://localhost:9999/v1/news')
    if resp.ok:
        news = resp.json()
        return news


def get_book (ticker):
    payload = {'ticker':ticker}
    resp = s.get('http://localhost:9999/v1/securities/book', params=payload)
    if resp.ok:
        book = resp.json()
        return book


def is_received (order_id):
    return s.get('http://localhost:9999/v1/orders/' + str(order_id)).ok


def main():
    TRADING_LIMIT = 5000
    POSITION_LIMIT = 100000
    CONFIDENCE_LEVEL = 0.95
    
    GEM_estimate = {'min' : 20, 'max' : 30}
    UB_estimate = {'min' : 40, 'max' : 60}
    ETF_estimate = {'min' : 60, 'max' : 90}
    
    order_id = 0
    
    order_received = True
    GEM_news_received = False
    UB_news_received = False
    
    status = get_status()
    
    while status == 'ACTIVE':
        book = {'UB' : get_book('UB'), 'GEM' : get_book('GEM'), 'ETF' : get_book('ETF')}

        UB_position = current_position('UB')
        GEM_position = current_position('GEM')
        ETF_position = current_position('ETF')

        bid_price_UB = book['UB']['bids'][0]['price']
        ask_price_UB = book['UB']['asks'][0]['price']
        bid_price_GEM = book['GEM']['bids'][0]['price']
        ask_price_GEM = book['GEM']['asks'][0]['price']
        bid_price_ETF = book['ETF']['bids'][0]['price']
        ask_price_ETF = book['ETF']['asks'][0]['price']

        ask_quantity_UB_A = min (TRADING_LIMIT, POSITION_LIMIT - (UB_position + abs(GEM_position) + abs(ETF_position)))
        bid_quantity_UB_A = min (TRADING_LIMIT, POSITION_LIMIT - (- UB_position + abs(GEM_position) + abs(ETF_position)))
        ask_quantity_GEM_A = min (TRADING_LIMIT, POSITION_LIMIT - (abs(UB_position) + GEM_position + abs(ETF_position)))
        bid_quantity_GEM_A = min (TRADING_LIMIT, POSITION_LIMIT - (abs(UB_position) - GEM_position + abs(ETF_position)))
        ask_quantity_ETF_A = min (TRADING_LIMIT, POSITION_LIMIT - (abs(UB_position) + abs(GEM_position) + ETF_position))
        bid_quantity_ETF_A = min (TRADING_LIMIT, POSITION_LIMIT - (abs(UB_position) + abs(GEM_position) - ETF_position))

        ask_quantity_UB_B = min (TRADING_LIMIT, POSITION_LIMIT - UB_position)
        bid_quantity_UB_B = min (TRADING_LIMIT, POSITION_LIMIT + UB_position)
        ask_quantity_GEM_B = min (TRADING_LIMIT, POSITION_LIMIT - GEM_position)
        bid_quantity_GEM_B = min (TRADING_LIMIT, POSITION_LIMIT + GEM_position)
        ask_quantity_ETF_B = min (TRADING_LIMIT, POSITION_LIMIT - ETF_position)
        bid_quantity_ETF_B = min (TRADING_LIMIT, POSITION_LIMIT + ETF_position)
        
        #Read the news and update the estimates
        
        news = get_news()
        for counter in range(len(news) - 1):
            headline = news[counter]['headline']
            body = news[counter]['body']
            
            parsed_body = body.split(" ")
            
            tick = int(parsed_body[1])
            estimate = float(parsed_body[13][1:])
            
            lowest = estimate - (300 - tick)/50
            highest = estimate + (300 - tick)/50

            if 'UB' in headline:
                if lowest > UB_estimate['min']:
                    UB_estimate.update({'min' : lowest})
                if highest < UB_estimate['max']:
                    UB_estimate.update({'max' : highest})
                UB_news_received = True
            elif 'GEM' in headline:
                if lowest > GEM_estimate['min']:
                    GEM_estimate.update({'min' : lowest})
                if highest < GEM_estimate['max']:
                    GEM_estimate.update({'max' : highest})
                GEM_news_received = True
            
            ETF_estimate.update({'min' : GEM_estimate['min'] + UB_estimate['min']})
            ETF_estimate.update({'max' : GEM_estimate['max'] + UB_estimate['max']})
            
        # Determine the optimal strategy
        
        UB_long = ((1 - CONFIDENCE_LEVEL))*(UB_estimate['max'] - UB_estimate['min']) + UB_estimate['min'] - ask_price_UB
        UB_short = bid_price_UB - (UB_estimate['max'] - ((1 - CONFIDENCE_LEVEL))*(UB_estimate['max'] - UB_estimate['min']))
        GEM_long = ((1 - CONFIDENCE_LEVEL))*(GEM_estimate['max'] - GEM_estimate['min']) + GEM_estimate['min'] - ask_price_GEM
        GEM_short = bid_price_GEM - (GEM_estimate['max'] - ((1 - CONFIDENCE_LEVEL))*(GEM_estimate['max'] - GEM_estimate['min']))
        ETF_long = ((1 - CONFIDENCE_LEVEL))*(ETF_estimate['max'] - ETF_estimate['min']) + ETF_estimate['min'] - ask_price_ETF
        ETF_short = bid_price_ETF - (ETF_estimate['max'] - ((1 - CONFIDENCE_LEVEL))*(ETF_estimate['max'] - ETF_estimate['min']))
        
        strategy = [({'ticker': 'N/A', 'type': 'LIMIT', 'quantity': 0, 'price': 0, 'action': 'BUY'}, 0, 0),
                  ({'ticker': 'UB', 'type': 'MARKET', 'quantity': ask_quantity_UB_A, 'price': ask_price_UB, 'action': 'BUY'}, UB_long, ask_quantity_UB_B),
                  ({'ticker': 'UB', 'type': 'MARKET', 'quantity': bid_quantity_UB_A, 'price': bid_price_UB, 'action': 'SELL'}, UB_short, bid_quantity_UB_B),
                  ({'ticker': 'GEM', 'type': 'MARKET', 'quantity': ask_quantity_GEM_A, 'price': ask_price_GEM, 'action': 'BUY'}, GEM_long, ask_quantity_GEM_B),
                  ({'ticker': 'GEM', 'type': 'MARKET', 'quantity': bid_quantity_GEM_A, 'price': bid_price_GEM, 'action': 'SELL'}, GEM_short, bid_quantity_GEM_B),
                  ({'ticker': 'ETF', 'type': 'MARKET', 'quantity': ask_quantity_ETF_A, 'price': ask_price_ETF, 'action': 'BUY'}, ETF_long, ask_quantity_ETF_B),
                  ({'ticker': 'ETF', 'type': 'MARKET', 'quantity': bid_quantity_ETF_A, 'price': bid_price_ETF, 'action': 'SELL'}, ETF_short, bid_quantity_ETF_B)]
        
        strategy.sort(key = lambda tup: tup[1], reverse = True)

        # Makes trades
        
        if order_id == 0:
            order_received = True
        else:
            order_received = is_received(order_id)
        
        if order_received:
            if UB_news_received or GEM_news_received:
                if abs(UB_position) + abs(GEM_position) + abs(ETF_position) < POSITION_LIMIT:
                    quantity = strategy[0][0]['quantity']
                
                    temp_strategy = strategy[0][0]
                    temp_strategy.update({'quantity': TRADING_LIMIT})
                
                    while quantity > TRADING_LIMIT:
                        trade_leg = s.post('http://localhost:9999/v1/orders', params = temp_strategy)
                        quantity = quantity - TRADING_LIMIT
                        
                    temp_strategy.update({'quantity': quantity})
                    trade_leg = s.post('http://localhost:9999/v1/orders', params = temp_strategy)

                    if trade_leg.ok:
                        order_id = trade_leg.json()['order_id']

                else:
                    optimal_unwind = -1
                    optimal_unwind_needed = True
                    optimal_rewind = -1
                    optimal_rewind_needed = True

                    for counter in range(len(strategy)):
                        if ((strategy[counter][0]['quantity'] > 0) & (optimal_unwind_needed)):
                            optimal_unwind = counter
                            optimal_unwind_needed = False

                        if ((strategy[counter][2] > 0) & (optimal_rewind_needed)):
                            optimal_rewind = counter
                            optimal_rewind_needed = False

                    if not (optimal_unwind_needed or optimal_rewind_needed):
                        if (strategy[optimal_unwind][1] + strategy[optimal_rewind][1]) > 0:
                            temp_strategy = strategy[optimal_unwind][0]

                            trade_leg = s.post('http://localhost:9999/v1/orders', params=temp_strategy)

                            if trade_leg.ok:
                                order_id = trade_leg.json()['order_id']

        status = get_status()

if __name__ == '__main__':
    main()
