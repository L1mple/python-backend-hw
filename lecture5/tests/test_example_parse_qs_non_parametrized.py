import pytest

from example_parse_qs import parse_qs


def test_parse_qs_valid_1() -> None:
    query_string = "name=John"  # arrange
    result = parse_qs(query_string)  # act
    assert result == {"name": "John"}  # assert


def test_parse_qs_valid_2() -> None:
    query_string = "name=John&age=30"
    result = parse_qs(query_string)
    assert result == {"name": "John", "age": "30"}


@pytest.mark.xfail()
def test_parse_qs_valid_3() -> None:
    query_string = "name=John&age=30&city=New%20York"
    result = parse_qs(query_string)
    assert result == {"name": "John", "age": "30", "city": "New York"}


@pytest.mark.xfail()
def test_parse_qs_valid_4() -> None:
    query_string = "name=John&age=30&city=New%20York&key="
    result = parse_qs(query_string)
    assert result == {"name": "John", "age": "30", "city": "New York", "key": ""}


@pytest.mark.xfail()
def test_parse_qs_valid_5() -> None:
    query_string = "name=John&name=Mary"
    result = parse_qs(query_string)
    assert result == {"name": ["John", "Mary"]}


# and many more tests
