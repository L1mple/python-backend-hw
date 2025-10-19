FROM python:3.11-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy only needed parts
# Copy package root so import path is `hw.shop_api.main`
COPY hw2/hw /app/hw
COPY lecture3/requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir -r /app/requirements.txt uvicorn fastapi

# Healthcheck deps
RUN python - <<'PY'
import pkgutil
import sys
missing = [m for m in ["sqlalchemy","psycopg2"] if not pkgutil.find_loader(m)]
assert not missing, f"Missing packages: {missing}"
PY

EXPOSE 8000

CMD ["uvicorn", "hw.shop_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
