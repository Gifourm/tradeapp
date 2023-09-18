import json
import time
from decimal import Decimal

import websockets
from sqlalchemy import select, insert, update, delete

from .manager import PoolManager
from .models import unfinished_trade
from ..database import async_session_maker
from ..exchange_api.binance import Client as binance_Client
from ..exchange_api.mexc import Client as mexc_Client
from ..trade_history.models import trade_history
from notification import send_telegram


class Analysis:
    ticker_box = set()
    black_list = ['DEFI', 'BTCST', 'LEVER', 'FIL', 'FOOTBALL', 'DODO', 'SPELL',
                  'HNT', 'BLUEBIRD', 'PHB', 'AMB', 'ANC', 'TLM', 'AUCTION', 'FXS', 'AGIX', 'AMB', 'USDC',
                  'SSV', 'RDNT', 'RAY', 'UNFI']

    @staticmethod
    async def finder() -> None:
        available_tickers = dict()
        exchange = binance_Client
        # for exchange in (binance_Client, mexc_Client):
        result = await exchange.exchange_info()
        for symbol in result:
            available_tickers[symbol['symbol']] = exchange

        while True:
            for ticker in available_tickers.keys():
                if ticker not in Analysis.ticker_box and ticker not in Analysis.black_list:
                    result = await Analysis.strategy(ticker, available_tickers[ticker], ticker)
                    if result['status'] == 'success':
                        Analysis.ticker_box.add(ticker)
                        pool = PoolManager.choose_from_pool(ticker, available_tickers[ticker])
                        await Analysis.maintenance(result, available_tickers[ticker], pool)
                    # candles = available_tickers[ticker].

    @staticmethod
    async def strategy(symbol: str, exchange: [binance_Client, mexc_Client], ticker: str) -> dict[str, str]:
        for timeframe in ('1h', '2h', '4h', '12h', '1d'):
            try:
                dataframe = exchange.get_candles(symbol, timeframe)
            except UnboundLocalError:
                return {'status': 'error'}

            """Hidden Logic"""

    @staticmethod
    async def maintenance(data: dict, exchange: [binance_Client, mexc_Client], pool: dict) -> None:
        """Hidden Logic"""
