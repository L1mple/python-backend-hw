from dataclasses import dataclass
from enum import StrEnum
from logging import getLogger
from typing import Protocol

import requests
from requests.exceptions import HTTPError

logger = getLogger(__name__)


class Errors(StrEnum):
    INVALID_PASSWORD = "INVALID_PASSWORD"
    DUPLICATE_USER = "DUPLICATE_USER"
    DISCONNECTED = "DISCONNECTED"
    API_ERROR = "API_ERROR"
    PROVIDER_NOT_FOUND = "PROVIDER_NOT_FOUND"

    def as_exc(self) -> Exception:
        return Exception(self.value)


@dataclass(slots=True)
class Entity[TId, TInfo]:
    uid: TId
    info: TInfo


@dataclass(slots=True)
class ExternalIdentity:
    uid: str
    provider: str


@dataclass(slots=True)
class InternalIdentity:
    username: str
    password: str


type Identity = ExternalIdentity | InternalIdentity


@dataclass(slots=True)
class User:
    name: str
    age: int
    identities: list[Identity]


@dataclass(slots=True)
class RegisterUserInternal:
    name: str
    age: int
    username: str
    password: str


@dataclass(slots=True)
class RegisterUserExternal:
    uid: str
    provider: str


type RegisterUser = RegisterUserExternal | RegisterUserInternal


class Repository[TId, TModel](Protocol):
    def insert(self, model: TModel) -> Entity[TId, TModel]: ...
    def get_by_id(self, id: TId) -> Entity[TId, TModel] | None: ...
    def delete_by_id(self, id: TId) -> None: ...
    def replace_by_id(self, id: TId, model: TModel) -> Entity[TId, TModel]: ...


class ExternalAuthAPI(Protocol):
    def get_user(self, uid: str) -> User: ...


class GoogleAuthAPI(ExternalAuthAPI):
    provider = "google"

    def get_user(self, uid: str) -> User:
        response = requests.get("http://google/auth", params={"id": uid})
        response.raise_for_status()

        response_data = response.json()
        return User(
            name=response_data["name"],
            age=response_data["age"],
            identities=[ExternalIdentity(uid=uid, provider=self.provider)],
        )


class VKAuthAPI(ExternalAuthAPI):
    provider = "vk"

    def get_user(self, uid: str) -> User:
        response = requests.get(f"http://vk/auth/{uid}")
        response.raise_for_status()

        response_data = response.json()
        return User(
            name=response_data["info"]["firstName"]
            + " "
            + response_data["info"]["lastName"],
            age=response_data["info"]["age"],
            identities=[ExternalIdentity(uid=uid, provider=self.provider)],
        )


class PasswordManager(Protocol):
    def is_password_valid(self, password: str) -> bool: ...
    def encrypt_password(self, password: str) -> str: ...
    def is_password_match(
        self, password: str, target_encrypted_password: str
    ) -> bool: ...


@dataclass(slots=True)
class UserService:
    _repository: Repository[int, User]
    _password_manager: PasswordManager
    _external_providers: dict[str, ExternalAuthAPI]

    def register_user(self, message: RegisterUser) -> Entity[int, User]:
        match message:
            case RegisterUserInternal():
                return self._register_user_internal(message)
            case RegisterUserExternal():
                return self._register_user_external(message)

    def _register_user_internal(
        self, message: RegisterUserInternal
    ) -> Entity[int, User]:
        logger.info("Register internal")

        if not self._password_manager.is_password_valid(message.password):
            logger.info("Password %s not valid", message.password)
            raise Errors.INVALID_PASSWORD.as_exc()

        encrypted_password = self._password_manager.encrypt_password(message.password)
        user = User(
            message.name,
            message.age,
            identities=[
                InternalIdentity(
                    username=message.username,
                    password=encrypted_password,
                ),
            ],
        )

        return self._repository.insert(user)

    def _register_user_external(
        self, message: RegisterUserExternal
    ) -> Entity[int, User]:
        logger.info("Register internal")

        if message.provider not in self._external_providers:
            logger.info("Provider %s not found", message.provider)
            raise Errors.PROVIDER_NOT_FOUND.as_exc()

        provider = self._external_providers[message.provider]

        try:
            user = provider.get_user(message.uid)
        except HTTPError as e:
            raise Errors.API_ERROR.as_exc() from e

        return self._repository.insert(user)
