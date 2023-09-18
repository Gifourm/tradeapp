from pymexc import futures
from .signature import Signature
import time
import json
import requests
import pandas

base_url = 'https://contract.mexc.com'


class Client:
    stock = 'Mexc'

    def __init__(self, api, secret):
        self.client = futures.HTTP(api_key=api, api_secret=secret)

    def get_account(self):
        result = self.client.tiered_fee_rate(symbol='BTC_USDT')
        return result

    @staticmethod
    def ticker_24h(symbol) -> json:
        endpoint = f'https://api.mexc.com/api/v3/ticker/24hr?symbol={symbol}'
        # result = self.client.generate_query(request_method='get', endpoint=endpoint, symbol=symbol)
        result = requests.get(url=endpoint)
        return float(json.loads(result.text)['volume'])

    @staticmethod
    def exchange_info() -> json:
        endpoint = 'https://api.mexc.com/api/v3/exchangeInfo'
        result = requests.get(url=endpoint)
        return json.loads(result.text)['symbols']

    @staticmethod
    def get_candles(symbol: str, timeframe: str) -> pandas.DataFrame:
        if timeframe == '1h':
            timeframe = '60m'

        endpoint = 'https://api.mexc.com/api/v3/klines'
        params = {'symbol': symbol,
                  'interval': timeframe,
                  'limit': 201}
        result = json.loads(requests.get(url=endpoint, params=params).text)
        dataframe = pandas.DataFrame(result)
        dataframe = dataframe.iloc[:, :6]
        dataframe.columns = ['Date', 'High', 'Low', 'Open', 'Close', 'Volume']
        dataframe = dataframe.astype({'High': float, 'Low': float, 'Open': float, 'Close': float, 'Volume': float})
        return dataframe

    @staticmethod
    def current_price(symbol: str):
        endpoint = f'https://api.mexc.com/api/v3/ticker/price?symbol={symbol}'
        result = json.loads(requests.get(url=endpoint).text)
        return result['price']

    #  ПОТОМ ДОПИШУ МЕКС ЗАКРЫЛ АПИ НА ФЬЮЧАХ
    # def change_leverage(self, symbol) -> None:
    #     result = self.client.change_leverage()
    #     leverage = result[0]['brackets'][0]['initialLeverage']
    #     self.client.generate_query(request_method='post', endpoint=base_url + '/fapi/v1/leverage?',
    #                                symbol=symbol, leverage=leverage, timestamp=int(time.time() * 1000))

    # def create_orders(self, side: str, symbol: str, pool: dict, early_candle:
    # float, next_candle: float, break_candle: float) -> tuple[Decimal, Decimal, Decimal]:
    #     try:
    #         price_len = len(str(early_candle).split('.')[1])
    #     except IndexError:
    #         price_len = 0
    #     early_candle = Decimal(early_candle)
    #     next_candle = Decimal(next_candle)
    #     break_candle = Decimal(break_candle)
    #
    #     if side == 'BUY':
    #         first_limit = Decimal(f'{(early_candle + next_candle) / 2 * Decimal("0.985"): .{price_len}f}')
    #         second_limit = Decimal(f'{early_candle * Decimal("0.99"): .{price_len}f}')
    #         stop_limit = Decimal(f'{break_candle * Decimal("0.984"): .{price_len}f}')
    #         stop_len = (first_limit + second_limit) / 2 / stop_limit - 1
    #
    #     elif side == 'SELL':
    #         first_limit = Decimal(f'{(early_candle + next_candle) / 2 * Decimal("1.015"): .{price_len}f}')
    #         second_limit = Decimal(f'{early_candle * Decimal("1.01"): .{price_len}f}')
    #         stop_limit = Decimal(f'{break_candle * Decimal("1.016"): .{price_len}f}')
    #         stop_len = stop_limit / (first_limit + second_limit) / 2 - 1
    #
    #     qty_len = 0
    #     for ticker in Client.exchange_info():
    #         if ticker['symbol'] == symbol:
    #             qty_len = ticker['quantityPrecision']
    #
    #     for user in pool:
    #         position_qty = Decimal(f'{pool[user]["Position_size"] * 0.05 / stop_len: .{qty_len}}')
    #         self.client = Signature(Fernet(key).decrypt(pool[user]['Hashed_api_key']).decode('utf-8'),
    #                                 Fernet(key).decrypt(pool[user]['Hashed_secret_key']).decode('utf-8'))
    #         self.change_leverage(symbol)
    #
    #         for price in (first_limit, second_limit):
    #             self.client.generate_query(request_method='post', endpoint=base_url + '/fapi/v1/order?', symbol=symbol,
    #                                        side=side,
    #                                        type='LIMIT', quantity=position_qty, price=price,
    #                                        timeInForce='GTC', timestamp=int(time.time() * 1000))
    #
    #         if pool[user]['Telegram_chat'] != 0:
    #             send_telegram(chat_id=pool[user]['Telegram_chat'], message=f'Созданы лимит-ордера\n'
    #                                                                  f'{symbol}: {side}\nОрдера на открытие позиции:\n'
    #                                                                  f'1.{first_limit}$\n'
    #                                                                  f'2.{second_limit}$\n'
    #                                                                  f'Стоп: {stop_limit}$')
    #     return first_limit, second_limit, stop_limit
    #
    # def reduce_position(self, side: str, ticker: str, price: float, pool: dict):
    #     for user in pool:
    #         self.client = Signature(Fernet(key).decrypt(pool[user]['Hashed_api_key']).decode('utf-8'),
    #                                 Fernet(key).decrypt(pool[user]['Hashed_secret_key']).decode('utf-8'))
    #         quantity = self.get_quantity(Fernet(key).decrypt(pool[user]['Hashed_api_key']).decode('utf-8'),
    #                                      Fernet(key).decrypt(pool[user]['Hashed_secret_key']).decode('utf-8'), ticker)
    #         try:
    #             quantity_len = len(str(quantity).split('.')[1])
    #         except IndexError:
    #             quantity_len = 0
    #
    #         if quantity < 0:
    #             quantity = - float(Decimal(f'{quantity / 2: .{quantity_len}f}'))
    #         else:
    #             quantity = float(Decimal(f'{quantity / 2: .{quantity_len}f}'))
    #
    #         self.client.generate_query(request_method='post', endpoint=base_url + '/fapi/v1/order?', symbol=ticker,
    #                                    side=side, type='LIMIT', quantity=quantity, price=price,
    #                                    timeInForce='GTC', timestamp=int(time.time() * 1000))
    #         if pool[user]['Telegram_chat'] != 0:
    #             send_telegram(chat_id=pool[user]['Telegram_chat'], message=f'Зафиксирована половина профита по {ticker}'
    #                                                                  f'\nСтоп перемещен в зону безубытка',)
    #
    # def close_position(self, side: str, ticker: str, pool: dict):
    #     for user in pool:
    #         self.client = Signature(Fernet(key).decrypt(pool[user]['Hashed_api_key']).decode('utf-8'),
    #                                 Fernet(key).decrypt(pool[user]['Hashed_secret_key']).decode('utf-8'))
    #         quantity = self.get_quantity(Fernet(key).decrypt(pool[user]['Hashed_api_key']).decode('utf-8'),
    #                                      Fernet(key).decrypt(pool[user]['Hashed_secret_key']).decode('utf-8'), ticker)
    #         try:
    #             quantity_len = len(str(quantity).split('.')[1])
    #         except IndexError:
    #             quantity_len = 0
    #
    #         if quantity < 0:
    #             quantity = - float(Decimal(f'{quantity : .{quantity_len}f}'))
    #         else:
    #             quantity = float(Decimal(f'{quantity: .{quantity_len}f}'))
    #
    #         self.client.generate_query(request_method='post', endpoint=base_url + '/fapi/v1/order?', symbol=ticker,
    #                                    side=side, type='MARKET', quantity=quantity, reduceOnly=True,
    #                                    timestamp=int(time.time() * 1000))
    #
    # @staticmethod
    # def connect_websocket(symbol: str) -> str:
    #     symbol = symbol.rstrip('USDT').rstrip('BUSD')
    #     method = f'{symbol.lower()}usdt@kline_1h'
    #     url = f'wss://ws-api.binance.com:443/ws-api/v3/{method}'
    #     return url
    #
    # def cancel_order(self, ticker, hashed_api, hashed_secret):
    #     self.client = Signature(Fernet(key).decrypt(hashed_api).decode('utf-8'),
    #                             Fernet(key).decrypt(hashed_secret).decode('utf-8'))
    #     order = self.client.generate_query(endpoint=base_url + '/fapi/v1/openOrders?', request_method='get',
    #                                        symbol=ticker, timestamp=int(time.time() * 1000))
    #     for i in range(len(order)):
    #         self.client.generate_query(request_method='delete', endpoint=base_url + '/fapi/v1/order?',
    #                                    orderId=order[i]['orderId'], symbol=ticker, timestamp=int(time.time() * 1000))
    #
    # def get_quantity(self, hashed_api_key: str, hashed_secret_key: str, ticker):
    #     self.client = Signature(hashed_api_key, hashed_secret_key)
    #     orders = self.client.generate_query(endpoint=base_url + ' /fapi/v2/positionRisk?', request_method='get',
    #                                         symbol=ticker, timestamp=int(time.time() * 1000))['']
    #     quantity = 1
    #     for order in orders:
    #         if order['symbol'] == ticker and Decimal(order['positionAmt']) != Decimal('0'):
    #             quantity = Decimal(order['positionAmt'])
    #
    #     return quantity
