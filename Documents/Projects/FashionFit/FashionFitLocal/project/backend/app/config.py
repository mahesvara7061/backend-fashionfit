import os
from dotenv import load_dotenv

# Load environment variables từ file .env
load_dotenv()

class Config:
    # MongoDB Atlas Configuration
    MONGO_URI = os.getenv("MONGO_URI")
    DATABASE_NAME = os.getenv("DATABASE_NAME")
    PRODUCT_COLLECTION = os.getenv("PRODUCT_COLLECTION")
    USER_COLLECTION = os.getenv("USER_COLLECTION")
    RATING_COLLECTION = os.getenv("RATING_COLLECTION")

    # PayPal API Configuration
    PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")
    PAYPAL_SECRET = os.getenv("PAYPAL_SECRET")
    PAYPAL_MODE = os.getenv("PAYPAL_MODE", "sandbox")  # Default là "sandbox"
