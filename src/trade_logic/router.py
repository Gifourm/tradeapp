from typing import Optional

from fastapi import APIRouter, Depends
from fastapi_users import FastAPIUsers

from .manager import PoolManager
from .schemas import Connection
from .. import config
from ..auth.base_config import auth_backend
from ..auth.manager import get_user_manager
from ..auth.models import User as User

verification_token_secret = config.SECRET_AUTH
key = config.SECRET_KEY

router = APIRouter(
    prefix="/connection",
    tags=["Bot_control"]
)

fastapi_user = FastAPIUsers[User, int](
    get_user_manager,
    [auth_backend],
)

current_user = fastapi_user.current_user()


@router.post("/connect")
async def connection(exchange_info: Connection = Depends(Connection),
                     user: User = Depends(current_user)
                     ) -> Optional[dict[str, str]]:
    if not user.is_verified:
        return {'status': 'error', 'details': 'User is not verified'}
    await PoolManager.add_to_pool(exchange_info)


@router.post('/disconnect')
async def disconnect(user: User = Depends(current_user)) -> Optional[dict[str, str]]:
    if user.id not in PoolManager.user_pool:
        return {'status': 'error', 'details': 'User is not connected'}
    else:
        await PoolManager.del_from_pool(user.id)
