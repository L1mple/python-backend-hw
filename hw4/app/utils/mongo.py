from loguru import logger

from app.core.mongo import get_mongo

# список коллекций, которые должны быть
REQUIRED_COLLECTIONS = [
    "carts",
    "items",
]


async def init_mongo_collections():
    """
    Проверяет наличие базы и нужных коллекций.
    Создаёт отсутствующие коллекции при запуске FastAPI.
    """
    mongo = await get_mongo()
    db = mongo.mongo

    # Получаем список существующих коллекций
    existing_collections = await db.list_collection_names()

    for name in REQUIRED_COLLECTIONS:
        if name not in existing_collections:
            await db.create_collection(name)
            logger.success(f"Created collection: {name}")
        else:
            logger.info(f"Collection '{name}' already exists")
