import os
from dotenv import load_dotenv

# Load environment variables từ file .env
load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    MONGO_URI = os.getenv("MONGO_URI")
    JWT_EXPIRATION = int(os.getenv("JWT_EXPIRATION", 3600))
    
    # PayPal API Configuration
    PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")
    PAYPAL_SECRET = os.getenv("PAYPAL_SECRET")
    PAYPAL_MODE = os.getenv("PAYPAL_MODE", "sandbox")  # Default là "sandbox"