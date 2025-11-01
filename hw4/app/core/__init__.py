from motor.motor_asyncio import AsyncIOMotorClient

from app.config import get_settings


class MongoDB:
    def __init__(self, client: AsyncIOMotorClient, db_name: str):
        """
        Create a MongoDB client.
        :param client: The AsyncIOMotorClient to use.
        :param db_name: The name of the database to use.
        """
        self.client = client
        self.mongo = client[db_name]


# Create a singleton MongoDB client
client = AsyncIOMotorClient(get_settings().mongo.url, maxPoolSize=get_settings().mongo.pool_size)
mongo_db = MongoDB(client, get_settings().mongo.db_name)


async def get_mongo() -> MongoDB:
    """
    Dependency for FastAPI to get a MongoDB client.
    This function will be used as a dependency in FastAPI endpoints to get a MongoDB client.
    It returns the singleton MongoDB client created with the specified pool size.
    """
    return mongo_db