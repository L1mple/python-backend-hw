docker-compose down && docker-compose up --build -d

sleep 30

curl http://localhost:8000/metrics | head -20

for i in {1..5}; do curl http://localhost:8000/cart; done

curl http://localhost:9090/api/v1/query?query=http_server_requests_seconds_count_total
