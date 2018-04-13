#!/usr/bin/env python
# -*- coding:utf-8 -*-
# author xuanzhi
import base64
import json
import time
import requests
import csv
import random
import hashlib
try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode


"""
https://www.bit-z.com/api_v1/<endpoint><get parameters>
www.bit-z.com/api_v1/：bit-z.com 的访问地址
endpoint：功能路由名称
get parameters：GET 方式携带的参数，POST 方式此处为空

"""


ENDPOINT = "https://www.bit-z.com/api_v1/"
proxies = {
    'https': 'http://127.0.0.1:1087',
    'http': 'http://127.0.0.1:1087'

}
def formatNumber(x):
    if isinstance(x, float):
        return "{:.8f}".format(x)
    else:
        return str(x)


class Client_bit_z():
    def __init__(self, apikey, secretkey,tradepwd):
        self._public_key = apikey
        self._private_key = secretkey
        self._trade_pwd = tradepwd
        self.sessn = requests.Session()
        self.adapter = requests.adapters.HTTPAdapter(pool_connections=5,
                                                     pool_maxsize=5, max_retries=5)
        self.sessn.mount('http://', self.adapter)
        self.sessn.mount('https://', self.adapter)
        self._exchange_name = 'bit-z'
        self.rebalance = 'off'
        self.Slippage = 0.002  # 滑点

    def signature(self, message):
        content = message + self._private_key
        #print(content)
        signature = hashlib.md5(content.encode('utf-8')).hexdigest().lower() # 32位md5算法进行加密签名
        return signature

    def signedRequest(self, method, path, params:dict):

        # create signature:

        _timestamp = str(int(time.time()))
        _nonce = str(random.randint(100000,999999))
        params['timestamp'] = _timestamp
        params['nonce'] = _nonce
        params['api_key'] = self._public_key
        param = ''
        for key in sorted(params.keys()):
            #print(key)
            param += key + '=' + str(params.get(key)) + '&'
        param = param.rstrip(' & ')
        #print(param) 
        signature = self.signature(message=param)
        #print(signature)
        params['sign'] = str(signature)
        #print(params)
        resp = self.sessn.request(method,ENDPOINT + path,headers=None,data=None,params=params,proxies=proxies)
        data = json.loads(resp.content)
        return data

    def ticker(self,symbol):
        params = {'coin':symbol}
        data = self.signedRequest(method="GET",path = 'ticker',params=params)['data']
        return data

    def depth(self,symbol):
        '''
        显示深度10档的信息
        '''
        symbol = symbol.lower()
        params = {'coin': symbol}
        data = self.signedRequest(method='GET',path = 'depth',params=params)['data']
        temp = {'asks':data['asks'][:10],'bids':data['bids'][:10]}
        return temp

    def balance(self):
        """Get current balances for all symbols.
        只有全部的余额情况，没有冻结资金与可用资金的区分。
        """
        params = {}
        try:

            data = self.signedRequest(method="POST", path= "balances",params=params)['data']
            data.pop('uid')
            new_data = {'asset':data}
            return new_data
        except Exception as e:
            return e

    def trade(self,type,amount,price,symbol):   #只有限价买卖的功能
        """
        委托下单 tradeAdd
        访问方式 POST

        参数
        字段	说明
        symbol	交易对符号，例如：ltc_btc
        type	buy / 买，sell / 卖
        price	委托价格
        number	委托数量
        tradepwd 交易密码
        返回
        字段	说明
        code        状态码
        msg      	success or fail reason
        data        order_id
        """
        symbol = symbol.lower()
        if type == 'buy':
            type = 'in'
        if type == 'sell':
            type = 'out'
        params = {
            "type": str(type),
            "coin": symbol,
            "price": float(price),
            "number": float(amount),
            "tradepwd":str(self._trade_pwd)
        }
        data = self.signedRequest("POST", path = "tradeAdd", params=params)['data']

        return data


    def openOrders(self,symbol,order_id=None,**kwargs):
        symbol = symbol.lower()
        params = {'coin':symbol}
        #params.update(kwargs)
        data = self.signedRequest(method="POST", path="openOrders", params=params)['data']
        return data


    def cancel(self, order_id,symbol=None, **kwargs):
        params = {'id': order_id}
        params.update(kwargs)
        data = self.signedRequest("POST", path='tradeCancel', params=params)
        return data

    def cancel_all(self,order_id_list=None,symbol='mzc_btc'):   #没有具体调整
        symbol = symbol.lower()
        if order_id_list:
            for i in order_id_list:
                try:
                    result = self.cancel(order_id=i,symbol=symbol)
                except:
                    continue
        else:
            order_id_list=[]
            openorders = self.openOrders(symbol)
            for i in openorders:
                if type(i) == type({}):
                    order_id_list.append(i['orderId'])
                    # print(order_id_list)
            for i in order_id_list:
                try:
                    result = self.cancel(order_id=i,symbol=symbol)
                    # print(result)
                except:
                    continue



if __name__ == '__main__':
    APIKEY,SKEY,tradepwd = input('akey,skey,trade_password').strip().split(',')
    client = Client_bit_z(apikey=APIKEY,secretkey=SKEY,tradepwd=tradepwd)
    '''print(client.ticker('mzc_btc'))
    print(client.depth('mzc_btc'))
    print(client.balance())'''          #测试用例