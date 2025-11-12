from typing import Any, Awaitable, Callable
import json
import math
from urllib.parse import parse_qs


async def application(
    scope: dict[str, Any],
    receive: Callable[[], Awaitable[dict[str, Any]]],
    send: Callable[[dict[str, Any]], Awaitable[None]],
):

    if scope["type"] != "http":
        await send(
            {
                "type": "http.response.start",
                "status": 422,
                "headers": [(b"content-type", b"application/json")],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": json.dumps({"error": "Unsupported scope type"}).encode(),
            }
        )
        return

    path = scope["path"]
    query_string = scope.get("query_string", b"").decode()
    query_params = parse_qs(query_string)

    status = 200
    response = {}

    try:
        if path.startswith("/fibonacci/"):
            part = path.removeprefix("/fibonacci/")
            try:
                n = int(part)
            except ValueError:
                status = 422
                response = {"error": "Invalid format for n"}
            else:
                if n < 0:
                    status = 400
                    response = {"error": "n must be non-negative"}
                else:
                    fib = [0, 1]
                    for i in range(2, n + 1):
                        fib.append(fib[-1] + fib[-2])
                    response = {"result": fib[n] if n >= 0 else 0}

        elif path == "/factorial":
            n_str = query_params.get("n", [None])[0]

            if n_str is None or n_str == "":
                status = 422
                response = {"error": "Missing or empty parameter n"}
            else:
                try:
                    n = int(n_str)
                except ValueError:
                    status = 422
                    response = {"error": "Invalid format for n"}
                else:
                    if n < 0:
                        status = 400
                        response = {"error": "n must be non-negative"}
                    else:
                        response = {"result": math.factorial(n)}
        elif path == "/mean":
            numbers = None

            event = await receive()
            if event.get("type") == "http.request" and event.get("body"):
                try:
                    numbers = json.loads(event["body"])
                except json.JSONDecodeError:
                    numbers = None

            if numbers is None:
                try:
                    numbers_str = query_params.get("numbers", [None])[0]
                    if numbers_str is not None:
                        numbers = [float(x) for x in numbers_str.split(",")]
                except Exception:
                    numbers = None

            if numbers is None:
                status = 422
                response = {"error": "Missing or invalid body"}
            elif not numbers:
                status = 400
                response = {"error": "Empty list"}
            else:
                try:
                    nums = [float(x) for x in numbers]
                    response = {"result": sum(nums) / len(nums)}
                except Exception:
                    status = 400
                    response = {"error": "Invalid numbers"}

        else:
            status = 404
            response = {"error": "Not found"}

    except Exception as e:
        status = 500
        response = {"error": str(e)}

    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [(b"content-type", b"application/json")],
        }
    )
    await send(
        {
            "type": "http.response.body",
            "body": json.dumps(response).encode("utf-8"),
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
