import json
import time
from decimal import Decimal

import pandas
import requests
from cryptography.fernet import Fernet

from notification import send_telegram
from .signature import Signature
from ..config import SECRET_KEY

base_url = 'https://fapi.binance.com'
key = SECRET_KEY


class Client:
    stock = 'Binance'

    @staticmethod
    async def get_account(api: str, secret: str) -> dict:
        endpoint = base_url + '/fapi/v2/account?'
        result = await Signature.generate_query(request_method='get', endpoint=endpoint,
                                                params=[{'timestamp': int(time.time() * 1000)}], header=[api],
                                                signs=[secret])
        return result[0]

    @staticmethod
    def ticker_24h(symbol) -> float:
        endpoint = base_url + f'/fapi/v1/ticker/24hr?symbol={symbol}'
        result = requests.get(url=endpoint)
        return float(json.loads(result.text)['volume'])

    @staticmethod
    async def exchange_info() -> dict:
        endpoint = base_url + '/fapi/v1/exchangeInfo'
        result = requests.get(url=endpoint)
        return json.loads(result.text)['symbols']

    @staticmethod
    def get_candles(symbol: str, timeframe: str) -> pandas.DataFrame:
        endpoint = base_url + f'/fapi/v1/klines'
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
    async def current_price(symbol: str) -> str:
        endpoint = base_url + f'/fapi/v1/ticker/price?symbol={symbol}'
        result = json.loads(requests.get(url=endpoint).text)
        return result['price']

    @staticmethod
    async def change_leverage(pool: dict, symbol: str) -> None:
        cipher_suite = Fernet(key)

        header = []
        params = []
        lev_params = []
        sign = []

        for user in pool:
            header.append(cipher_suite.decrypt(pool[user]['Hashed_api_key']).decode('utf-8'))
            lev_params.append({'symbol': symbol, 'timestamp': int(time.time() * 1000)})
            sign.append(cipher_suite.decrypt(pool[user]['Hashed_secret_key']).decode('utf-8'))

        leverage = await Signature.generate_query(request_method='get', endpoint=base_url + '/fapi/v1/leverageBracket',
                                                  header=header, params=lev_params, signs=sign)

        leverage = leverage[0]['brackets'][0]['initialLeverage']

        for user in range(len(pool)):
            params.append({'symbol': symbol, 'timestamp': int(time.time() * 1000), 'leverage': leverage[user]})

        await Signature.generate_query(request_method='post', endpoint=base_url + '/fapi/v1/leverage',
                                       header=header, params=params, signs=sign)

    @staticmethod
    async def create_orders(side: str,
                            symbol: str,
                            pool: dict,
                            early_candle: float,
                            next_candle: float,
                            break_candle: float
                            ) -> tuple[Decimal, Decimal, Decimal]:
        cipher_suite = Fernet(key)
        try:
            price_len = len(str(early_candle).split('.')[1])
        except IndexError:
            price_len = 0
        early_candle = Decimal(early_candle)
        next_candle = Decimal(next_candle)
        break_candle = Decimal(break_candle)

        if side == 'BUY':
            first_limit = Decimal(f'{(early_candle + next_candle) / 2 * Decimal("0.985"): .{price_len}f}')
            second_limit = Decimal(f'{early_candle * Decimal("0.99"): .{price_len}f}')
            stop_limit = Decimal(f'{break_candle * Decimal("0.984"): .{price_len}f}')
            stop_len = (first_limit + second_limit) / 2 / stop_limit - 1

        else:
            first_limit = Decimal(f'{(early_candle + next_candle) / 2 * Decimal("1.015"): .{price_len}f}')
            second_limit = Decimal(f'{early_candle * Decimal("1.01"): .{price_len}f}')
            stop_limit = Decimal(f'{break_candle * Decimal("1.016"): .{price_len}f}')
            stop_len = stop_limit / (first_limit + second_limit) / 2 - 1

        qty_len = 0
        for ticker in await Client.exchange_info():
            if ticker['symbol'] == symbol:
                qty_len = ticker['quantityPrecision']

        await Client.change_leverage(pool, symbol)

        header = []
        params = []
        sign = []

        for price in (first_limit, second_limit):
            for user in pool:
                header.append(cipher_suite.decrypt(pool[user]['Hashed_api_key']).decode('utf-8'))
                params.append({'symbol': symbol, 'timestamp': int(time.time() * 1000), 'price': price,
                               'timeInForce': 'GTC', 'type': 'LIMIT',
                               'quantity': Decimal(f'{pool[user]["Position_size"] * 0.05 / stop_len: .{qty_len}}'),
                               'side': side})
                sign.append(cipher_suite.decrypt(pool[user]['Hashed_secret_key']).decode('utf-8'))

            await Signature.generate_query(request_method='post', endpoint=base_url + '/fapi/v1/order',
                                           header=header, params=params, signs=sign)

        for user in pool:
            if pool[user]['Telegram_chat'] != 0:
                send_telegram(chat_id=pool[user]['Telegram_chat'], message=f'Созданы лимит-ордера\n'
                                                                           f'{symbol}: {side}\n'
                                                                           f'Ордера на открытие позиции:\n'
                                                                           f'1.{first_limit}$\n'
                                                                           f'2.{second_limit}$\n'
                                                                           f'Стоп: {stop_limit}$')

        return first_limit, second_limit, stop_limit

    @staticmethod
    async def reduce_position(side: str, ticker: str, price: float, pool: dict) -> None:
        cipher_suite = Fernet(key)
        header = []
        params = []
        sign = []

        quantity = await Client.get_quantity(pool, ticker, True)
        i = 0
        for user in pool:
            header.append(cipher_suite.decrypt(pool[user]['Hashed_api_key']).decode('utf-8'))
            params.append({'symbol': ticker, 'timestamp': int(time.time() * 1000), 'price': price,
                           'timeInForce': 'GTC', 'type': 'LIMIT', 'quantity': quantity[i], 'side': side})
            sign.append(cipher_suite.decrypt(pool[user]['Hashed_secret_key']).decode('utf-8'))
            i += 1

            if pool[user]['Telegram_chat'] != 0:
                send_telegram(chat_id=pool[user]['Telegram_chat'], message=f'Зафиксирована половина профита по {ticker}'
                                                                           f'\nСтоп перемещен в зону без убытка', )

        await Signature.generate_query(request_method='post', endpoint=base_url + '/fapi/v1/order',
                                       header=header, params=params, signs=sign)

    @staticmethod
    async def close_position(side: str, ticker: str, pool: dict) -> None:
        cipher_suite = Fernet(key)
        header = []
        params = []
        sign = []

        quantity = await Client.get_quantity(pool, ticker, False)
        i = 0
        for user in pool:
            header.append(cipher_suite.decrypt(pool[user]['Hashed_api_key']).decode('utf-8'))
            params.append({'symbol': ticker, 'timestamp': int(time.time() * 1000), 'reduceOnly': True,
                           'type': 'MARKET', 'quantity': quantity[i], 'side': side})
            sign.append(cipher_suite.decrypt(pool[user]['Hashed_secret_key']).decode('utf-8'))
            i += 1

        await Signature.generate_query(request_method='post', endpoint=base_url + '/fapi/v1/order',
                                       header=header, params=params, signs=sign)

    @staticmethod
    async def connect_websocket(symbol: str) -> str:
        symbol = symbol.rstrip('USDT').rstrip('BUSD')
        method = f'{symbol.lower()}usdt@kline_1h'
        url = f'wss://ws-api.binance.com:443/ws-api/v3/{method}'
        return url

    @staticmethod
    async def cancel_order(pool: dict, ticker: str) -> None:
        cipher_suite = Fernet(key)
        header = []
        params = []
        sign = []
        for user in pool:
            if pool[user]['Telegram_chat'] != 0:
                send_telegram(chat_id=pool[user]['Telegram_chat'], message=f'Прекращено слежение за {ticker}.'
                                                                           f'\nВозобновление поиска позиции')

            header.append(cipher_suite.decrypt(pool[user]['Hashed_api_key']).decode('utf-8'))
            params.append({'symbol': ticker, 'timestamp': int(time.time() * 1000)})
            sign.append(cipher_suite.decrypt(pool[user]['Hashed_secret_key']).decode('utf-8'))

        await Signature.generate_query(request_method='delete', endpoint=base_url + '/fapi/v1/allOpenOrders',
                                       header=header, params=params, signs=sign)

    @staticmethod
    async def get_quantity(pool: dict, ticker: str, reduce: bool) -> list:
        cipher_suite = Fernet(key)
        header = []
        params = []
        sign = []
        if reduce:
            mult = 2
        else:
            mult = 1

        for user in pool:
            header.append(cipher_suite.decrypt(pool[user]['Hashed_api_key']).decode('utf-8'))
            params.append({'symbol': ticker, 'timestamp': int(time.time() * 1000)})
            sign.append(cipher_suite.decrypt(pool[user]['Hashed_secret_key']).decode('utf-8'))

        orders_list = await Signature.generate_query(endpoint=base_url + ' /fapi/v2/positionRisk',
                                                     request_method='get',
                                                     header=header, params=params, signs=sign)
        quantity_list = []
        for orders in orders_list:
            for order in orders:
                if order['symbol'] == ticker and Decimal(order['positionAmt']) != Decimal('0'):
                    quantity = Decimal(order['positionAmt'])

                    try:
                        quantity_len = len(str(quantity).split('.')[1])
                    except IndexError:
                        quantity_len = 0

                    if quantity < 0:
                        quantity = - float(Decimal(f'{quantity / mult: .{quantity_len}f}'))
                    else:
                        quantity = float(Decimal(f'{quantity / mult: .{quantity_len}f}'))

                    quantity_list.append(quantity)

                elif order == orders[-1]:
                    quantity_list.append(1)

        return quantity_list
