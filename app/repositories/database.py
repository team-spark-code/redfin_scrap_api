# app/repositories/database.py
from pymongo import MongoClient
from pymongo.database import Database
from app.config import MONGO_URI, MONGO_DB


class MongoManager:
    _client: MongoClient | None = None
    _db: Database | None = None

    @classmethod
    def get_client(cls) -> MongoClient:
        if cls._client is None:
            # connect=False는 포크(fork) 안전성을 위해 설정 (웹 서버 환경 고려)
            cls._client = MongoClient(MONGO_URI, connect=False)
        return cls._client

    @classmethod
    def get_db(cls) -> Database:
        if cls._db is None:
            cls._db = cls.get_client()[MONGO_DB]
        return cls._db

    @classmethod
    def close(cls):
        if cls._client:
            cls._client.close()
            cls._client = None
            cls._db = None

