print("""
PostgreSQL не поддерживает уровень READ UNCOMMITTED. Любая попытка
установить его сводится к READ COMMITTED, поэтому dirty read невозможен.
""")
