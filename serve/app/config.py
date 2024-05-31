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

    PLGRAPH_PATHPREFIX: str = '/tmp/personal_graph'

    LOG_LEVEL: str = 'INFO'
    LOG_LEVEL_CORE: str = 'DEBUG'
    LOGURU_FORMAT: str = ("<green>{time:YYYY-MM-DD HH:mm:ss}</green>"
                            " | {name}:{function}:{line} [{correlation_id}]"
                            " | {level} | <level>{message}</level>" )
    SWAGGER_BASE_URL: str

    RELOAD_FREQ_SECS: int = 3600

    model_config = SettingsConfigDict(
        # `.env.prod` takes priority over `.env`
        env_file=('.env', '.env.prod')
    )

    @computed_field
    def POSTGRES_URI(self) -> SecretStr:
        return SecretStr(f"postgresql://{self.DB_USERNAME}:{self.DB_PASSWORD.get_secret_value()}"\
                         f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"\
                        f"?random_page_cost=1.1")

    @computed_field
    def POSTGRES_ASYNC_URI(self) -> SecretStr:
        return SecretStr(f"postgresql+asyncpg://{self.DB_USERNAME}:{self.DB_PASSWORD.get_secret_value()}"\
                         f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"\
                            f"?random_page_cost=1.1")

settings = Settings()