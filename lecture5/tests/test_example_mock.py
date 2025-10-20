from http import HTTPStatus
from logging import getLogger
from typing import Any

import pytest
import responses
from pytest_mock import MockerFixture

from lecture5.example_register_user import (
    Entity,
    Errors,
    ExternalAuthAPI,
    ExternalIdentity,
    GoogleAuthAPI,
    InternalIdentity,
    PasswordManager,
    RegisterUserExternal,
    RegisterUserInternal,
    Repository,
    User,
    UserService,
    VKAuthAPI,
)

logger = getLogger(__name__)

ENCRYPTED_PASSWORD = "encrypted_password"


@pytest.fixture()
def user_data() -> dict[str, Any]:
    return {
        "name": "John Doe",
        "age": 30,
        "username": "john.doe",
        "password": "testPassword_123",
        "provider": "google",
        "provider_uid": "external-uid",
    }


@pytest.fixture()
def register_user_internal(user_data) -> RegisterUserInternal:
    return RegisterUserInternal(
        user_data["name"],
        user_data["age"],
        user_data["username"],
        user_data["password"],
    )


@pytest.fixture()
def register_user_external(user_data) -> RegisterUserExternal:
    return RegisterUserExternal(user_data["provider_uid"], user_data["provider"])


@pytest.fixture()
def providers() -> dict[str, ExternalAuthAPI]:
    return {}


@pytest.fixture()
def add_google_provider(providers: dict):
    providers[GoogleAuthAPI.provider] = GoogleAuthAPI()


@pytest.fixture()
def add_vk_provider(providers: dict):
    providers[VKAuthAPI.provider] = VKAuthAPI()


@pytest.fixture()
def mock_user_repository(mocker: MockerFixture) -> Repository[int, User]:
    return mocker.MagicMock(spec=Repository[int, User])


@pytest.fixture()
def mock_user_repository_insert_raises_connection_error(mock_user_repository) -> None:
    mock_user_repository.insert.side_effect = Errors.DISCONNECTED.as_exc()


@pytest.fixture()
def mock_user_repository_insert_raises_duplicate_error(mock_user_repository) -> None:
    mock_user_repository.insert.side_effect = Errors.DUPLICATE_USER.as_exc()


@pytest.fixture()
def mock_user_repository_insert_success(mocker: MockerFixture, mock_user_repository):
    def _insert_side_effect(user: User) -> Entity[int, User]:
        return Entity(0, user)

    mock_user_repository.insert.side_effect = _insert_side_effect


@pytest.fixture()
def mock_password_manager(mocker: MockerFixture) -> PasswordManager:
    return mocker.MagicMock(spec=PasswordManager)


@pytest.fixture()
def mock_password_manager_is_valid_password_true(mock_password_manager):
    mock_password_manager.is_password_valid.return_value = True


@pytest.fixture()
def mock_password_manager_is_valid_password_false(mock_password_manager):
    mock_password_manager.is_password_valid.return_value = False


@pytest.fixture(autouse=True)
def mock_password_manager_encrypt_password(mock_password_manager):
    mock_password_manager.encrypt_password.return_value = ENCRYPTED_PASSWORD


@pytest.fixture()
def mock_google_auth_api_get_user_http_error():
    responses.add(
        responses.GET,
        "http://google/auth",
        status=HTTPStatus.INTERNAL_SERVER_ERROR,
    )


@pytest.fixture()
def mock_vk_auth_api_get_user_http_error(user_data: dict):
    responses.add(
        responses.GET,
        "http://vk/auth/" + user_data["provider_uid"],
        status=HTTPStatus.INTERNAL_SERVER_ERROR,
    )


@pytest.fixture()
def mock_google_auth_api_get_user(user_data):
    responses.add(
        responses.GET,
        "http://google/auth",
        json={"name": user_data["name"], "age": user_data["age"]},
        status=HTTPStatus.OK,
    )


@pytest.fixture()
def mock_vk_auth_api_get_user(user_data):
    responses.add(
        responses.GET,
        "http://vk/auth/" + user_data["provider_uid"],
        json={
            "info": {
                "firstName": user_data["name"].split(" ")[0],
                "lastName": user_data["name"].split(" ")[1],
                "age": user_data["age"],
            }
        },
        status=HTTPStatus.OK,
    )


@pytest.mark.usefixtures("mock_password_manager_is_valid_password_false")
def test_register_user_internal_with_invalid_password(
    mock_user_repository,
    mock_password_manager,
    providers,
    register_user_internal,
):
    # arrange
    user_service = UserService(mock_user_repository, mock_password_manager, providers)

    # act
    with pytest.raises(Exception) as exc_info:
        user_service.register_user(register_user_internal)

    # assert
    assert Errors.INVALID_PASSWORD.value in str(exc_info.value)
    assert not mock_user_repository.insert.called
    assert not mock_password_manager.encrypt_password.called


@pytest.mark.usefixtures(
    "mock_password_manager_is_valid_password_true",
    "mock_user_repository_insert_raises_duplicate_error",
)
def test_register_user_duplicate_error(
    mock_user_repository: Repository[int, User],
    mock_password_manager: PasswordManager,
    providers: dict[str, ExternalAuthAPI],
    register_user_internal: RegisterUserInternal,
):
    user_service = UserService(mock_user_repository, mock_password_manager, providers)

    with pytest.raises(Exception) as exc_info:
        user_service.register_user(register_user_internal)

    assert Errors.DUPLICATE_USER.value in str(exc_info.value)


