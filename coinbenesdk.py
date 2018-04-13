#!/usr/bin/env python
# -*- coding:utf-8 -*-
#author:xuanzhi

import requests
import json
import time
import hashlib




BASE_API = 'https://api.coinbene.com/v1/'

DEFAULT_HEADER = {}


proxies = {
    'https': 'http://127.0.0.1:1087',
    'http': 'http://127.0.0.1:1087'
}

class Client_Coinbene():
    def __init__(self, apikey, secretkey):
        self._public_key = str(apikey)
        self._private_key = str(secretkey)
        self.sessn = requests.Session()
        self.adapter = requests.adapters.HTTPAdapter(pool_connections=5,
                                                     pool_maxsize=5, max_retries=5)
        self.sessn.mount('http://', self.adapter)
        self.sessn.mount('https://', self.adapter)
        self._exchange_name = 'coinbene'
        self.order_list = []

    def signature(self, message):
        content = message
        #print(content)
        signature = hashlib.md5(content.encode('utf-8')).hexdigest().lower() # 32位md5算法进行加密签名
        return signature

    def signedRequest(self, method, path, params:dict):

        # create signature:

        _timestamp = str(int(time.time()*1000))   #时间戳，精确到毫秒
        params['timestamp'] = _timestamp
        params['apiid'] = self._public_key
        params['secret'] = self._private_key
        param = ''
        for key in sorted(params.keys()):
            #print(key)
            param += key.upper() + '=' + str(params.get(key)).upper() + '&'
        param = param.rstrip(' & ')
        #print(param) 
        signature = self.signature(message=param)
        #print(signature)
        params['sign'] = str(signature)
        del params['secret']
        #print(params)
        resp = self.sessn.request(method,BASE_API+path,headers=None,data=None,params=params,proxies=proxies)
        data = json.loads(resp.content)
        return data


    def ticker(self,symbol):
    	symbol = symbol.replace('_','').lower()
    	params = {'symbol':symbol}
    	data = self.signedRequest(method="GET",path ='market/ticker',params=params)['ticker']
    	return data

    def depth(self,symbol,depth=10):	#默认盘口深度为10
    	symbol = symbol.replace('_','').lower()
    	params = {'symbol':symbol,'depth':depth}
    	data = self.signedRequest(method="GET",path ='market/orderbook',params=params)['orderbook']
    	asks,bids = [],[] 
    	for item in data['asks']:
    		asks.append([item['price'],item['quantity']])
    	for item in data['bids']:
    		bids.append([item['price'],item['quantity']])
    	return {'asks':asks,'bids':bids}

    def balance(self):
    	params = {'account':'exchange'}
    	data = self.signedRequest(method="POST",path ='trade/balance',params=params)['balance']
    	available = []
    	frozen = []
    	total = []
    	for item in data:
    		key = item['asset']
    		available.append({key:item['available']})
    		frozen.append({key:item['reserved']})
    		total.append({key:item['total']})
    	tem = {'total':total,'available':available,'frozen':frozen}
    	return tem

    def trade(self,trade_type,price,amount,symbol):	
    	symbol = symbol.replace('_','').lower()
    	'''
    	trade_type:only buy-limit/sell-limit
    	'''
    	if trade_type != 'buy-limit' or 'sell-limit':
    		print('WRONG ORDER!!!!')
    	else:
    		params = {
    			'price':float(price),
    			'quantity':float(amount),
    			'symbol':symbol,
    			'type':trade_type
    		}
    	data = self.signedRequest(method="POST",path ='trade/order/place',params=params)['orderid']
    	self.order_list.append(data)
    	return data,self.order_list

    def order_info(self,order_id):
    	orderid = order_id.replace('_','')
    	params = {'orderid':orderid}
    	data = self.signedRequest(method="POST",path ='trade/order/info',params=params)['order']
    	return data

    def cancel_order(self,order_id):
    	orderid = order_id.replace('_','')
    	params = {'orderid':orderid}
    	data = self.signedRequest(method="POST",path ='trade/order/cancel',params=params)
    	return data

    def cancel_all(self,orderid_list):
    	for i in orderid_list:
    		cancel_order(i)
    	return 'Cancel all orders!'

    def open_orders(self,symbol):
    	symbol = symbol.replace('_','').lower()
    	params = {'symbol':symbol}
    	data = self.signedRequest(method="POST",path ='trade/order/open-orders',params=params)['order']
    	return data



client = Client_Coinbene(apikey,secretkey)
#print(client.ticker('btc_usdt'))
#print(client.depth('btc_usdt'))
#print(client.balance())


