from typing import Iterable

from demo_service.contracts import UserRequest, UserResource


def _generate_int_id() -> Iterable[int]:
    i = 0
    while True:
        yield i
        i += 1


_users = dict[int, UserResource]()
_id_generator = _generate_int_id()


def insert(user: UserRequest) -> UserResource:
    id = next(_id_generator)
    resource = UserResource(uid=id, **user.model_dump())

    _users[id] = resource

    return resource


def select(id: int) -> UserResource | None:
    return _users.get(id, None)
