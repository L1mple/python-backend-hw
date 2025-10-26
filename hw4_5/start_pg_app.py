import uvicorn

from src.config import settings



if __name__ == "__main__":
    uvicorn.run(
        app="src.main:pg_app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False
    )