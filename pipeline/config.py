from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import computed_field, SecretStr

class Settings(BaseSettings):  
    DB_USER:str = 'replicator'
    DB_PASSWORD:SecretStr
    DB_NAME:str = 'replicator'
    DB_PORT:int = 5432
    DB_HOST:str = '127.0.0.1'
    POSTGRES_TIMEOUT_SECS: int = 60
    GO_EIGENTRUST_URL:str = 'http://localhost:8080'
    GO_EIGENTRUST_TIMEOUT_MS:int = 600000 # 10 mins
    EIGENTRUST_ALPHA:float = 0.5
    EIGENTRUST_EPSILON:float = 1.0
    EIGENTRUST_MAX_ITER:int = 50
    EIGENTRUST_FLAT_TAIL:int = 2

    LOG_LEVEL: str = 'INFO'
    LOG_FORMAT: str = '[%(asctime)s - %(levelname)s - %(filename)s:%(lineno)s - %(funcName)s ] %(message)s'
    LOG_PATH: str = '/tmp/'

    model_config = SettingsConfigDict(
        # `.env.prod` takes priority over `.env`
        env_file=('.env', '.env.prod')
    )

    @computed_field
    def POSTGRES_DSN(self) -> SecretStr:
      return SecretStr(f" dbname={self.DB_NAME}"
                       f" user={self.DB_USER}" 
                       f" host={self.DB_HOST}" 
                       f" port={self.DB_PORT}" 
                       f" password={self.DB_PASSWORD.get_secret_value()}")

settings = Settings()
  

