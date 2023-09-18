from pydantic import BaseModel


class UserVerify(BaseModel):
    api_key: str
    api_secret_key: str
    exchange: str
