import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    DB_HOST = os.getenv('POSTGRES_HOST', 'localhost')
    DB_PORT = int(os.getenv('POSTGRES_PORT', '5432'))
    DB_NAME = os.getenv('POSTGRES_DB', 'hr_db')
    DB_USER = os.getenv('POSTGRES_USER', 'hr_user')
    DB_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'secure_password')

    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

    DATA_DIR = os.getenv('DATA_DIR', './data')
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
    RETRY_DELAY = int(os.getenv('RETRY_DELAY_SECONDS', '5'))
