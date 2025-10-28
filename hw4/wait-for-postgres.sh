#!/bin/bash
set -e

host="$1"
shift
cmd="$@"

until pg_isready -h "$host" -U "postgres" > /dev/null 2>&1; do
  echo "⏳ Waiting for Postgres ($host)..."
  sleep 1
done

echo "✅ Postgres is ready — starting app..."
exec $cmd
