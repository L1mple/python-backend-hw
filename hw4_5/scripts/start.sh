#! bin/bash
PYTHONPATH=. alembic upgrade head
python start_pg_app.py