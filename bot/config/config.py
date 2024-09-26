from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

    API_ID: int
    API_HASH: str

    RANDOM_SLEEP: list[int] = [10, 15]
    RANDOM_LONG_SLEEP: list[int] = [1*60*60, 3*60*60]

    SLEEP_EMULATION: bool = True
    USE_PROXY_FROM_FILE: bool = False


settings = Settings()
