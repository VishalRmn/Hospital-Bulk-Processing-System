import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration."""
    
    # Flask
    DEBUG = False
    TESTING = False
    JSON_SORT_KEYS = False
    
    # Hospital API
    HOSPITAL_API_URL = os.getenv('HOSPITAL_API_URL', 'https://hospital-directory.onrender.com')
    
    # Request settings
    REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '10'))
    MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
    
    # Batch processing
    MAX_BATCH_SIZE = int(os.getenv('MAX_BATCH_SIZE', '20'))
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    # Data persistence
    DATA_DIR = os.getenv('DATA_DIR', 'data')


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    LOG_LEVEL = 'DEBUG'


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    LOG_LEVEL = 'DEBUG'
    # Use in-memory storage for tests
    DATA_DIR = '/tmp/test_data'


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    LOG_LEVEL = 'INFO'


def get_config():
    """Get configuration based on environment."""
    env = os.getenv('APP_CONFIG', 'development')
    
    if env == 'production':
        return ProductionConfig
    elif env == 'testing':
        return TestingConfig
    else:
        return DevelopmentConfig
