import os
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    mongodb_url: str = "mongodb://localhost:27017"
    database_name: str = "doctor_clinic"
    
    # JWT
    jwt_secret_key: str = "your_jwt_secret_key_here_change_this_in_production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 1440 * 30*6  # 24 hours
    gimini_api_key: str = "your_gemini_api_key_here"
    
    # CORS
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    
    def get_cors_origins(self) -> List[str]:
        return self.cors_origins.split(",")
    
    class Config:
        env_file = ".env"

settings = Settings() 