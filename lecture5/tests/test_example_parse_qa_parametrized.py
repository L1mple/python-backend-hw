from typing import Any

import pytest

from lecture5.example_parse_qs import parse_qs


@pytest.mark.xfail()
@pytest.mark.parametrize(
    ("query_string", "expected_result"),
    [
        ("name=John", {"name": "John"}),
        ("name=John&age=30", {"name": "John", "age": "30"}),
        (
            "name=John&age=30&city=New%20York",
            {"name": "John", "age": "30", "city": "New York"},
        ),
        (
            "name=John&age=30&city=New%20York&key=",
            {"name": "John", "age": "30", "city": "New York", "key": ""},
        ),
        ("name=John&name=Mary", {"name": ["John", "Mary"]}),
    ],
)
def test_parse_qs_valid(query_string: str, expected_result: dict[str, Any]) -> None:
    result = parse_qs(query_string)
    assert result == expected_result
