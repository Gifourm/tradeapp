import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from fastapi import Depends, Request
from fastapi_users import BaseUserManager, IntegerIDMixin, exceptions, models, schemas

from .models import User
from .utils import get_user_db
from .. import config


class UserData:
    user_data: dict[hash, dict[str, str]] = {}

    @staticmethod
    def add_to_dict(key: hash, value: dict[str, str]) -> None:
        UserData.user_data[key] = value

    @staticmethod
    def del_from_dict(key: hash) -> None:
        del UserData.user_data[key]


def send_email(email: str, token: hash) -> None:
    # Добавить хтмл все такое чтоб красиво было
    message = f"Для подтверждения регистрации перейдите по ссылке\nhttp://localhost:8000/activate?token={token}"
    msg = MIMEMultipart()
    msg['From'] = "Gifourm@yandex.ru"
    msg['To'] = email
    msg['Subject'] = "Регистрация GarmTrade"
    msg.attach(MIMEText(message, 'plain'))

    sender = "Gifourm@yandex.ru"  # Ну это потом изменить сам понимаешь
    password = config.EMAIL_PASSWORD
    try:
        server = smtplib.SMTP_SSL('smtp.yandex.ru', 465)
        server.ehlo(sender)
        server.login("Gifourm@yandex.ru", password)
        server.auth_plain()
        server.send_message(msg)
        server.quit()
    except Exception as _e:
        raise exceptions.FastAPIUsersException


class UserManager(IntegerIDMixin, BaseUserManager[User, int]):
    reset_password_token_secret = config.SECRET_AUTH
    verification_token_secret = config.SECRET_AUTH

    async def on_after_register(self, user: User, request: Optional[Request] = None) -> dict[str, str]:
        return {'status': "success", 'details': 'Check your email for activation link'}

    async def create(self, user_create: schemas.UC,
                     safe: bool = False,
                     request: Optional[Request] = None
                     ) -> models.UP:
        await self.validate_password(user_create.password, user_create)

        existing_user = await self.user_db.get_by_email(user_create.email)
        if existing_user is not None:
            raise exceptions.UserAlreadyExists()

        user_dict = (
            user_create.create_update_dict()
            if safe
            else user_create.create_update_dict_superuser()
        )
        password = user_dict.pop("password")
        user_dict["hashed_password"] = self.password_helper.hash(password)
        user_dict["role_id"] = 1
        user_dict['is_active'] = 0

        try:
            activation_token = hash(user_dict['email'])
            UserData.add_to_dict(activation_token, {'email': user_dict['email'], 'req_time': time.time()})
            send_email(email=user_dict['email'], token=activation_token)
        except exceptions.FastAPIUsersException:
            raise exceptions.FastAPIUsersException

        created_user = await self.user_db.create(user_dict)

        await self.on_after_register(created_user, request)

        return created_user


async def get_user_manager(user_db=Depends(get_user_db)) -> None:
    yield UserManager(user_db)
