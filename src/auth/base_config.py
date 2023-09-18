from fastapi_users import FastAPIUsers
from fastapi_users.authentication import CookieTransport, AuthenticationBackend
from fastapi_users.authentication import JWTStrategy

from .manager import get_user_manager
from .models import User
from .. import config


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=config.SECRET_AUTH, lifetime_seconds=3600)


cookie_transport = CookieTransport(cookie_name="GarmTrade", cookie_max_age=3600)

auth_backend = AuthenticationBackend(
    name="jwt",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, int](
    get_user_manager,
    [auth_backend],
)
