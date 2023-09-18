from typing import Optional
from pydantic import BaseModel


class Connection(BaseModel):
    user_id: Optional[int] = 0
    position_size: float
    api_key: Optional[str] = ''
    api_secret_key: Optional[str] = ''
    telegram_chat: Optional[int] = 0
    exchange: Optional[str] = ''
    priority: Optional[int] = 0
    in_position: Optional[bool] = 0
