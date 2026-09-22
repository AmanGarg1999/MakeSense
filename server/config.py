from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    database_url: str = "postgresql://makesense:makesense_dev@localhost:5432/makesense"
    gemini_api_key: Optional[str] = None
    llm_provider: str = "runanywhere"
    runanywhere_endpoint: str = "http://172.17.0.1:8000/v1"
    runanywhere_model: str = "qwen2.5:3b"
    secret_key: str = "change-me-in-production"
    cors_origins: str = "http://localhost:8090,http://localhost:8000,http://localhost:5173"
    
    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
