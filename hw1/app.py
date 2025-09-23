from typing import Any, Awaitable, Callable
import json
import math
from urllib.parse import parse_qs

async def application(
    scope: dict[str, Any],
    receive: Callable[[], Awaitable[dict[str, Any]]],
    send: Callable[[dict[str, Any]], Awaitable[None]],
):


    async def send_json(status: int, payload: dict[str, Any]) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [(b"content-type", b"application/json; charset=utf-8")],
            }
        )
        await send({"type": "http.response.body", "body": json.dumps(payload).encode()})

    path: str = scope.get("path", "")
    method: str = scope.get("method", "GET")

    # Разрешаем только GET на известных ручках
    if method != "GET":
        await send_json(404, {"detail": "Not Found"})
        return

    #/factorial?n=INT
    if path == "/factorial":
        # Валидация query
        qs = parse_qs(scope.get("query_string", b"").decode())
        if "n" not in qs or len(qs["n"]) == 0 or qs["n"][0].strip() == "":
            await send_json(422, {"detail": "Query parameter 'n' is required"})
            return
        try:
            n = int(qs["n"][0])
        except Exception:
            await send_json(422, {"detail": "Parameter 'n' must be integer"})
            return
        if n < 0:
            await send_json(400, {"detail": "n must be >= 0"})
            return

        # Вычисление факториала
        result = 1
        for i in range(2, n + 1):
            result *= i
        await send_json(200, {"result": result})
        return

    #/fibonacci/<n>
    if path.startswith("/fibonacci"):
        parts = path.split("/")
        if len(parts) < 3 or parts[2] == "":
            await send_json(422, {"detail": "Path parameter 'n' is required"})
            return
        try:
            n = int(parts[2])
        except Exception:
            await send_json(422, {"detail": "Path parameter 'n' must be integer"})
            return
        if n < 0:
            await send_json(400, {"detail": "n must be >= 0"})
            return

        # Вычисление числа Фибоначчи
        if n == 0:
            fib = 0
        else:
            a, b = 0, 1
            for _ in range(1, n):
                a, b = b, a + b
            fib = b
        await send_json(200, {"result": fib})
        return

    # /mean  (GET с JSON-массивом чисел в теле)
    if path == "/mean":
        # Считываем тело (может приходить частями)
        body = b""
        more = True
        while more:
            message = await receive()
            if message.get("type") == "http.request":
                body += message.get("body", b"")
                more = message.get("more_body", False)
            else:
                more = False

        if not body:
            await send_json(422, {"detail": "JSON body is required"})
            return
        try:
            data = json.loads(body.decode() or "null")
        except Exception:
            await send_json(422, {"detail": "Body must be valid JSON"})
            return
        if not isinstance(data, list):
            await send_json(422, {"detail": "Body must be a JSON array"})
            return
        if len(data) == 0:
            await send_json(400, {"detail": "Array must be non-empty"})
            return
        # Валидация элементов
        nums: list[float] = []
        for x in data:
            if isinstance(x, (int, float)):
                nums.append(float(x))
            else:
                await send_json(422, {"detail": "Array must contain only numbers"})
                return

        await send_json(200, {"result": sum(nums) / len(nums)})
        return

    # Неизвестные пути
    await send_json(404, {"detail": "Not Found"})



if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
