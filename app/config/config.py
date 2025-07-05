import os
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    mongodb_url: str  
    database_name: str
    
    # JWT
    jwt_secret_key: str 
    jwt_algorithm: str
    jwt_access_token_expire_minutes: int = 1440 * 30*6  # 24 hours
    gimini_api_key: str
    # CORS
    cors_origins: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    class Config:
        env_file = ".env"

settings = Settings() 