@pytest.mark.usefixtures(
    "mock_password_manager_is_valid_password_true",
    "mock_user_repository_insert_raises_connection_error",
)
def test_register_user_connection_error(
    mock_user_repository: Repository[int, User],
    mock_password_manager: PasswordManager,
    providers: dict[str, ExternalAuthAPI],
    register_user_internal: RegisterUserInternal,
):
    user_service = UserService(mock_user_repository, mock_password_manager, providers)

    with pytest.raises(Exception) as exc_info:
        user_service.register_user(register_user_internal)

    assert Errors.DISCONNECTED.value in str(exc_info.value)


@pytest.mark.usefixtures(
    "mock_password_manager_is_valid_password_true",
    "mock_user_repository_insert_success",
)
def test_register_user_internal(
    mock_user_repository: Repository[int, User],
    mock_password_manager: PasswordManager,
    providers: dict[str, ExternalAuthAPI],
    register_user_internal: RegisterUserInternal,
):
    user_service = UserService(mock_user_repository, mock_password_manager, providers)
    entity = user_service.register_user(register_user_internal)

    assert entity.info.name == register_user_internal.name
    assert entity.info.age == register_user_internal.age
    assert len(entity.info.identities) == 1
    assert isinstance(entity.info.identities[0], InternalIdentity)
    assert entity.info.identities[0].username == register_user_internal.username
    assert entity.info.identities[0].password == ENCRYPTED_PASSWORD


def test_register_user_external_not_found_provider(
    mock_user_repository: Repository[int, User],
    mock_password_manager: PasswordManager,
    providers: dict[str, ExternalAuthAPI],
    register_user_external: RegisterUserExternal,
):
    user_service = UserService(mock_user_repository, mock_password_manager, providers)

    with pytest.raises(Exception) as exc_info:
        user_service.register_user(register_user_external)

    assert Errors.PROVIDER_NOT_FOUND.value in str(exc_info.value)
    assert not mock_user_repository.insert.called


@responses.activate
@pytest.mark.usefixtures(
    "add_google_provider",
    "mock_google_auth_api_get_user_http_error",
)
def test_register_user_external_api_error_google(
    mock_user_repository: Repository[int, User],
    mock_password_manager: PasswordManager,
    providers: dict[str, ExternalAuthAPI],
    register_user_external: RegisterUserExternal,
):
    user_service = UserService(mock_user_repository, mock_password_manager, providers)

    with pytest.raises(Exception) as exc_info:
        user_service.register_user(register_user_external)

    assert Errors.API_ERROR.value in str(exc_info.value)
    assert not mock_user_repository.insert.called


@responses.activate
@pytest.mark.usefixtures(
    "add_google_provider",
    "mock_google_auth_api_get_user",
    "mock_user_repository_insert_success",
)
def test_register_user_external_google(
    mock_user_repository: Repository[int, User],
    mock_password_manager: PasswordManager,
    providers: dict[str, ExternalAuthAPI],
    register_user_external: RegisterUserExternal,
    user_data,
):
    user_service = UserService(mock_user_repository, mock_password_manager, providers)
    entity = user_service.register_user(register_user_external)

    assert entity.info.name == user_data["name"]
    assert entity.info.age == user_data["age"]
    assert len(entity.info.identities) == 1
    assert isinstance(entity.info.identities[0], ExternalIdentity)
    assert entity.info.identities[0].provider == GoogleAuthAPI.provider
    assert entity.info.identities[0].uid == user_data["provider_uid"]


@responses.activate
@pytest.mark.usefixtures(
    "add_vk_provider",
    "mock_vk_auth_api_get_user_http_error",
)
def test_register_user_external_api_error_vk(
    mock_user_repository: Repository[int, User],
    mock_password_manager: PasswordManager,
    providers: dict[str, ExternalAuthAPI],
    register_user_external: RegisterUserExternal,
):
    register_user_external.provider = "vk"
    user_service = UserService(mock_user_repository, mock_password_manager, providers)

    with pytest.raises(Exception) as exc_info:
        user_service.register_user(register_user_external)

    assert Errors.API_ERROR.value in str(exc_info.value)
    assert not mock_user_repository.insert.called


@responses.activate
@pytest.mark.usefixtures(
    "add_vk_provider",
    "mock_vk_auth_api_get_user",
    "mock_user_repository_insert_success",
)
def test_register_user_external_vk(
    mock_user_repository: Repository[int, User],
    mock_password_manager: PasswordManager,
    providers: dict[str, ExternalAuthAPI],
    register_user_external: RegisterUserExternal,
    user_data,
):
    register_user_external.provider = "vk"
    user_service = UserService(mock_user_repository, mock_password_manager, providers)
    entity = user_service.register_user(register_user_external)

    assert entity.info.name == user_data["name"]
    assert entity.info.age == user_data["age"]
    assert len(entity.info.identities) == 1
    assert isinstance(entity.info.identities[0], ExternalIdentity)
    assert entity.info.identities[0].provider == VKAuthAPI.provider
    assert entity.info.identities[0].uid == user_data["provider_uid"]
