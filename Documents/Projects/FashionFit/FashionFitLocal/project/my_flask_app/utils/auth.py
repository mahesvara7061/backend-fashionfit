import jwt
from flask import request, jsonify
from functools import wraps
from config import Config

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get("Authorization", "").split("Bearer ")[-1]
        if not token:
            return jsonify({"error": "Token is missing!"}), 403
        try:
            payload = jwt.decode(token, Config.SECRET_KEY, algorithms=["HS256"])
            if payload.get("role") != "Admin":
                return jsonify({"error": "Access denied! Admins only."}), 403
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired!"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token!"}), 401
        return f(*args, **kwargs)
    return decorated_function
