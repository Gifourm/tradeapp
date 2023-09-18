import sqlalchemy.exc
from fastapi import APIRouter
from fastapi_users import FastAPIUsers, exceptions
from sqlalchemy import update

from .. import config
from ..auth.base_config import auth_backend
from ..auth.manager import get_user_manager, UserData
from ..auth.models import User as User, user as user_table
from ..database import async_session_maker

verification_token_secret = config.SECRET_AUTH
key = config.SECRET_KEY

router = APIRouter(
    prefix="/activate",
    tags=["Auth"]
)

fastapi_user = FastAPIUsers[User, int](
    get_user_manager,
    [auth_backend],
)

current_user = fastapi_user.current_user()


@router.get('')
async def user_activate(token: int) -> dict[str, str]:
    if token in UserData.user_data.keys():
        data = UserData.user_data[token]
    else:
        raise exceptions.UserNotExists

    async with async_session_maker() as async_session:
        async with async_session.begin():
            try:
                stmt = update(user_table).where(user_table.c.email == data['email']).values(is_active=True)
                await async_session.execute(stmt)
            except sqlalchemy.exc.IntegrityError:
                raise exceptions.UserNotExists
            UserData.del_from_dict(token)

    return {'status': 'success', 'details': 'Account activated'}
