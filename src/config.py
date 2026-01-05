# src/config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Server config
    APP_PORT = int(os.getenv("APP_PORT", 8000))
    RELAY_PUBLIC_KEY = os.getenv("RELAY_PUBLIC_KEY", 8000)
    

settings = Settings()
