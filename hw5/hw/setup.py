from setuptools import setup, find_packages

setup(
    name="shop_api",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.104.0",
        "sqlalchemy>=2.0.0", 
        "psycopg2-binary>=2.9.0",
        "pydantic>=2.5.0",
    ],
)