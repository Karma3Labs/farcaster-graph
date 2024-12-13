from functools import cached_property

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import computed_field, SecretStr

class Settings(BaseSettings):
    DB_USER:str = 'postgres'
    DB_PASSWORD:SecretStr = 'password'
    DB_NAME:str = 'postgres'
    DB_PORT:int = 5432
    DB_HOST:str = '127.0.0.1'

    DB_CHANNEL_FIDS:str = 'k3l_channel_fids'

    POSTGRES_POOL_SIZE: int = 10
    POSTGRES_TIMEOUT_SECS: int = 60
    GO_EIGENTRUST_URL:str = 'http://localhost:8080'
    GO_EIGENTRUST_URL_ALT:str = 'http://localhost:9080'
    GO_EIGENTRUST_TIMEOUT_MS:int = 600_000 # 10 mins
    GO_EIGENTRUST_BIND_SRC:str = '/tmp'
    GO_EIGENTRUST_BIND_TARGET:str = '/tmp'
    GO_EIGENTRUST_FILE_MODE:bool = False
    EIGENTRUST_ALPHA:float = 0.5
    EIGENTRUST_EPSILON:float = 1.0
    EIGENTRUST_MAX_ITER:int = 50
    EIGENTRUST_FLAT_TAIL:int = 2

    OPENRANK_REQ_ADDR:str = 'CHANGEME'
    OPENRANK_REQ_SECRET_KEY:SecretStr = 'CHANGEME'
    OPENRANK_URL:str = 'https://CHANGEME'
    OPENRANK_TIMEOUT_SECS:int = 300
    OPENRANK_REQ_IDS_FILENAME: str = 'request_ids.csv'

    FRAMES_NAP_SECS: int = 10
    FRAMES_SLEEP_SECS: int = 300
    FRAMES_BATCH_SIZE: int = 1_000
    FRAMES_SCRAPE_CONCURRENCY: int = 10
    FRAMES_SCRAPE_CONNECT_TIMEOUT_SECS: int = 5
    FRAMES_SCRAPE_READ_TIMEOUT_SECS: int = 10

    CASTS_SLEEP_SECS: int = 10
    CASTS_BATCH_INTERVAL_HRS: int = 1 # Deprecated. Remove in future update.
    CASTS_BATCH_LIMIT:int = 100_000

    
    WARPCAST_CHANNELS_TIMEOUT: int = 5 # Deprecated. Remove in future update.
    WARPCAST_PARALLEL_REQUESTS: int = 10
    WARPCAST_CHANNELS_TIMEOUT_SECS: int = 5
    WARPCAST_SLEEP_SECS:float = 1.0
    DAEMON_SLEEP_SECS: int = 300
    CHANNEL_SLEEP_SECS:int = 1

    PERSONAL_IGRAPH_INPUT: str
    PERSONAL_IGRAPH_URL: str

    USE_NEYNAR:bool = True # Deprecated. Remove in future update.
    IS_TEST: bool = False
    TEST_CURSOR_LIMIT: int = 2
    TEST_CHANNEL_LIMIT: int = 2

    LOG_LEVEL: str = 'INFO'
    LOG_FORMAT: str = '[%(asctime)s - %(levelname)s - %(filename)s:%(lineno)s - %(funcName)s ] %(message)s'
    LOGURU_FORMAT: str = ("<green>{time:YYYY-MM-DD HH:mm:ss}</green>"
                            " | {name}:{function}:{line}"
                            " | {level} | <level>{message}</level>" )
    LOG_PATH: str = '/tmp/'

    REMOTE_DB_USER:str = 'postgres'
    REMOTE_DB_PASSWORD:SecretStr = 'password'
    REMOTE_DB_NAME:str = 'postgres'
    REMOTE_DB_HOST:str = '127.0.0.1'
    REMOTE_DB_PORT:int = 9541
    
    SANDBOX_DB_USER:str = 'postgres'
    SANDBOX_DB_PASSWORD:SecretStr = 'password'
    SANDBOX_DB_NAME:str = 'postgres'
    SANDBOX_DB_HOST:str = '172.17.0.1' # docker tunnel binding ip
    SANDBOX_DB_PORT:int = 9541
    SANDBOX_REMOTE_HOST:str = 'changeme.elb.us-east-1.amazonaws.com'
    SANDBOX_REMOTE_PORT:int = 5432
    SANDBOX_REMOTE_USER: str = 'openrank'

    AIRFLOW_UID: int
    AIRFLOW_GID: int
    AIRFLOW__CORE__FERNET_KEY: str
    SSH_KEY_PATH: str = 'changeme'
    SSH_LISTEN_PORT: int = 9599
    SSH_LISTEN_HOST: str = '127.0.0.1'

    DUNE_API_KEY: str = 'changeme'

    CURA_SCMGR_URL: str = 'changeme'
    CURA_SCMGR_API_KEY: SecretStr = 'changeme'

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

    @computed_field
    def POSTGRES_ASYNC_URI(self) -> SecretStr:
        return SecretStr(f"postgresql://{self.DB_USER}:{self.DB_PASSWORD.get_secret_value()}"\
                         f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"\
                            f"?random_page_cost=1.1")

settings = Settings()


