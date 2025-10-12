# gRPC Example

Идейно изначально мы описываем .proto файл 

Затем командой генерим код (для этого нам понадобится библиотечка из requirements.txt), который будет за нас отправлять и принимать такие сообщения:

```sh
python3 -m grpc_tools.protoc \
    --proto_path=./hw2/grpc_example/proto/ \
    --python_out=./hw2/grpc_example \
    --grpc_python_out=./hw2/grpc_example \
    --pyi_out=./hw2/grpc_example \
    ping.proto
```

Затем используя сгенерированный код можно написать свой клиент или сервер, тут уже нвписаны примеры в example_service.py и example_client.py

Чтобы запустить сервис и клиент можно использовать следующие команды:

```sh
python3 -m hw2.grpc_example.example_service
```

```sh
python3 -m hw2.grpc_example.example_client
```
