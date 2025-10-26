# Homework 4

```bash
cd hw4_stepa
docker-compose up database -d

pip install -r requirements.txt

export DATABASE_URL="postgresql://stepa_user:stepa_password@localhost:5433/stepa_shop_db"
uvicorn api.main:app --reload --port 8001

## Тестирование:

chmod +x test_api.sh
./test_api.sh



python3 test_isolation.py
```
