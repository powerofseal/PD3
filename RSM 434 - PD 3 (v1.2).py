# -*- coding: utf-8 -*-
"""
Created on Fri Oct 25 14:20:02 2019

@author: trader53
"""

import requests
import time

s = requests.Session()
s.headers.update({'X-API-key': '********'})

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
    
    current_gross_position = 0
    
    GEM_estimate = {'min' : 20, 'max' : 30, 'average' : 25}
    UB_estimate = {'min' : 40, 'max' : 60, 'average' : 50}
    ETF_estimate = {'min' : 60, 'max' : 90, 'average' : 75}
    
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

        current_gross_position = abs(UB_position) + abs(GEM_position) + abs(ETF_position)

        bid_price_UB = book['UB']['bids'][0]['price']
        ask_price_UB = book['UB']['asks'][0]['price']
        bid_price_GEM = book['GEM']['bids'][0]['price']
        ask_price_GEM = book['GEM']['asks'][0]['price']
        bid_price_ETF = book['ETF']['bids'][0]['price']
        ask_price_ETF = book['ETF']['asks'][0]['price']
        
        bid_quantity_UB = book['UB']['bids'][0]['quantity'] - book['UB']['bids'][0]['quantity_filled']
        ask_quantity_UB = book['UB']['asks'][0]['quantity'] - book['UB']['asks'][0]['quantity_filled']
        bid_quantity_GEM = book['GEM']['bids'][0]['quantity'] - book['GEM']['bids'][0]['quantity_filled']
        ask_quantity_GEM = book['GEM']['asks'][0]['quantity'] - book['GEM']['asks'][0]['quantity_filled']
        bid_quantity_ETF = book['ETF']['bids'][0]['quantity'] - book['ETF']['bids'][0]['quantity_filled']
        ask_quantity_ETF = book['ETF']['asks'][0]['quantity'] - book['ETF']['asks'][0]['quantity_filled']

        ask_quantity_UB = min (ask_quantity_UB, POSITION_LIMIT - (UB_position + abs(GEM_position) + abs(ETF_position)))
        bid_quantity_UB = min (bid_quantity_UB, POSITION_LIMIT - (- UB_position + abs(GEM_position) + abs(ETF_position)))
        ask_quantity_GEM = min (ask_quantity_GEM, POSITION_LIMIT - (abs(UB_position) + GEM_position + abs(ETF_position)))
        bid_quantity_GEM = min (bid_quantity_GEM, POSITION_LIMIT - (abs(UB_position) - GEM_position + abs(ETF_position)))
        ask_quantity_ETF = min (ask_quantity_ETF, POSITION_LIMIT - (abs(UB_position) + abs(GEM_position) + ETF_position))
        bid_quantity_ETF = min (bid_quantity_ETF, POSITION_LIMIT - (abs(UB_position) + abs(GEM_position) - ETF_position))
    
        strategy = [{'ticker': 'UB', 'type': 'LIMIT', 'quantity': 0, 'price': 0, 'action': 'BUY'},
                {'ticker': 'UB', 'type': 'LIMIT', 'quantity': ask_quantity_UB, 'price': ask_price_UB, 'action': 'BUY'},
                {'ticker': 'UB', 'type': 'LIMIT', 'quantity': bid_quantity_UB, 'price': bid_price_UB, 'action': 'SELL'},
                {'ticker': 'GEM', 'type': 'LIMIT', 'quantity': ask_quantity_GEM, 'price': ask_price_GEM, 'action': 'BUY'},
                {'ticker': 'GEM', 'type': 'LIMIT', 'quantity': bid_quantity_GEM, 'price': bid_price_GEM, 'action': 'SELL'},
                {'ticker': 'ETF', 'type': 'LIMIT', 'quantity': ask_quantity_ETF, 'price': ask_price_ETF, 'action': 'BUY'},
                {'ticker': 'ETF', 'type': 'LIMIT', 'quantity': bid_quantity_ETF, 'price': bid_price_ETF, 'action': 'SELL'},]
        
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
            
            UB_estimate.update({'average': (UB_estimate['min'] + UB_estimate['max'])/2})
            GEM_estimate.update({'average': (GEM_estimate['min'] + GEM_estimate['max'])/2})
            
            ETF_estimate.update({'min' : GEM_estimate['min'] + UB_estimate['min']})
            ETF_estimate.update({'max' : GEM_estimate['max'] + UB_estimate['max']})
            ETF_estimate.update({'average': UB_estimate['average'] + GEM_estimate['average']})  
            
        #Determine the optimal strategy
        
        UB_long = UB_estimate['average'] - ask_price_UB
        UB_short = bid_price_UB - UB_estimate['average']
        GEM_long = GEM_estimate['average'] - ask_price_GEM
        GEM_short = bid_price_GEM - GEM_estimate['average']
        ETF_long = ETF_estimate['average'] - ask_price_ETF
        ETF_short = bid_price_ETF - ETF_estimate['average']
        
        optimal_strategy = 0
        max_profit = 0
        if UB_long > max_profit:
            optimal_strategy = 1
            max_profit = UB_long
        if UB_short > max_profit:
            optimal_strategy = 2
            max_profit = UB_short
        if GEM_long > max_profit:
            optimal_strategy = 3
            max_profit = GEM_long
        if GEM_short > max_profit:
            optimal_strategy = 4
            max_profit = GEM_short
        if ETF_long > max_profit:
            optimal_strategy = 5
            max_profit = ETF_long
        if ETF_short > max_profit:
            optimal_strategy = 6
            max_profit = ETF_short
        
        #Makes trades
        
        if order_id == 0:
            order_received = True
        else:
            order_received = is_received(order_id)
        
        if order_received:
            if UB_news_received & GEM_news_received:
                quantity = strategy[optimal_strategy]['quantity']
                
                temp_strategy = strategy[optimal_strategy]
                temp_strategy.update({'quantity': TRADING_LIMIT})
                
                while quantity > TRADING_LIMIT:
                    trade_leg = s.post('http://localhost:9999/v1/orders', params = temp_strategy)
                    quantity = quantity - TRADING_LIMIT
                        
                temp_strategy.update({'quantity': quantity})
                trade_leg = s.post('http://localhost:9999/v1/orders', params = temp_strategy)
                
                if trade_leg.ok:
                    order_id = trade_leg.json()['order_id']
                    
                buy_cancel = s.post('http://localhost:9999/v1/commands/cancel', params={'query': 'Volume > 0'})
                sell_cancel = s.post('http://localhost:9999/v1/commands/cancel', params={'query': 'Volume < 0'})
        
        status = get_status()

if __name__ == '__main__':
    main()
