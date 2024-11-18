import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings:
    # AWS Settings
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')  # Default to us-east-1

    FIREBASE_CREDENTIALS_PATH = os.getenv('FIREBASE_CREDENTIALS_PATH')

    REDIS_URL = os.getenv('REDIS_URL')

    # SES Settings
    SES_SENDER_EMAIL = os.getenv('SES_SENDER_EMAIL')
    SES_CONFIGURATION_SET = os.getenv('SES_CONFIGURATION_SET')

    # Groq Settings
    GROQ_API_KEY = os.getenv('GROQ_API_KEY')

    GOOGLE_SHEETS_CREDENTIALS_PATH = os.getenv('backend/app/services/creds.json', 'creds.json')

settings = Settings()