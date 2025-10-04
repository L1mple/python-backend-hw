from datetime import datetime

from pydantic import BaseModel


class UserResource(BaseModel):
    uid: int
    username: str
    first_name: str
    last_name: str
    birthdate: datetime | None = None


class UserRequest(BaseModel):
    username: str
    first_name: str
    last_name: str
    birthdate: datetime | None = None
