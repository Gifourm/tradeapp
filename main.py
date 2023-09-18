from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import insert, select

from src.auth.base_config import auth_backend, fastapi_users
from src.auth.models import role
from src.auth.router import router as router_activate
from src.auth.schemas import UserRead, UserCreate
from src.database import async_session_maker
from src.trade_logic.router import router as router_connection
from src.verify.router import router as router_verify

# from src.trade_logic.analysis import Analysis


@asynccontextmanager
async def startup_event(application: FastAPI) -> None:
    async with async_session_maker() as async_session:
        async with async_session.begin():
            exists = select(role).where(role.c.id == 2)
            result = await async_session.execute(exists)
            if not result.scalar():
                stmt = insert(role).values({'id': 1,
                                            'name': 'user',
                                            'permissions': []})
                await async_session.execute(stmt)
                stmt = insert(role).values({'id': 2,
                                            'name': 'admin',
                                            'permissions': ['all']})
                await async_session.execute(stmt)
                print('Добавить записи')
            await async_session.commit()
            print('Таблицы созданы')
    # await Analysis.finder()
    yield


app = FastAPI(
    title="Trading App",
    lifespan=startup_event
)

app.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth",
    tags=["Auth"],
)

app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["Auth"],
)

app.include_router(router_verify)
app.include_router(router_activate)
app.include_router(router_connection)




