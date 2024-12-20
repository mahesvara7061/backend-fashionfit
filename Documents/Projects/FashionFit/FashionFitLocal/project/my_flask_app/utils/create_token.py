import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")

# Tạo token
import jwt
from datetime import datetime, timedelta

payload = {
    "user_id": "admin",
    "role": "Admin",
    "exp": datetime.now() + timedelta(hours=1)
}

token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
print(f"Generated Token: {token}")