import pytest

from lecture5.example_async import map_async, slow_map_async
from lecture5.tests.conftest import to_str_async


@pytest.mark.asyncio  # pytest-asyncio plugin
async def test_map_async(int_list) -> None:
    result = await map_async(to_str_async, int_list)
    assert result == ["1", "2", "3", "4", "5"]


@pytest.mark.asyncio  # pytest-asyncio plugin
@pytest.mark.parametrize(
    ("iterable_name", "expected_result"),
    [
        ("int_list", ["1", "2", "3", "4", "5"]),
        ("int_list_empty", []),
    ],
)
async def test_map_async_parametrized(
    request,  # provides api for managing fixtures
    iterable_name: str,
    expected_result: list,
) -> None:
    iterable = request.getfixturevalue(iterable_name)
    result = await map_async(to_str_async, iterable)
    assert result == expected_result


@pytest.mark.slow
@pytest.mark.asyncio  # pytest-asyncio plugin
async def test_slow_map_async(int_list) -> None:
    result = await slow_map_async(to_str_async, int_list)
    assert result == ["1", "2", "3", "4", "5"]
