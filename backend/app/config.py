from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # API and Basic Config
    API_VERSION: str = "1.0.0"
    REDIS_URL: str = "redis://localhost:6379"
    GROQ_API_KEY: str = ""
    
    # AWS Configuration
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = ""
    SES_SENDER_EMAIL: str = ""
    SES_CONFIGURATION_SET: str = ""
    
    # Google Sheets API
    GOOGLE_SHEETS_CREDENTIALS_PATH: str = "credentials.json"
    
    # Firebase
    FIREBASE_CREDENTIALS_PATH: str = "firebase-key.json"
    
    # Rate Limiting Settings
    RATE_LIMIT_EMAILS_PER_HOUR: int = 100
    MAX_BATCH_SIZE: int = 1000
    CONCURRENT_LIMIT: int = 5
    
    class Config:
        env_file = ".env"

settings = Settings()