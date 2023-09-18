from sqlalchemy import Table, Column, Integer, MetaData, Boolean, JSON, ForeignKey, Float

from ..trade_history.models import trade_history

metadata = MetaData()

unfinished_trade = Table(
    "unfinished_trade",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("trade_id", ForeignKey(trade_history.c.id)),
    Column("first_limit", Float),
    Column("second_limit", Float),
    Column("stop_limit", Float),
    Column("reduced", Boolean),
    Column("averaged", Boolean),
    Column("telegram_id", JSON)
)
