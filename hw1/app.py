from typing import Any, Awaitable, Callable
import json
import urllib.parse


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

    # Обработка lifespan-сообщений
    if scope["type"] == "lifespan":
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return

    # Проверяем, что это HTTP-запрос
    if scope["type"] != "http":
        return

    # Получаем метод, путь и параметры запроса
    method = scope["method"]
    path = scope["path"]
    query_string = scope["query_string"].decode("utf-8")

    # Инициализация ответа
    status = 200
    response_body = {"result": None}

    try:
        # Обработка несуществующих эндпоинтов и неподдерживаемых методов
        if method != "GET" or (
            not path.startswith("/factorial")
            and not path.startswith("/fibonacci")
            and not path.startswith("/mean")
        ):
            status = 404
            response_body = {"error": "Not found"}
        else:
            if path.startswith("/factorial"):
                # Обработка /factorial?n=<number>
                if not query_string:
                    status = 422
                    response_body = {"error": "Missing parameter 'n'"}
                else:
                    params = urllib.parse.parse_qs(query_string)
                    if "n" not in params or len(params["n"]) != 1:
                        status = 422
                        response_body = {"error": "Invalid parameter 'n'"}
                    else:
                        try:
                            n = int(params["n"][0])
                            if n < 0:
                                status = 400
                                response_body = {
                                    "error": "Parameter 'n' must be non-negative"
                                }
                            else:
                                # Вычисляем факториал
                                result = 1
                                for i in range(1, n + 1):
                                    result *= i
                                response_body = {"result": result}
                        except ValueError:
                            status = 422
                            response_body = {
                                "error": "Parameter 'n' must be an integer"
                            }

            elif path.startswith("/fibonacci"):
                # Обработка /fibonacci/<n>
                try:
                    n = int(path.split("/")[-1])
                    if n < 0:
                        status = 400
                        response_body = {"error": "Parameter must be non-negative"}
                    else:
                        # Вычисляем число Фибоначчи
                        if n == 0:
                            result = 0
                        elif n == 1:
                            result = 1
                        else:
                            a, b = 0, 1
                            for _ in range(2, n + 1):
                                a, b = b, a + b
                            result = b
                        response_body = {"result": result}
                except ValueError:
                    status = 422
                    response_body = {"error": "Parameter must be an integer"}

            elif path.startswith("/mean"):
                # Обработка /mean с JSON в теле запроса
                message = await receive()
                if message["type"] != "http.request":
                    status = 422
                    response_body = {"error": "Invalid request format"}
                else:
                    body = message.get("body", b"")
                    if not body:
                        status = 422
                        response_body = {"error": "Missing numbers"}
                    else:
                        try:
                            numbers = json.loads(body)
                            if not isinstance(numbers, list):
                                status = 422
                                response_body = {
                                    "error": "Input must be a list of numbers"
                                }
                            elif not numbers:
                                status = 400
                                response_body = {
                                    "error": "List of numbers cannot be empty"
                                }
                            else:
                                try:
                                    numbers = [float(x) for x in numbers]
                                    result = sum(numbers) / len(numbers)
                                    response_body = {"result": result}
                                except (ValueError, TypeError):
                                    status = 422
                                    response_body = {
                                        "error": "All elements must be numbers"
                                    }
                        except json.JSONDecodeError:
                            status = 422
                            response_body = {"error": "Invalid JSON format"}

    except Exception:
        status = 422
        response_body = {"error": "Invalid request format"}

    # Подготовка ответа
    response_bytes = json.dumps(response_body).encode("utf-8")

    # Отправка заголовков
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [
                [b"content-type", b"application/json"],
                [b"content-length", str(len(response_bytes)).encode("utf-8")],
            ],
        }
    )

    # Отправка тела ответа
    await send(
        {
            "type": "http.response.body",
            "body": response_bytes,
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
