from sys import argv


def parse_qs(query_string):
    # это код который я взял из реализации 1-го ДЗ одного из студентов
    return dict(param.split("=") for param in query_string.split("&") if "=" in param)


if __name__ == "__main__":
    query_string = argv[1]
    print(parse_qs(query_string))
