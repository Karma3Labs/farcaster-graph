from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import computed_field

class Settings(BaseSettings):  
    DB_USERNAME:str = 'postgres'
    DB_PASSWORD:str = 'postgres'
    DB_NAME:str = 'postgres'
    DB_PORT:int = 5432
    DB_HOST:str = '127.0.0.1'
    POSTGRES_POOL_SIZE: int = 5
    POSTGRES_ECHO: bool = False
    POSTGRES_TIMEOUT_SECS: int = 60

    LOG_LEVEL: str = 'INFO'

    FOLLOW_GRAPH: str = ''
    ENGAGEMENT_GRAPH: str = ''
    RELOAD_FREQ_SECS: int = 3600

    model_config = SettingsConfigDict(
        # `.env.prod` takes priority over `.env`
        env_file=('.env', '.env.prod')
    )

    @computed_field
    def POSTGRES_URI(self) -> str:
        return f"postgresql://{self.DB_USERNAME}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @computed_field
    def POSTGRES_ASYNC_URI(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USERNAME}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

settings = Settings()