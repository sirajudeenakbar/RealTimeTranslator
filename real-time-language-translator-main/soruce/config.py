"""
Configuration settings for the Language Translator API
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Flask Configuration
DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
HOST = os.getenv('HOST', '0.0.0.0')
PORT = int(os.getenv('PORT', 5000))
FLASK_ENV = os.getenv('FLASK_ENV', 'development')

# CORS Configuration
CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000,http://localhost:5173,http://localhost:8000').split(',')

# Translation Settings
MAX_TEXT_LENGTH = 5000
REQUEST_TIMEOUT = 30
MAX_LANGUAGES_CACHE_SIZE = 1000

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', 'translator.log')

# Feature Flags
ENABLE_SPEECH_RECOGNITION = True
ENABLE_TEXT_TO_SPEECH = True
ENABLE_HISTORY = True

# MySQL Database Configuration
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = int(os.getenv('DB_PORT', 3306))
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_NAME = os.getenv('DB_NAME', 'translator_db')
DB_CHARSET = 'utf8mb4'
DB_COLLATE = 'utf8mb4_unicode_ci'

