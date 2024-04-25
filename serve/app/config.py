from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import computed_field, SecretStr

class Settings(BaseSettings):
    DB_USERNAME:str = 'postgres'
    DB_PASSWORD:SecretStr = 'postgres'
    DB_NAME:str = 'postgres'
    DB_PORT:int = 5432
    DB_HOST:str = '127.0.0.1'
    POSTGRES_POOL_SIZE: int = 5
    POSTGRES_ECHO: bool = False
    POSTGRES_TIMEOUT_SECS: int = 60
    GO_EIGENTRUST_URL:str = 'http://localhost:8080'
    GO_EIGENTRUST_TIMEOUT_MS:int = 3000
    EIGENTRUST_ALPHA:float = 0.5
    EIGENTRUST_EPSILON:float = 1.0
    EIGENTRUST_MAX_ITER:int = 50
    EIGENTRUST_FLAT_TAIL:int = 2

    WARPCAST_CHANNELS_TIMEOUT: int = 30000

    LOG_LEVEL: str = 'INFO'
    LOGURU_FORMAT: str = '<green>{time:YYYY-MM-DD HH:mm:ss}</green> | {module}:{file}:{function}:{line} | {level} | <level>{message}</level>'
    SWAGGER_BASE_URL: str

    FOLLOW_GRAPH_PATHPREFIX: str = '/tmp/fc_following_fid'
    ENGAGEMENT_GRAPH_PATHPREFIX: str = '/tmp/fc_engagement_fid'
    RELOAD_FREQ_SECS: int = 3600

    model_config = SettingsConfigDict(
        # `.env.prod` takes priority over `.env`
        env_file=('.env', '.env.prod')
    )

    @computed_field
    def POSTGRES_URI(self) -> SecretStr:
        return SecretStr(f"postgresql://{self.DB_USERNAME}:{self.DB_PASSWORD.get_secret_value()}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}")

    @computed_field
    def POSTGRES_ASYNC_URI(self) -> SecretStr:
        return SecretStr(f"postgresql+asyncpg://{self.DB_USERNAME}:{self.DB_PASSWORD.get_secret_value()}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}")

settings = Settings()