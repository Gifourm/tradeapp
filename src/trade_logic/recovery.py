from sqlalchemy import select

from analysis import Analysis
from .manager import PoolManager
from .models import unfinished_trade
from ..database import async_session_maker
from ..exchange_api.binance import Client as binance_Client
from ..exchange_api.mexc import Client as mexc_Client
from ..trade_history.models import trade_history
from ..verify.models import exchange_info


async def recovery() -> None:  # Эту функцию нужно вызывать на старте и из неё запускать потоки рабочие
    async with async_session_maker() as async_session:
        async with async_session.begin():
            query = select(exchange_info).where(exchange_info.c.connected is True)
            exchange_info_result = await async_session.execute(query)
            if exchange_info_result.scalar():
                for user in exchange_info_result:
                    PoolManager.user_pool[user.exchange][user.user_id] = \
                        {'Position_size': user.position_size,
                         'Hashed_api_key': user.hashed_api_key,
                         'Hashed_secret_key': user.hashed_api_secret_key,
                         'Telegram_chat': 0,
                         'Priority': user.priority,
                         'In_position': False}

            query = select(unfinished_trade)
            unfinished_trade_result = await async_session.execute(query)
            if unfinished_trade_result.scalar():
                for trade in unfinished_trade_result:
                    pool = dict()
                    query = select(trade_history).where(trade_history.c.id == trade.trade_id)
                    trade_history_result = await async_session.execute(query).first()
                    users = trade_history_result.users
                    for index in range(len(users)):
                        query = select(exchange_info).where(exchange_info.c.user == users[index])
                        exchange_info_result = await async_session.execute(query).first()
                        PoolManager.user_pool[exchange_info_result.exchange][users[index]]['In_position'] = True
                        PoolManager.user_pool[exchange_info_result.exchange][users[index]]['Telegram_chat'] = \
                            unfinished_trade_result.telegram_id[index]
                        pool[users[index]] = PoolManager.user_pool[exchange_info_result.exchange][users[index]]

                    data = {'status': 'recovery',
                            'averaged': unfinished_trade_result.averaged,
                            'reduced': unfinished_trade_result.reduced,
                            'start_stop': unfinished_trade_result.stop_limit,
                            'first_limit': unfinished_trade_result.first_limit,
                            'second_limit': unfinished_trade_result.second_limit,
                            'ticker': trade_history_result.ticker}

                    exchange = binance_Client if exchange_info_result.exchange == 'Binance' else mexc_Client
                    await Analysis.maintenance(data, exchange, pool)  # ТУТ ЗАПУСКАТЬ РАБОЧИЙ ПОТОК
