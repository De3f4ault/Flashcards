import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))

# Load .env from project root (one level up from app/)
project_root = os.path.dirname(basedir)
load_dotenv(os.path.join(project_root, '.env'))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'flashcards.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Flash message categories
    FLASH_CATEGORIES = ['success', 'info', 'warning', 'error']

    # Pagination
    CARDS_PER_PAGE = 20
    DECKS_PER_PAGE = 12

    # AI Configuration
    AI_ENABLED = os.environ.get('AI_ENABLED', 'false').lower() == 'true'
    AI_PROVIDER = os.environ.get('AI_PROVIDER', 'gemini')
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')  # Optional fallback

    # AI Limits and Controls
    AI_FREE_CREDITS_PER_USER = int(os.environ.get('AI_FREE_CREDITS_PER_USER', '100'))
    AI_MAX_CARDS_PER_GENERATION = int(os.environ.get('AI_MAX_CARDS_PER_GENERATION', '50'))
    AI_REQUEST_TIMEOUT = int(os.environ.get('AI_REQUEST_TIMEOUT', '30'))
    AI_RATE_LIMIT_PER_HOUR = int(os.environ.get('AI_RATE_LIMIT_PER_HOUR', '50'))

    # AI Feature Flags
    AI_CARD_GENERATION_ENABLED = os.environ.get('AI_CARD_GENERATION_ENABLED', 'true').lower() == 'true'
    AI_CARD_ENHANCEMENT_ENABLED = os.environ.get('AI_CARD_ENHANCEMENT_ENABLED', 'true').lower() == 'true'
    AI_HINT_GENERATION_ENABLED = os.environ.get('AI_HINT_GENERATION_ENABLED', 'true').lower() == 'true'
    AI_TAG_SUGGESTIONS_ENABLED = os.environ.get('AI_TAG_SUGGESTIONS_ENABLED', 'false').lower() == 'true'


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_ECHO = True


class ProductionConfig(Config):
    DEBUG = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
