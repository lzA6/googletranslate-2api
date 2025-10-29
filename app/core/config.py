from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        extra="ignore"
    )

    APP_NAME: str = "googletranslate-2api"
    APP_VERSION: str = "1.0.0"
    DESCRIPTION: str = "一个将 Google Translate API 转换为兼容 OpenAI 格式的代理。"

    API_MASTER_KEY: Optional[str] = None
    NGINX_PORT: int = 8088
    
    GOOGLE_API_KEY: Optional[str] = None

    API_REQUEST_TIMEOUT: int = 60

    DEFAULT_MODEL: str = "google-translate"
    KNOWN_MODELS: List[str] = ["google-translate"]

settings = Settings()
