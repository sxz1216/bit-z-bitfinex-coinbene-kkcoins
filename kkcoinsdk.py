#!/usr/bin/env python
# -*- coding:utf-8 -*-
'''需要两个文件，api_key.txt,private.pem,均存放在根目录即可。'''
from OpenSSL.crypto import load_privatekey, FILETYPE_PEM, sign
import base64
import json
import time
import requests
import csv
try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode


"""
https://api.kkcoin.com/rest/<endpoint><get parameters>
api.kkcoin.com/rest：KKCoin.COM 的访问地址
endpoint：功能路由名称
get parameters：GET 方式携带的参数，POST 方式此处为空

"""

'''需要两个文件，api_key.txt,private.pem'''

ENDPOINT = "https://api.kkcoin.com/rest/"

BUY = "BUY"
SELL = "SELL"

LIMIT = "LIMIT"
MARKET = "MARKET"

IOC = "IOC"

proxies = {
    'https': 'http://127.0.0.1:1087',
    'http': 'http://127.0.0.1:1087'
}
def formatNumber(x):
    if isinstance(x, float):
        return "{:.8f}".format(x)
    else:
        return str(x)


class Client_Kkcoin():
    def __init__(self, apikey, secretkey,):
        self._public_key = apikey
        self._private_key = secretkey
        self.sessn = requests.Session()
        self.adapter = requests.adapters.HTTPAdapter(pool_connections=5,
                                                     pool_maxsize=5, max_retries=5)
        self.sessn.mount('http://', self.adapter)
        self.sessn.mount('https://', self.adapter)
        self._exchange_name = 'kkcoin'
        self.rebalance = 'off'
        self.Slippage = 0.002  # 滑点

    def signature(self, message):
        # 从PEM文件中读取私钥数据
        key_file = open('private.pem', 'rb')
        key_data = key_file.read()
        key_file.close()

        password = bytes('951114', encoding="utf-8")
        key = load_privatekey(FILETYPE_PEM, key_data, passphrase=password)
        content = message

        dig = sign(key, content, 'sha256')  # d为经过SHA1算法进行摘要、使用私钥进行签名之后的数据
        signature = base64.b64encode(dig).decode() # 将d转换为BASE64的格式
        return signature
    def signedRequest(self, method, path, params:dict):

        # create signature:

        _nonce = int(time.time())
        _new_params = {}
        if params == {}: # 空param用[]表示
            _new_params = []
            content = path + str(_new_params) + str(_nonce)
        else:
            keys = sorted(params.keys())   #参数升序排序
            for key in keys:
                _new_params[key] = str(params.get(key))
            content = path + json.dumps(_new_params) + str(_nonce)
        print(content.replace(' ','')) #强行去掉空格
        signature = self.signature(message=content.replace(' ',''))
        headers = {
            "Host": "api.kkcoin.com:80",
            "KKCOINAPIKEY": self._public_key,
            "KKCOINSIGN": signature,
            "KKCOINTIMESTAMP": str(_nonce),
            "Cache-Control": "no-cache",
        }
        print(headers)
        resp = self.sessn.request(method,ENDPOINT + path,headers=headers,params=_new_params, verify=False)
        print(resp.url)
        print(resp.content)
        data = json.loads(resp.content)
        return data

    def balance(self):
        """Get current balances for all symbols.
        asset_symbol	资产符号
        bal	余额
        available_bal	其中可用金额
        frozen_bal	其中冻结金额

        """
        try:

            data = self.signedRequest(method="GET", path="balance", params={})
            print(data)
            # print(data['balances'])
            # for i in data['balances']:
            #     print(i)
            balance = {'asset': {'total': 0, 'net': 0},
                       'trade': {},
                       'frozen': {},
                       }
            for i in data:
                balance['trade'][i['asset_symbol'].lower()] = float(i['available_bal'])
                balance['frozen'][i['asset_symbol'].lower()] = float(i['frozen_bal'])
            return balance
        except Exception as e:
            return e

    def trade(self,trade_type,amount, price,symbol,test=False):
        """
        委托下单 trade
        访问方式 POST

        参数
        字段	说明
        symbol	交易对符号，例如：KK_ETH
        ordertype	委托类型，LIMIT / 限价单
        orderop	BUY / 买，SELL / 卖
        price	委托价格
        amount	委托数量
        返回
        字段	说明
        order_id	订单号
        注意

        得到返回订单号不代表下单成功，需要通过 order 路由查询订单状态确认执行的结果
        """
        symbol = symbol.upper()

        side, orderType = trade_type.upper().split('_')
        params = {
            "symbol": symbol,
            "ordertype": orderType,
            "orderop": side,
            "price": price,
            "amount": amount,
        }
        path = "trade"
        data = self.signedRequest("POST", path, params)

        return data


    def order_info(self, order_id, symbol=None, **kwargs):
        """Check an order's status.
            status	订单状态： NEW / 新委托单，FILLED / 已完成，PARTIALLY_FILLED / 部分成交，CANCELED / 已取消
        """
        params = {'id':order_id}
        params.update(kwargs)
        data = self.signedRequest(method="GET", path="order", params=params)
        return data


    def cancel(self, order_id,symbol=None, **kwargs):
        """Cancel an active order.
        Args:
            symbol (str)
            orderId (int, optional)
            origClientOrderId (str, optional)
            newClientOrderId (str, optional): Used to uniquely identify this
                cancel. Automatically generated by default.
            recvWindow (int, optional)
        """

        params = {'id': order_id}
        params.update(kwargs)
        path = "cancel"
        data = self.signedRequest("POST", path, params)
        return data

    def cancel_all(self,order_id_list=None,symbol='ETH_USDT'):
        symbol = symbol.upper()
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



    def openOrders(self, symbol, **kwargs):
        """Get all open orders on a symbol.
        Args:
            参数	说明
            symbol	交易对符号，例如：KK_ETH
            返回
            字段	说明
            order_id	订单号
            symbol	交易对符号，例如：KK_ETH
            type	委托类型，LIMIT / 限价单，MARKET / 市价单（暂不支持）
            orderop	BUY / 买，SELL / 卖
            price	委托价格
            origin_amount	委托数量
            executed_price	成交均价
            executed_amount	成交量
            status	订单状态：NEW / 新委托单， FILLED / 已完成， PARTIALLY_FILLED / 部分成交，CANCELED / 已取消
            source	订单来源
            ip	订单来源 IP 地址
        """
        symbol = symbol.upper()
        params = {"symbol": symbol}
        params.update(kwargs)
        data = self.signedRequest("GET", 'openorders', params)
        return data

if __name__ == '__main__':
    filepath = 'api_key.txt'
    with open(filepath) as f:
        r  = csv.reader(f)
        APIKEY = list(r)[0][0]
        print(APIKEY)
    client = Client_Kkcoin(apikey=APIKEY,secretkey='')
    print(client.balance())
    '''print(client.order_info(order_id="923459920"))
    print(client.openOrders(symbol="KK_ETH"))
    print(client.balance()['trade']['btc'])
    print(client.cancel('7866876', 'btc_usdt'))
    print(client.trade('sell_limit',99,99,'KK_ETH'))'''
