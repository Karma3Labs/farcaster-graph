from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import computed_field, SecretStr


class Settings(BaseSettings):
    DB_USERNAME: str = "postgres"
    DB_PASSWORD: SecretStr = "postgres"
    DB_NAME: str = "postgres"
    DB_PORT: int = 5432
    DB_HOST: str = "127.0.0.1"
    POSTGRES_POOL_SIZE: int = 5
    POSTGRES_ECHO: bool = False
    POSTGRES_TIMEOUT_SECS: int = 60

    CACHE_DB_ENABLED: bool = False
    CACHE_DB_USERNAME: str = "postgres"
    CACHE_DB_PASSWORD: SecretStr = "postgres"
    CACHE_DB_NAME: str = "postgres"
    CACHE_DB_PORT: int = 5432
    CACHE_DB_HOST: str = "127.0.0.1"
    CACHE_POSTGRES_POOL_SIZE: int = 5
    CACHE_POSTGRES_ECHO: bool = False
    CACHE_POSTGRES_TIMEOUT_SECS: int = 60

    GO_EIGENTRUST_URL: str = "http://localhost:8080"
    GO_EIGENTRUST_TIMEOUT_MS: int = 3000
    EIGENTRUST_ALPHA: float = 0.5
    EIGENTRUST_EPSILON: float = 1.0
    EIGENTRUST_MAX_ITER: int = 50
    EIGENTRUST_FLAT_TAIL: int = 2

    FEED_TIMEOUT_SECS: int = 30

    CURA_SCMGR_URL: str = "changeme"
    CURA_SCMGR_USERNAME: str = "changeme"
    CURA_SCMGR_PASSWORD: SecretStr = "changeme"

    MAX_CHANNELS_PER_USER: int = 50

    USE_PANDAS_PERF: bool
    LOG_LEVEL: str = "INFO"
    LOG_LEVEL_CORE: str = "DEBUG"
    LOGURU_FORMAT: str = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green>"
        " | {name}:{function}:{line} [{correlation_id}]"
        " | {level} | <level>{message}</level>"
    )
    SWAGGER_BASE_URL: str

    FOLLOW_GRAPH_PATHPREFIX: str = "/tmp/fc_following_fid"
    ENGAGEMENT_GRAPH_PATHPREFIX: str = "/tmp/fc_engagement_fid"
    NINETYDAYS_GRAPH_PATHPREFIX: str = "/tmp/fc_90dv3_fid"
    RELOAD_FREQ_SECS: int = 3600
    PAUSE_BEFORE_RELOAD_SECS: int = 300

    CURA_API_ENDPOINT: str = "https://cura.network/api"
    CURA_API_KEY: str


    model_config = SettingsConfigDict(
        # `.env.prod` takes priority over `.env`
        env_file=(".env", ".env.prod")
    )

    @computed_field
    def POSTGRES_URI(self) -> SecretStr:
        return SecretStr(
            f"postgresql://{self.DB_USERNAME}:{self.DB_PASSWORD.get_secret_value()}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            f"?random_page_cost=1.1"
        )

    @computed_field
    def POSTGRES_ASYNC_URI(self) -> SecretStr:
        return SecretStr(
            f"postgresql+asyncpg://{self.DB_USERNAME}:{self.DB_PASSWORD.get_secret_value()}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            f"?random_page_cost=1.1"
        )

    @computed_field
    def CACHE_POSTGRES_URI(self) -> SecretStr:
        return SecretStr(
            f"postgresql://{self.CACHE_DB_USERNAME}:{self.CACHE_DB_PASSWORD.get_secret_value()}"
            f"@{self.CACHE_DB_HOST}:{self.CACHE_DB_PORT}/{self.CACHE_DB_NAME}"
            f"?random_page_cost=1.1"
        )

    @computed_field
    def CACHE_POSTGRES_ASYNC_URI(self) -> SecretStr:
        return SecretStr(
            f"postgresql+asyncpg://{self.CACHE_DB_USERNAME}:{self.CACHE_DB_PASSWORD.get_secret_value()}"
            f"@{self.CACHE_DB_HOST}:{self.CACHE_DB_PORT}/{self.CACHE_DB_NAME}"
            f"?random_page_cost=1.1"
        )


settings = Settings()
