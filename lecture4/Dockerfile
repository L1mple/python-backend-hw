FROM golang:1.24-alpine AS builder

WORKDIR /app

COPY go.mod ./
RUN go mod download

COPY . .

RUN go run github.com/sqlc-dev/sqlc/cmd/sqlc@latest generate

RUN go run github.com/swaggo/swag/cmd/swag@latest init -g cmd/app/main.go

RUN go mod tidy

RUN CGO_ENABLED=0 GOOS=linux go build -o main ./cmd/app

FROM alpine:latest

WORKDIR /app

RUN apk --no-cache add ca-certificates

COPY --from=builder /app/main .

EXPOSE 8080

CMD ["./main"]

