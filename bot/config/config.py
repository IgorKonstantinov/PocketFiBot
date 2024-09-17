from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

    API_ID: int
    API_HASH: str

    RANDOM_SLEEP: list[int] = [10, 15]
    RANDOM_LONG_SLEEP: list[int] = [60*30, 60*60]

    USE_PROXY_FROM_FILE: bool = False


settings = Settings()
