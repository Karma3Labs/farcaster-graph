from functools import cached_property

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import computed_field, SecretStr

class Settings(BaseSettings):
    DB_USER:str = 'replicator'
    DB_PASSWORD:SecretStr
    DB_NAME:str = 'replicator'
    DB_PORT:int = 5432
    DB_HOST:str = '127.0.0.1'

    DB_TEMP_LOCALTRUST:str = 'tmp_lt'
    DB_LOCALTRUST:str
    DB_TEMP_GLOBALTRUST:str = 'tmp_gt'
    DB_GLOBALTRUST:str
    DB_CHANNEL_FIDS:str

    POSTGRES_TIMEOUT_SECS: int = 60
    GO_EIGENTRUST_URL:str = 'http://localhost:8080'
    GO_EIGENTRUST_TIMEOUT_MS:int = 600_000 # 10 mins
    EIGENTRUST_ALPHA:float = 0.5
    EIGENTRUST_EPSILON:float = 1.0
    EIGENTRUST_MAX_ITER:int = 50
    EIGENTRUST_FLAT_TAIL:int = 2

    FRAMES_NAP_SECS: int = 10
    FRAMES_SLEEP_SECS: int = 300
    FRAMES_BATCH_SIZE: int = 1_000
    FRAMES_SCRAPE_CONCURRENCY: int = 10
    FRAMES_SCRAPE_CONNECT_TIMEOUT_SECS: int = 5
    FRAMES_SCRAPE_READ_TIMEOUT_SECS: int = 10

    CASTS_SLEEP_SECS: int = 10
    CASTS_BATCH_INTERVAL_HRS: int = 1 # Deprecated. Remove in future update.
    CASTS_BATCH_LIMIT:int = 100_000

    WARPCAST_CHANNELS_TIMEOUT: int = 5
    CHANNEL_SLEEP_SECS:int = 1

    PERSONAL_IGRAPH_INPUT: str
    PERSONAL_IGRAPH_URL: str

    USE_NEYNAR: bool = False
    IS_TEST: bool = False

    LOG_LEVEL: str = 'INFO'
    LOG_FORMAT: str = '[%(asctime)s - %(levelname)s - %(filename)s:%(lineno)s - %(funcName)s ] %(message)s'
    LOGURU_FORMAT: str = '<green>{time:YYYY-MM-DD HH:mm:ss}</green> | {module}:{file}:{function}:{line} | {level} | <level>{message}</level>'
    LOG_PATH: str = '/tmp/'

    AIRFLOW_UID: int
    AIRFLOW_GID: int
    REMOTE_DB_HOST: str
    AIRFLOW__CORE__FERNET_KEY: str
    SSH_KEY_PATH: str = 'id_rsa'
    REMOTE_DB_PORT: int = 9541

    DUNE_API_KEY: str = 'repalce_me'

    model_config = SettingsConfigDict(
        # `.env.prod` takes priority over `.env`
        env_file=('.env', '.env.prod')
    )

    @computed_field
    @cached_property
    def PERSONAL_IGRAPH_URLPATH(self) -> str:
       return f"{self.PERSONAL_IGRAPH_URL}/graph"

    @computed_field
    def POSTGRES_DSN(self) -> SecretStr:
      return SecretStr(f" dbname={self.DB_NAME}"
                       f" user={self.DB_USER}"
                       f" host={self.DB_HOST}"
                       f" port={self.DB_PORT}"
                       f" password={self.DB_PASSWORD.get_secret_value()}")

    @computed_field
    def POSTGRES_URL(self) -> SecretStr:
      return SecretStr(f"postgresql+psycopg2://"
                       f"{self.DB_USER}:{self.DB_PASSWORD.get_secret_value()}@"
                       f"{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}")

settings = Settings()


