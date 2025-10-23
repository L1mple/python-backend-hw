from .database import engine
from . import models

# Создаем таблицы при импорте
models.Base.metadata.create_all(bind=engine)
