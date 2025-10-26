import json


def is_digit(
        str_num: str
) -> bool:
    if str_num.startswith("-"):
        str_num = str_num[1:]

    return str_num.isdigit()


def check_request_valid(
        method: str,
        path: str
) -> bool:
    return method == "GET" and path in ["/factorial", "/fibonacci", "/mean"]


def create_start_message(
        status_code: int = 200
) -> dict:
    return {
        'type': 'http.response.start',
        'status': status_code,
        'headers': [
            (b'content-type', b'text/plain'),
        ]
    }


def create_message(
        body: str
) -> dict:
    return {
        'type': 'http.response.body',
        'body': json.dumps(body).encode("utf-8"),
    }
