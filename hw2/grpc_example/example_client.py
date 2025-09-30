import grpc

import hw2.grpc_example.ping_pb2 as pb2
import hw2.grpc_example.ping_pb2_grpc as pb2_grpc


def message_from_input_generator():
    while True:
        message = input()

        if not message:
            return

        yield pb2.PingRequest(message=message)


if __name__ == "__main__":
    with grpc.insecure_channel("localhost:50051") as channel:
        stub = pb2_grpc.ExampleStub(channel)

        response = stub.Ping(pb2.PingRequest(message="message lol"))
        print(response)

        for response in stub.PingStream(message_from_input_generator()):
            print(response)
