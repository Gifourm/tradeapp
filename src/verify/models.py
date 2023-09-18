from sqlalchemy import Table, Column, Integer, String, MetaData, Float, ForeignKey, Boolean
from ..auth.models import user

metadata = MetaData()

exchange_info = Table(
    "exchange_info",
    metadata,
    Column("user_id", Integer, ForeignKey(user.c.id)),
    Column("hashed_api_key", String, unique=True),
    Column("hashed_api_secret_key", String, unique=True),
    Column("exchange", String),
    Column('position_size', Float),
    Column('priority', Integer),
    Column('connected', Boolean)
)
