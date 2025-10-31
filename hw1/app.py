from typing import Any, Awaitable, Callable


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

    def get_params(query_string: str) -> dict[str, str]:
        """Парсит query_string в словарь параметров вида {"key": "value"}"""

        query_params = {}
        for pair in query_string.split("&"):
            if "=" in pair:
                key, value = pair.split("=", 1)
                query_params[key] = value
        return query_params

    async def send_response(status: int, message: str) -> None:
        """Отправляет ответ клиенту"""
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    [b"content-type", b"application/json"],
                ],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": message.encode(),
            }
        )

    if scope["type"] == "http":

        path = scope["path"]
        query_string = scope.get("query_string", b"").decode()

        # Реализация API для расчета чисел Фибоначчи
        if path.startswith("/fibonacci/"):

            path_parsed = path.split("/")
            n_value = path_parsed[2]

            # Проверка наличия параметра для расчета
            if not n_value:
                message = (
                    '{"error": "Number parameter \\"/fibonacci/{n}\\" is required"}'
                )
                await send_response(422, message)
                return

            # Попытка преобразовать параметр в число
            try:
                n = int(n_value)
            except ValueError:
                message = f'{{"error": "Parameter \\"n\\" must be an integer, got \\"{n_value}\\""}}'
                await send_response(422, message)
                return

            # Проверка на отрицательное число
            if n < 0:
                message = (
                    f'{{"error": "Parameter \\"n\\" cannot be negative, got {n}"}}'
                )
                await send_response(400, message)
                return

            # Расчет числа Фибоначчи
            else:

                a, b = 0, 1
                for _ in range(n):
                    a, b = b, a + b

                factorial_number = a
                result = f'{{"result": {factorial_number}}}'

                await send_response(200, result)
                return

        # Реализация API для расчета факториала
        elif path.startswith("/factorial"):

            query_params = get_params(query_string)

            # Проверка наличия параметра n
            if "n" not in query_params:
                message = '{"error": "Parameter \\"n\\" is required"}'
                await send_response(422, message)
                return

            n_value = query_params["n"]

            # Проверка, что параметр не пустой
            if not n_value:
                message = '{"error": "Parameter \\"n\\" cannot be empty"}'
                await send_response(422, message)
                return

            # Попытка преобразовать параметр в число
            try:
                n = int(n_value)
            except ValueError:
                message = f'{{"error": "Parameter \\"n\\" must be an integer, got \\"{n_value}\\""}}'
                await send_response(422, message)
                return

            # Проверка на отрицательное число
            if n < 0:
                message = (
                    f'{{"error": "Parameter \\"n\\" cannot be negative, got {n}"}}'
                )
                await send_response(400, message)
                return

            # Расчет факториала
            else:

                factorial_number = 1
                for i in range(1, n + 1):
                    factorial_number *= i

                result = f'{{"result": {factorial_number}}}'
                await send_response(200, result)
                return

        # Реализация API для расчета среднего
        elif path.startswith("/mean"):

            query_params = get_params(query_string)

            # Проверка наличия параметра numbers
            try:
                numbers_list = []

                # Получение данных из тела запроса
                body = b""
                more_body = True

                while more_body:
                    message = await receive()
                    body += message.get("body", b"")
                    more_body = message.get("more_body", False)

                if body:

                    body_str = body.decode().strip()

                    # Проверка, что данные не пустые
                    if body_str == "[]":
                        message = '{"error": "Parameter \\"numbers\\" cannot be empty"}'
                        await send_response(400, message)
                        return

                    # Обработка JSON из тела запроса
                    if body_str.startswith("[") and body_str.endswith("]"):
                        numbers_str = body_str[1:-1].strip()
                        if numbers_str:
                            for num_str in numbers_str.split(","):
                                num_clean = num_str.strip()
                                if num_clean:
                                    numbers_list.append(float(num_clean))

                # Проверка query_params, если данных нет в теле запроса
                else:

                    # Проверка наличия параметра numbers
                    if "numbers" not in query_params:
                        message = '{"error": "Parameter \\"numbers\\" is required"}'
                        await send_response(422, message)
                        return

                    numbers_value = query_params["numbers"]

                    # Проверка, что параметр не пустой
                    if not numbers_value:
                        message = '{"error": "Parameter \\"numbers\\" cannot be empty"}'
                        await send_response(400, message)
                        return

                    # Попытка преобразования параметра в список чисел
                    try:
                        numbers_list = numbers_value.replace("%20", "").split(",")
                        numbers_list = [int(float(number)) for number in numbers_list]
                    except ValueError:
                        message = f'{{"error": "Parameter \\"numbers\\" must be a list of integers, got \\"{numbers_value}\\""}}'
                        await send_response(422, message)
                        return

                mean_number = sum(numbers_list) / len(numbers_list)
                result = f'{{"result": {mean_number}}}'
                await send_response(200, result)
                return

            except Exception:
                message = '{"error": "Invalid request"}'
                await send_response(422, message)
                return

        # Обработка запроса favicon.ico
        elif path.startswith("/favicon.ico"):
            message = '{"error": "No Content favicon"}'
            await send_response(204, message)

        # Возвращение ошибки 404, если путь не соответствует ни одному из ожидаемых
        else:
            message = '{"error": "Not found"}'
            await send_response(404, message)
            return

    # Обработка запросов жизненного цикла (startup/shutdown)
    elif scope["type"] == "lifespan":
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return
    else:
        message = '{"error": "Unsupported request type"}'
        await send_response(422, message)
        return


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
