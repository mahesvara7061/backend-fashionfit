from flask import Blueprint, request, jsonify
from database import get_db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import pytz

user_bp = Blueprint("user", __name__, url_prefix='/api/user')

# Hàm lấy thời gian hiện tại theo GMT+7
def get_current_time():
    tz = pytz.timezone('Asia/Bangkok')
    return datetime.now(tz).isoformat()

@user_bp.route("/register", methods=["POST"])
def register_user():
    """
    API đăng ký user.
    """
    try:
        db = get_db()
        data = request.get_json()

        # Kiểm tra các trường bắt buộc
        required_fields = ["Username", "Password", "Email", "FullName", "Address", "DateOfBirth", "PhoneNumber"]
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({
                "success": False,
                "error": f"Missing required fields: {', '.join(missing_fields)}"
            }), 400

        # Kiểm tra username và email đã tồn tại
        if db.users.find_one({"Username": data["Username"]}):
            return jsonify({"success": False, "error": "Username already exists."}), 400
        if db.users.find_one({"Email": data["Email"]}):
            return jsonify({"success": False, "error": "Email already exists."}), 400

        # Hash mật khẩu
        hashed_password = generate_password_hash(data["Password"])

        # Lấy UserId tiếp theo
        last_user = db.users.find_one(sort=[("UserId", -1)])
        next_id = int(last_user["UserId"]) + 1 if last_user else 1

        # Tạo user mới
        user = {
            "UserId": f"{next_id:03}",
            "Username": data["Username"],
            "Password": hashed_password,
            "Email": data["Email"],
            "FullName": data["FullName"],
            "Address": data["Address"],
            "DateOfBirth": data["DateOfBirth"],
            "PhoneNumber": data["PhoneNumber"],
            "CreatedTime": get_current_time(),
            "UpdatedTime": get_current_time()
        }

        db.users.insert_one(user)

        return jsonify({"success": True, "message": "User registered successfully."}), 201

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@user_bp.route("/login", methods=["POST"])
def login_user():
    """
    API đăng nhập user.
    """
    try:
        db = get_db()
        data = request.get_json()
        username = data.get("Username")
        password = data.get("Password")

        # Kiểm tra user có tồn tại
        user = db.users.find_one({"Username": username})
        if not user or not check_password_hash(user["Password"], password):
            return jsonify({"success": False, "error": "Invalid username or password."}), 401

        return jsonify({"success": True, "message": "Login successful.", "UserId": user["UserId"]}), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@user_bp.route("/update/<user_id>", methods=["PUT"])
def update_user(user_id):
    """
    API cập nhật thông tin user bằng UserId.
    """
    try:
        db = get_db()
        update_data = request.get_json()

        # Các trường không được phép cập nhật
        prohibited_fields = ["UserId", "CreatedTime"]
        if any(field in update_data for field in prohibited_fields):
            return jsonify({
                "success": False,
                "error": f"Fields not allowed to be manually updated: {', '.join(prohibited_fields)}"
            }), 400

        # Chuẩn bị dữ liệu cập nhật
        update_fields = {key: update_data[key] for key in update_data if key not in prohibited_fields}
        update_fields["UpdatedTime"] = get_current_time()

        # Cập nhật user trong database
        result = db.users.update_one({"UserId": user_id}, {"$set": update_fields})
        if result.matched_count == 0:
            return jsonify({"success": False, "error": "User not found."}), 404

        return jsonify({"success": True, "message": "User updated successfully."}), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@user_bp.route("/delete/<user_id>", methods=["DELETE"])
def delete_user(user_id):
    """
    API xóa user bằng UserId.
    """
    try:
        db = get_db()
        result = db.users.delete_one({"UserId": user_id})
        if result.deleted_count == 0:
            return jsonify({"success": False, "error": "User not found."}), 404

        return jsonify({"success": True, "message": "User deleted successfully."}), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@user_bp.route("/profile/<user_id>", methods=["GET"])
def get_user_profile(user_id):
    """
    API lấy thông tin user.
    """
    try:
        db = get_db()
        user = db.users.find_one({"UserId": user_id}, {"Password": 0, "_id": 0})
        if not user:
            return jsonify({"success": False, "error": "User not found."}), 404

        return jsonify({"success": True, "data": user}), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
