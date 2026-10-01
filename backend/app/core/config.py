from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Project Stardust"
    VERSION: str = "0.1.0"
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    DATABASE_URL: str = "postgresql://stardust:stardust_password@localhost:5432/stardust_db"
    REDIS_URL: str = "redis://localhost:6379/0"
    FIRMS_MAP_KEY: str = ""

settings = Settings()
