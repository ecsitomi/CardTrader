# config.py
import os
from pathlib import Path

# Alap beállítások
BASE_DIR = Path(__file__).parent
DATABASE_NAME = 'cards_platform.db'
DATABASE_PATH = BASE_DIR / DATABASE_NAME

# Streamlit beállítások
PAGE_CONFIG = {
    "page_title": "Kártya Csere Platform",
    "page_icon": "🃏",
    "layout": "wide",
    "initial_sidebar_state": "expanded"
}

# Biztonság
SECRET_KEY = os.environ.get('SECRET_KEY', 'development-key-change-in-production')
PASSWORD_SALT_ROUNDS = 100000  # PBKDF2 iterációk száma

# Rate limiting
MAX_LOGIN_ATTEMPTS = 5
LOGIN_TIMEOUT_SECONDS = 300  # 5 perc

# Fejlesztői mód
DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'
