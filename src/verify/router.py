import jwt
import sqlalchemy.exc
from cryptography.fernet import Fernet
from fastapi import APIRouter, Depends
from fastapi_users import FastAPIUsers, exceptions
from fastapi_users.jwt import decode_jwt, generate_jwt
from sqlalchemy import insert, update, select

from .models import exchange_info
from .schemas import UserVerify
from .. import config
from ..auth.base_config import auth_backend
from ..auth.manager import get_user_manager
from ..auth.models import User as User, user as user_table
from ..database import async_session_maker
from ..exchange_api.binance import Client as binance_Client
from ..exchange_api.mexc import Client as mexc_Client

verification_token_secret = config.SECRET_AUTH
key = config.SECRET_KEY

router = APIRouter(
    prefix="/verify",
    tags=["Verify"]
)

fastapi_user = FastAPIUsers[User, int](
    get_user_manager,
    [auth_backend],
)

current_user = fastapi_user.current_user()


async def on_after_request_verify(token: str, user: User) -> None:
    try:
        data = decode_jwt(
            token,
            verification_token_secret,
            ["fastapi-users:verify"]
        )
    except jwt.PyJWTError:
        raise exceptions.InvalidVerifyToken()

    try:
        exchange = data["exchange"]
        api = data['api_key']
        secret_api = data['api_secret_key']
    except KeyError:
        raise exceptions.InvalidVerifyToken()

    async with async_session_maker() as async_session:
        async with async_session.begin():
            query = select(user_table).where(user_table.c.email == user.email, user_table.c.id == user.id)
            result = await async_session.execute(query)
            if result is None:
                raise exceptions.UserNotExists

    if user.is_verified:
        raise exceptions.UserAlreadyVerified()

    cipher_suite = Fernet(key.encode('utf-8'))
    hashed_api = cipher_suite.encrypt(api.encode('utf-8'))
    hashed_api_secret = cipher_suite.encrypt(secret_api.encode('utf-8'))

    async with async_session_maker() as async_session:
        async with async_session.begin():
            try:
                stmt = insert(exchange_info).values(user_id=user.id, hashed_api_key=hashed_api,
                                                    hashed_api_secret_key=hashed_api_secret,
                                                    exchange=exchange)
                await async_session.execute(stmt)
            except sqlalchemy.exc.InternalError:
                raise exceptions.UserAlreadyExists

            stmt = update(user_table).where(user_table.c.id == user.id).values(is_verified=True)
            await async_session.execute(stmt)


async def request_verify(params: UserVerify, user: User) -> None:
    if not user.is_active:
        raise exceptions.UserInactive()
    if user.is_verified:
        raise exceptions.UserAlreadyVerified()

    token_data = {
        'sub': str(user.id),
        'email': user.email,
        'aud': "fastapi-users:verify",
        'api_key': params.api_key,
        'api_secret_key': params.api_secret_key,
        'exchange': params.exchange
    }
    token = generate_jwt(
        token_data,
        verification_token_secret,
        3600
    )

    await on_after_request_verify(token, user)


# В фронтэнде добавить подсказку о необходимости добавления IP сервера в исключения API
@router.post("/")
async def user_verify(data: UserVerify, user: User = Depends(current_user)) -> dict[str, str]:
    params = data.model_dump()
    if params['exchange'] == 'Binance':
        api = params['api_key']
        secret = params['api_secret_key']
        try:
            result = await binance_Client.get_account(api, secret)
            print(result['canTrade'])
        except KeyError:
            return {'status': 'error', 'details': 'Invalid API-keys'}

    elif params['exchange'] == 'Mexc':
        client = mexc_Client(params['api_key'], params['api_secret_key'])
        try:
            result = client.get_account()
            print(result['data']['makerFee'])
        except KeyError:
            return {'status': 'error', 'details': 'Invalid API-keys'}

    elif params['exchange'] == 'Bybit':
        return {'status': 'error', 'details': 'The specified exchange is not supported'}

    else:
        return {'status': 'error', 'details': 'The specified exchange is not supported'}
    await request_verify(data, user)
