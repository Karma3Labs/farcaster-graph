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
    GO_EIGENTRUST_URL:str = 'http://localhost:8080'
    EIGENTRUST_ALPHA:float = 0.5
    EIGENTRUST_EPSILON:float = 1.0
    EIGENTRUST_MAX_ITER:int = 50
    EIGENTRUST_FLAT_TAIL:int = 2

    LOG_LEVEL: str = 'INFO'

    FOLLOW_GRAPH_PATHPREFIX: str = '/tmp/fc_following'
    ENGAGEMENT_GRAPH_PATHPREFIX: str = '/tmp/fc_engagement'
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