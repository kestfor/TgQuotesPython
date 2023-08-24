from pydantic import BaseSettings, SecretStr


class Settings(BaseSettings):

    bot_token: SecretStr
    user: SecretStr
    password: SecretStr
    host: SecretStr
    database: SecretStr
    raise_on_warnings: bool

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


config = Settings()
