import pandas
from sqlalchemy import insert, update

from .schemas import Connection
from ..database import async_session_maker
from ..exchange_api.binance import Client as binance_Client
from ..exchange_api.mexc import Client as mexc_Client
from ..verify.models import exchange_info as user_data


class PoolManager:
    user_pool = {'Binance': {},
                 'Mexc': {},
                 'Bybit': {}}

    @staticmethod
    def deep_update(base_dict: dict, update_dict: dict) -> dict:
        for key, value in update_dict.items():
            if isinstance(value, dict):
                base_dict[key] = PoolManager.deep_update(base_dict.get(key, {}), value)
            else:
                base_dict[key] = value
        return base_dict

    @staticmethod
    async def add_to_pool(exchange_info: Connection) -> None:
        exchange = exchange_info.exchange
        PoolManager.user_pool[exchange][exchange_info.user_id] = {'Position_size': exchange_info.position_size,
                                                                  'Hashed_api_key': exchange_info.api_key,
                                                                  'Hashed_secret_key': exchange_info.api_secret_key,
                                                                  'Telegram_chat': exchange_info.telegram_chat,
                                                                  'Priority': 0 if exchange_info.position_size < 10000
                                                                  else 1,
                                                                  'In_position': exchange_info.in_position}
        async with async_session_maker() as async_session:
            async with async_session.begin():
                stmt = insert(user_data).values({'position_size': exchange_info.position_size,
                                                 'hashed_api_key': exchange_info.api_key,
                                                 'hashed_api_secret_key': exchange_info.api_secret_key,
                                                 'exchange': exchange,
                                                 'priority': 0 if exchange_info.position_size < 10000 else 1,
                                                 'user_id': exchange_info.user_id,
                                                 'connected': True})
                await async_session.execute(stmt)

    @staticmethod
    async def del_from_pool(user_id) -> None:
        del PoolManager.user_pool[user_id]
        async with async_session_maker() as async_session:
            async with async_session.begin():
                stmt = update(user_data).values({'connected': False}).where(user_data.c.user_id == user_id)
                await async_session.execute(stmt)

    @staticmethod
    def choose_from_pool(symbol: str, exchange: [binance_Client, mexc_Client]) -> dict:
        ticker_volume = exchange.ticker_24h(symbol) * 0.00015
        frame = pandas.DataFrame(PoolManager.user_pool[exchange.stock]).T
        frame['Position_size'] = pandas.to_numeric(frame['Position_size'])
        frame['Priority'] = pandas.to_numeric(frame['Priority'])

        volume = 0
        pool = {}

        for priority in range(frame['Priority'].max(), -1, -1):
            while volume < ticker_volume:
                try:
                    filtered = frame[frame['Priority'] == priority]
                    if filtered['Position_size'].max() < ticker_volume - volume and \
                            not filtered.empty:
                        max_pos_size_index = filtered['Position_size'].idxmax()
                        if not PoolManager.user_pool[exchange][max_pos_size_index]['In_position']:
                            pool[max_pos_size_index] = PoolManager.user_pool[exchange][max_pos_size_index]
                            volume += frame.at[max_pos_size_index, 'Position_size']
                            frame = frame.drop(max_pos_size_index)
                    else:
                        break
                except IndexError:
                    break

        return pool

    @staticmethod
    def change_in_position(pool: dict, exchange: str) -> None:
        p = PoolManager.user_pool[exchange]
        for user in pool.keys():
            if user in p.keys():
                p[user]['In_position'] = not p[user]['In_position']

    @staticmethod
    def change_priority(pool: dict, exchange: str) -> None:
        p = PoolManager.user_pool[exchange]
        for user in p:
            user['Priority'] += 1

        for user in pool.keys():
            if user in p.keys():
                p[user]['Priority'] = 0

