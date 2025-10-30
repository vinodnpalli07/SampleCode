"""Application configuration using environment variables."""

from functools import lru_cache
from pydantic import BaseModel, Field


class BambooConfig(BaseModel):
    base_url: str = Field(..., description="Base URL for the Bamboo instance")
    username: str | None = Field(default=None, description="Username for Bamboo basic auth")
    password: str | None = Field(default=None, description="Password or API token for Bamboo basic auth")
    personal_access_token: str | None = Field(
        default=None, description="Personal access token for Bamboo REST API"
    )


class MongoConfig(BaseModel):
    uri: str = Field(..., description="MongoDB connection URI")
    database: str = Field(..., description="Database name for storing test run data")


class AppConfig(BaseModel):
    environment: str = Field(default="development", description="Runtime environment name")
    mongo: MongoConfig
    bamboo: BambooConfig
    dashboard_secret: str | None = Field(
        default=None,
        description="Optional shared secret to protect dashboard endpoints",
    )


@lru_cache
def get_settings() -> AppConfig:
    """Load application settings from environment variables."""

    from pydantic_settings import BaseSettings

    class Settings(BaseSettings):
        environment: str = "development"
        mongo_uri: str
        mongo_database: str
        bamboo_base_url: str
        bamboo_username: str | None = None
        bamboo_password: str | None = None
        bamboo_pat: str | None = None
        dashboard_secret: str | None = None

        class Config:
            env_file = ".env"

    raw = Settings()
    return AppConfig(
        environment=raw.environment,
        mongo=MongoConfig(uri=raw.mongo_uri, database=raw.mongo_database),
        bamboo=BambooConfig(
            base_url=raw.bamboo_base_url,
            username=raw.bamboo_username,
            password=raw.bamboo_password,
            personal_access_token=raw.bamboo_pat,
        ),
        dashboard_secret=raw.dashboard_secret,
    )

