from fastapi import Depends
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from .models import User
from .. import database


async def get_user_db(session: AsyncSession = Depends(database.get_async_session)) -> None:
    yield SQLAlchemyUserDatabase(session, User)
