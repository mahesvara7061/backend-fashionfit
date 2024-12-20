from flask import Blueprint, request, jsonify
from utils.auth import admin_required
from database import get_db
from datetime import datetime

manager_bp = Blueprint("manager", __name__, url_prefix='/api/manager')

@manager_bp.route("/add", methods=["PUT"])
@admin_required
def add_manager():
    """
    API để thêm manager mới.
    """
    try:
        db = get_db()
        data = request.json

        user_id = str(data.get("userId"))

        # Kiểm tra thông tin bắt buộc
        if not user_id:
            return jsonify({"error": "Missing required fields!"}), 400

        db.users.update_one(
            {"UserId": user_id},
            {"$set": {"Role": "Manager",
                      "UpdatedTime": str(datetime.now())}}
        )
        return jsonify({"message": "Manager added successfully!"}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@manager_bp.route("/remove", methods=["DELETE"])
@admin_required
def remove_manager():
    try:
        db = get_db()
        data = request.json

        user_id = str(data.get("userId"))

        # Kiểm tra thông tin bắt buộc
        if not user_id:
            return jsonify({"error": "Missing required fields!"}), 400

        db.users.update_one(
            {"UserId": user_id},
            {"$unset": {"Role": ""}}
        )
        return jsonify({"message": "Manager removed successfully!"}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500
