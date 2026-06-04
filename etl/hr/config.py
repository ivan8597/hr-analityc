import os
from dotenv import load_dotenv

from ..config import Config as BaseConfig

load_dotenv()


class HRConfig:
    DB_HOST = BaseConfig.DB_HOST
    DB_PORT = BaseConfig.DB_PORT
    DB_NAME = BaseConfig.DB_NAME
    DB_USER = BaseConfig.DB_USER
    DB_PASSWORD = BaseConfig.DB_PASSWORD
    DATABASE_URL = BaseConfig.DATABASE_URL

    DATA_DIR = BaseConfig.DATA_DIR
    HR_EXCEL_FILENAME = os.getenv('HR_EXCEL_FILENAME', 'ш.xls')
    HR_EXCEL_PATH = os.path.join(DATA_DIR, HR_EXCEL_FILENAME)

    LOG_LEVEL = BaseConfig.LOG_LEVEL
    MAX_RETRIES = BaseConfig.MAX_RETRIES
    RETRY_DELAY = BaseConfig.RETRY_DELAY

    HR_SCHEMA_MAPPING_PATH = os.getenv('HR_SCHEMA_MAPPING_PATH', './config/hr_schema_mapping.json')

    BATCH_SIZE = int(os.getenv('HR_BATCH_SIZE', '5000'))
    REJECT_BATCH_SIZE = int(os.getenv('HR_REJECT_BATCH_SIZE', '1000'))
    FUZZY_THRESHOLD = int(os.getenv('HR_FUZZY_THRESHOLD', '85'))
