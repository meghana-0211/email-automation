from pydantic import BaseSettings, SecretStr

class Settings(BaseSettings):
    # API Configuration
    API_VERSION: str = "v1"
    DEBUG: bool = False
    API_KEY: SecretStr
    
    # Email Service Providers
    SES_SENDER_EMAIL: str
    AWS_ACCESS_KEY_ID: SecretStr
    AWS_SECRET_ACCESS_KEY: SecretStr
    AWS_REGION: str = "us-east-1"
    
    # OAuth2 Configuration
    GOOGLE_CLIENT_ID: SecretStr
    GOOGLE_CLIENT_SECRET: SecretStr
    OAUTH_REDIRECT_URI: str
    
    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379"
    
    # Firebase Configuration
    FIREBASE_CREDENTIALS_PATH: str
    
    # Groq Configuration
    GROQ_API_KEY: SecretStr
    
    # Rate Limiting
    RATE_LIMIT_EMAILS_PER_HOUR: int = 1000
    RATE_LIMIT_API_REQUESTS: int = 100
    
    class Config:
        env_file = ".env"

settings = Settings()