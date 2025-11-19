from datetime import timedelta
from enum import Enum
from functools import cached_property

from pydantic import SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Database(str, Enum):
    EIGEN2 = "eigen2"
    EIGEN8 = "eigen8"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        extra="ignore",
        # `.env.prod` takes priority over `.env`
        env_file=(".env", ".env.prod"),
    )

    DB_USER: str = "postgres"
    DB_PASSWORD: SecretStr = "password"
    DB_NAME: str = "postgres"
    DB_PORT: int = 5432
    DB_HOST: str = "127.0.0.1"

    ALT_DB_USER: str = "postgres"
    ALT_DB_PASSWORD: SecretStr = "password"
    ALT_DB_NAME: str = "postgres"
    ALT_DB_HOST: str = "127.0.0.1"
    ALT_DB_PORT: int = 9541

    TBL_CHANNEL_FIDS: str = "k3l_channel_fids"

    POSTGRES_POOL_SIZE: int = 10
    POSTGRES_TIMEOUT_SECS: int = 60
    GO_EIGENTRUST_URL: str = "http://localhost:8080"
    GO_EIGENTRUST_URL_ALT: str = "http://localhost:9080"
    GO_EIGENTRUST_TIMEOUT_MS: int = 600_000  # 10 mins
    GO_EIGENTRUST_BIND_SRC: str = "/tmp"
    GO_EIGENTRUST_BIND_TARGET: str = "/tmp"
    GO_EIGENTRUST_FILE_MODE: bool = False
    EIGENTRUST_ALPHA: float = 0.5
    EIGENTRUST_EPSILON: float = 1.0
    EIGENTRUST_MAX_ITER: int = 50
    EIGENTRUST_FLAT_TAIL: int = 2

    FRAMES_NAP_SECS: int = 10
    FRAMES_SLEEP_SECS: int = 300
    FRAMES_BATCH_SIZE: int = 1_000
    FRAMES_SCRAPE_CONCURRENCY: int = 10
    FRAMES_SCRAPE_CONNECT_TIMEOUT_SECS: int = 5
    FRAMES_SCRAPE_READ_TIMEOUT_SECS: int = 10

    CASTS_SLEEP_SECS: int = 10
    CASTS_BATCH_INTERVAL_HRS: int = 1  # Deprecated. Remove in future update.
    CASTS_BATCH_LIMIT: int = 100_000

    WARPCAST_CHANNELS_TIMEOUT: int = 5  # Deprecated. Remove in future update.
    WARPCAST_PARALLEL_REQUESTS: int = 10
    WARPCAST_CHANNELS_TIMEOUT_SECS: int = 5
    WARPCAST_SLEEP_SECS: float = 1.0
    DAEMON_SLEEP_SECS: int = 300
    CHANNEL_SLEEP_SECS: int = 1

    PERSONAL_IGRAPH_INPUT: str
    PERSONAL_IGRAPH_URL: str

    USE_NEYNAR: bool = True  # Deprecated. Remove in future update.
    # We don't have a test env, so control is in the code
    IS_TEST: bool = False
    TEST_CURSOR_LIMIT: int = 2
    TEST_CHANNEL_LIMIT: int = 2

    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "[%(asctime)s - %(levelname)s - %(filename)s:%(lineno)s - %(funcName)s ] %(message)s"
    LOGURU_FORMAT: str = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green>"
        " | {name}:{function}:{line}"
        " | {level} | <level>{message}</level>"
    )
    LOG_PATH: str = "/tmp/"

    # useful only if source db and destination db are different
    # ... for example, globaltrust calculation can read from replica and write to the primary
    REMOTE_DB_USER: str = "postgres"
    REMOTE_DB_PASSWORD: SecretStr = "password"
    REMOTE_DB_NAME: str = "postgres"
    REMOTE_DB_HOST: str = "127.0.0.1"
    REMOTE_DB_PORT: int = 9541

    ALT_REMOTE_DB_USER: str = "postgres"
    ALT_REMOTE_DB_PASSWORD: SecretStr = "password"
    ALT_REMOTE_DB_NAME: str = "postgres"
    ALT_REMOTE_DB_HOST: str = "127.0.0.1"
    ALT_REMOTE_DB_PORT: int = 9541

    SANDBOX_DB_USER: str = "postgres"
    SANDBOX_DB_PASSWORD: SecretStr = "password"
    SANDBOX_DB_NAME: str = "postgres"
    SANDBOX_DB_HOST: str = "172.17.0.1"  # docker tunnel binding ip
    SANDBOX_DB_PORT: int = 9541
    SANDBOX_REMOTE_HOST: str = "changeme.elb.us-east-1.amazonaws.com"
    SANDBOX_REMOTE_PORT: int = 5432
    SANDBOX_REMOTE_USER: str = "openrank"

    AIRFLOW_UID: int
    AIRFLOW_GID: int
    AIRFLOW__CORE__FERNET_KEY: str

    DUNE_API_KEY: str = "changeme"

    CURA_SCMGR_URL: str = "changeme"
    CURA_SCMGR_USERNAME: str = "changeme"
    CURA_SCMGR_PASSWORD: SecretStr = "changeme"
    CURA_SCMGR_READ_TIMEOUT_SECS: float = 180.0
    CURA_SCMGR_CONNECT_TIMEOUT_SECS: float = 5.0
    CURA_SCMGR_BATCH_SIZE: int = 250

    FID_BATCH_SIZE: int = 250

    CURA_FE_API_URL: str = "changeme"
    CURA_FE_API_KEY: str = "changeme"
    CURA_NOTIFY_CHUNK_SIZE: int = 100

    FCGRAPH_API_URL: str = "https://graph.cast.k3l.io"

    SUPABASE_URL: str = "changeme"
    SUPABASE_SERVICE_ROLE_KEY: SecretStr = "changeme"
    SUPABASE_DB_HOST: str
    SUPABASE_DB_PORT: int = 5432
    SUPABASE_DB_USER: str = "postgres"
    SUPABASE_DB_PASSWORD: SecretStr
    SUPABASE_DB_NAME: str = "postgres"

    FCM_WEBHOOK_URL: str = "https://api.neynar.com/v2/farcaster/webhook/"
    FCM_WEBHOOK_TIMEOUT_SECS: int = 30
    NEYNAR_API_KEY: str = "changeme"

    CURA_TOKEN_DISTRIBUTION_WALLET_PRIVATE_KEY: SecretStr

    # Web3/Blockchain configuration for token distribution, keyed by chain ID
    # (default: use public RPCs from chain_index)
    ETH_RPC_URLS: dict[int, str] = {}

    # Transaction confirmation timeout and retry interval
    TX_CONFIRMATION_TIMEOUT: timedelta = timedelta(minutes=10)
    TX_CONFIRMATION_INTERVAL: timedelta = timedelta(seconds=5)

    # Token metadata fetching configuration
    TOKEN_QUERY_BATCH_SIZE: int = 100  # Number of tokens to query per batch
    RPC_RATE_LIMIT_DELAY: float = (
        0.1  # Delay in seconds between individual RPC calls to avoid 429 errors
    )

    # Multicall3 addresses - default for most chains
    # Override with MULTICALL3_ADDRESS_{chain_id} environment variable
    MULTICALL3_ADDRESS_DEFAULT: str = "0xcA11bde05977b3631167028862bE2a173976CA11"

    # Per-chain Multicall3 address overrides (if needed)
    # Example: MULTICALL3_ADDRESS_1: str = "0x..."

    def get_multicall3_address(self, chain_id: int) -> str:
        """Get Multicall3 address for a specific chain, with fallback to default."""
        import os

        # First check for chain-specific override in environment
        env_var = f"MULTICALL3_ADDRESS_{chain_id}"
        if env_var in os.environ:
            return os.environ[env_var]
        # Check if we have it as an attribute (from .env file)
        if hasattr(self, env_var):
            return getattr(self, env_var)
        # Fall back to default
        return self.MULTICALL3_ADDRESS_DEFAULT

    @computed_field
    @cached_property
    def POSTGRES_TIMEOUT_MS(self) -> int:
        return self.POSTGRES_TIMEOUT_SECS * 1000

    @computed_field
    @cached_property
    def PERSONAL_IGRAPH_URLPATH(self) -> str:
        return f"{self.PERSONAL_IGRAPH_URL}/graph"

    @computed_field
    def POSTGRES_DSN(self) -> SecretStr:
        return SecretStr(
            f" dbname={self.DB_NAME}"
            f" user={self.DB_USER}"
            f" host={self.DB_HOST}"
            f" port={self.DB_PORT}"
            f" password={self.DB_PASSWORD.get_secret_value()}"
        )

    @computed_field
    def ALT_POSTGRES_DSN(self) -> SecretStr:
        return SecretStr(
            f" dbname={self.ALT_DB_NAME}"
            f" user={self.ALT_DB_USER}"
            f" host={self.ALT_DB_HOST}"
            f" port={self.ALT_DB_PORT}"
            f" password={self.ALT_DB_PASSWORD.get_secret_value()}"
        )

    @computed_field
    def POSTGRES_URL(self) -> SecretStr:
        return SecretStr(
            f"postgresql+psycopg2://"
            f"{self.DB_USER}:{self.DB_PASSWORD.get_secret_value()}@"
            f"{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @computed_field
    def ALT_POSTGRES_URL(self) -> SecretStr:
        return SecretStr(
            f"postgresql+psycopg2://"
            f"{self.ALT_DB_USER}:{self.ALT_DB_PASSWORD.get_secret_value()}@"
            f"{self.ALT_DB_HOST}:{self.ALT_DB_PORT}/{self.ALT_DB_NAME}"
        )

    @computed_field
    def POSTGRES_ASYNC_URI(self) -> SecretStr:
        return SecretStr(
            f"postgresql://{self.DB_USER}:{self.DB_PASSWORD.get_secret_value()}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            f"?random_page_cost=1.1"
        )

    @computed_field
    def ALT_POSTGRES_ASYNC_URI(self) -> SecretStr:
        return SecretStr(
            f"postgresql://{self.ALT_DB_USER}:{self.ALT_DB_PASSWORD.get_secret_value()}"
            f"@{self.ALT_DB_HOST}:{self.ALT_DB_PORT}/{self.ALT_DB_NAME}"
            f"?random_page_cost=1.1"
        )


class OpenRankSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="OPENRANK_", env_file=(".env", ".env.prod"), extra="ignore"
    )
    CHAIN_RPC_URL: str
    MANAGER_ADDRESS: str

    # Vault configuration for secure mnemonic retrieval
    # OPENRANK_VAULT_URL: URL to your OpenBao/Vault instance (e.g., "https://vault.example.com")
    # OPENRANK_VAULT_TOKEN: Authentication token for vault access
    # OPENRANK_VAULT_SECRET_PATH: Path to the secret containing the mnemonic (default: "secret/openrank/mnemonic")
    # The secret should contain a key named "mnemonic" with the private key value
    VAULT_URL: str
    VAULT_TOKEN: SecretStr
    VAULT_SECRET_PATH: str = "openrank/mnemonic"

    TIMEOUT_SECS: int = 300
    REQ_IDS_FILENAME: str = "request_ids.csv"
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str


settings = Settings()
