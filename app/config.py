from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PLANETS_")

    app_name: str = "Solar System Emulator API"
    debug: bool = False


settings = Settings()
