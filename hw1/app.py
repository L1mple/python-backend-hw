from typing import Any, Awaitable, Callable

import json
import math
from urllib.parse import parse_qs
from http import HTTPStatus

async def _read_request_body(reader: Callable[[], Awaitable[dict[str, Any]]]) -> bytes:
    buffer = bytearray()
    continue_reading = True
    while continue_reading:
        event = await reader()
        if event.get("type") != "http.request":
            break
        chunk = event.get("body", b"")
        if chunk:
            buffer.extend(chunk)
        continue_reading = bool(event.get("more_body", False))
    return bytes(buffer)


async def _respond_json(writer: Callable[[dict[str, Any]], Awaitable[None]], status_code: int, data: dict,) -> None:
    body_bytes = json.dumps(data).encode("utf-8")
    headers = [
        (b"content-type", b"application/json"),
        (b"content-length", str(len(body_bytes)).encode("utf-8")),
    ]
    await writer({"type": "http.response.start", "status": status_code, "headers": headers})
    await writer({"type": "http.response.body", "body": body_bytes})


def _decode_query_params(raw_query: bytes) -> dict[str, list[str]]:
    query_str = raw_query.decode("utf-8")
    return parse_qs(query_str, keep_blank_values=True)


def _safe_int_cast(text: str):
    if text == "":
        return None, "empty"
    try:
        return int(text), None
    except Exception:
        return None, "bad"


def _calc_factorial(num: int) -> int:
    return math.factorial(num)


def _calc_fibonacci(num: int) -> int:
    first, second = 0, 1
    for _ in range(num):
        first, second = second, first + second
    return first

async def application(
    scope: dict[str, Any],
    receive: Callable[[], Awaitable[dict[str, Any]]],
    send: Callable[[dict[str, Any]], Awaitable[None]],
):
    """
    Args:
        scope: Словарь с информацией о запросе
        receive: Корутина для получения сообщений от клиента
        send: Корутина для отправки сообщений клиенту
    """
    # TODO: Ваша реализация здесь
    
    if scope.get("type") != "http":
        await _respond_json(send, HTTPStatus.NOT_FOUND, {"detail": "Не найдено"})
        return

    http_method = scope.get("method", "")
    url_path = scope.get("path", "")

    if http_method != "GET":
        await _respond_json(send, HTTPStatus.NOT_FOUND, {"detail": "Не найдено"})
        return


    if url_path == "/factorial":
        params = _decode_query_params(scope.get("query_string", b""))
        if "n" not in params:
            await _respond_json(send, HTTPStatus.UNPROCESSABLE_ENTITY, {"detail": "Отсутствует n"})
            return
        n_raw = params["n"][0]
        n_value, err = _safe_int_cast(n_raw)
        if err is not None:
            await _respond_json(send, HTTPStatus.UNPROCESSABLE_ENTITY, {"detail": "Параметр n должен быть целым числом"})
            return
        if n_value < 0:
            await _respond_json(send, HTTPStatus.BAD_REQUEST, {"detail": "n должен быть неотрицательным"})
            return

        try:
            result_val = _calc_factorial(n_value)
        except (OverflowError, ValueError) as exc:
            await _respond_json(send, HTTPStatus.BAD_REQUEST, {"detail": str(exc)})
            return
        await _respond_json(send, HTTPStatus.OK, {"result": result_val})
        return


    if url_path.startswith("/fibonacci/"):
        n_str = url_path[len("/fibonacci/") :]
        n_value, err = _safe_int_cast(n_str)
        if err is not None:
            await _respond_json(send, HTTPStatus.UNPROCESSABLE_ENTITY, {"detail": "Параметр пути должен быть целым числом"})
            return
        if n_value < 0:
            await _respond_json(send, HTTPStatus.BAD_REQUEST, {"detail": "n должен быть неотрицательным"})
            return
        fib_val = _calc_fibonacci(n_value)
        await _respond_json(send, HTTPStatus.OK, {"result": fib_val})
        return


    if url_path == "/mean":
        body_content = await _read_request_body(receive)
        if not body_content:
            await _respond_json(send, HTTPStatus.UNPROCESSABLE_ENTITY, {"detail": "Отсутствует тело запроса в формате JSON"})
            return
        try:
            parsed_data = json.loads(body_content.decode("utf-8"))
        except Exception:
            await _respond_json(send, HTTPStatus.UNPROCESSABLE_ENTITY, {"detail": "Некорректный JSON"})
            return
        if not isinstance(parsed_data, list):
            await _respond_json(send, HTTPStatus.UNPROCESSABLE_ENTITY, {"detail": "JSON должен быть массивом чисел"})
            return
        if len(parsed_data) == 0:
            await _respond_json(send, HTTPStatus.BAD_REQUEST, {"detail": "Массив не должен быть пустым"})
            return
        numbers = []
        for element in parsed_data:
            if isinstance(element, (int, float)):
                numbers.append(float(element))
            else:
                await _respond_json(send, HTTPStatus.UNPROCESSABLE_ENTITY, {"detail": "Элементы массива должны быть числами"})
                return
        avg_val = sum(numbers) / len(numbers)
        await _respond_json(send, HTTPStatus.OK, {"result": avg_val})
        return

    await _respond_json(send, HTTPStatus.NOT_FOUND, {"detail": "Не найдено"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
