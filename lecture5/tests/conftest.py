import pytest


async def to_str_async[_TVal](x: _TVal) -> str:
    return str(x)


@pytest.fixture()
def int_list() -> list[int]:
    return [1, 2, 3, 4, 5]


@pytest.fixture()
def int_list_empty() -> list[int]:
    return []
