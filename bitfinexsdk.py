#!/usr/bin/env python3
# -*- coding:utf-8 -*-

"""
@author: tutu
@file: bitfinexsdk.py
"""
import requests,json
import time
import hashlib
import hmac
import base64
import accountConfig


BASE_API = 'https://api.bitfinex.com/v1'

TICKER_API = '%s/pubticker'% BASE_API
DEPTH_API='%s/book' % BASE_API
BALANCE_API = '%s/balances' %BASE_API
TRADE_API = '%s/order/new' % BASE_API
CANCEL_API = '%s/order/cancel' % BASE_API
CANCEL_ALL_API = '%s/order/cancel/all' % BASE_API
CANCEL_MULTI_API = '%s/order/cancel/multi' % BASE_API
TRADEVIEW_API = '%s/order/status' % BASE_API
ADDRESS_API = '%s/deposit/new' % BASE_API

DEFAULT_HEADERS = {'Content-Type': 'application/json', 'Accept': 'application/json'}
proxies = {
    'https': 'http://127.0.0.1:1087',
    'http': 'http://127.0.0.1:1087'
}

def get_nonce_time():
    curr_stamp = time.time() * 100000000
    return str(int(curr_stamp))

def bitfinex_service(key_index='USD_1'):
    access_key = accountConfig.BITFINEX[key_index]['ACCESS_KEY']
    secret_key = accountConfig.BITFINEX[key_index]['SECRET_KEY']
    return Client_Bitfinex(access_key, secret_key)

class Client_Bitfinex():
    def __init__(self, access_key, secret_key,):
        self._public_key = access_key
        self._private_key = secret_key
        self.sessn = requests.Session()
        self.adapter = requests.adapters.HTTPAdapter(pool_connections=3,
                                            pool_maxsize=3, max_retries=5)
        self.sessn.mount('http://', self.adapter)
        self.sessn.mount('https://', self.adapter)
        self.exchange = 'bitfinex'
        self.rebalance = 'off'
        self.Slippage = 0.002  # 滑点

    def http_get(self, url, encode=False):
        # if encode is True:
        #     data_wrap = urlencode(data_wrap)
        req = self.sessn.get(url).content
        resp = json.loads(req)
        return resp

    def http_post(self,url, header):
        req = self.sessn.post(url, headers=header,proxies=proxies).content
        try:
            resp = json.loads(req)
        except:
            resp = None
        return resp

    def get_signature(self, data):
        payload = base64.standard_b64encode(json.dumps(data).encode('utf-8'))
        signature = hmac.new(self._private_key.encode('utf-8'), payload, digestmod=hashlib.sha384).hexdigest()
        headers = DEFAULT_HEADERS.copy()
        headers['X-BFX-APIKEY'] = self._public_key
        headers['X-BFX-PAYLOAD'] = payload
        headers['X-BFX-SIGNATURE'] = signature
        headers['Connection'] = 'close'
        return headers

    def get_fee(self,symbol='eth_cny'):
        return 0.002

    def get_depth(self,symbol='eth_usd'):
        try:
            symbol = symbol.replace('_','')
            url = DEPTH_API+ '/' + symbol
            temp = self.http_get(url)
            bids = []
            asks = []
            for i in temp['bids']:
                bids.append([float(i['price']),float(i['amount'])])
            for i in temp['asks']:
                asks.append([float(i['price']),float(i['amount'])])
            depth = {'bids':bids,'asks':asks}
            return depth
        except:
            return temp
            time.sleep(0.1)


    def get_ticker(self,symbol='eth_cny'):
        symbol=symbol.replace('_','')
        url = TICKER_API + '/' + symbol
        temp = self.http_get(url)
        ticker = {'vol':temp['volume'],'last':temp['last_price'],'sell':temp['ask'],'buy':temp['bid'],'high':temp['high'],'low':temp['low']}
        return ticker

    def trade(self,trade_type,amount, price='',symbol='eth_usd'):
        symbol = symbol.replace('_','')
        side,type = trade_type.split('_')
        type = 'exchange '+type
        if type == 'market':
            price = 1
        data = {'request':'/v1/order/new','nonce':get_nonce_time(),'symbol':symbol,'amount':str(amount),'price':str(price),'side':side,'type':type,'ocoorder':False,'buy_price_oco':0,'sell_price_oco':0}
        headers= self.get_signature(data)
        temp = self.http_post(TRADE_API,headers)
        if 'id' in temp:
            temp['order_id'] = temp['id']
        return temp

    def balance(self):
        try:
            data = {'request':'/v1/balances','nonce':get_nonce_time()}
            headers=self.get_signature(data)
            temp=self.http_post(BALANCE_API,headers)
            balance = {'asset':{'total':0,'net':0},'trade':{'btc': 0,'usd': 0,'cny': 0, 'eth': 0, 'ltc': 0, 'etc': 0},'frozen':{'btc': 0, 'usd': 0,'cny': 0, 'eth': 0, 'ltc': 0, 'etc': 0}}
            for i in temp:
                if i['type'] == 'exchange':
                    balance['trade'][i['currency']]=float(i['available'])
                    balance['frozen'][i['currency']]=float(i['amount'])-float(i['available'])
            return balance
        except:
            time.sleep(0.1)


    def cancel(self,order_id,symbol=None):
        data = {'request':'/v1/order/cancel','nonce':get_nonce_time(),'order_id':order_id}
        headers = self.get_signature(data)
        temp = self.http_post(CANCEL_API, headers)
        if 'id' in temp:
            temp['order_id'] = temp['id']
        return temp

    def order_info(self,order_id,symbol=None):
        data = {'request': '/v1/order/status', 'nonce': get_nonce_time(), 'order_id': order_id}
        headers = self.get_signature(data)
        temp = self.http_post(TRADEVIEW_API, headers)
        if 'id' in temp:
            temp['order_id'] = temp['id']
        return temp

    def cancel_all(self,order_id_list=None,symbol=None):
        data = {'request': '/v1/order/cancel/all', 'nonce': get_nonce_time()}
        headers = self.get_signature(data)
        temp = self.http_post(CANCEL_ALL_API, headers)
        return temp

    def deposit_address(self,wallet_name,symbol=None):
        method,money=symbol.split('_')
        if method == 'btc':
            method = 'bitcoin'
        elif method == 'ltc':
            method = 'litecoin'
        elif method == 'eth':
            method = 'ethereum'
        elif method == 'etc':
            method = 'ethereumc'
        data = {'request':'/v1/deposit/new','nonce':get_nonce_time(),'method':method,'wallet_name':wallet_name}
        headers = self.get_signature(data)
        temp = self.http_post(ADDRESS_API, headers)
        return temp