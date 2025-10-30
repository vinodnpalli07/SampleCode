"""MongoDB client setup and helpers."""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from .config import get_settings


class Database:
    """Singleton-style access to the Mongo database."""

    _client: AsyncIOMotorClient | None = None

    @classmethod
    def get_client(cls) -> AsyncIOMotorClient:
        if cls._client is None:
            cfg = get_settings()
            cls._client = AsyncIOMotorClient(cfg.mongo.uri)
        return cls._client

    @classmethod
    def get_database(cls) -> AsyncIOMotorDatabase:
        cfg = get_settings()
        return cls.get_client()[cfg.mongo.database]

    @classmethod
    async def close(cls) -> None:
        if cls._client is not None:
            cls._client.close()
            cls._client = None

