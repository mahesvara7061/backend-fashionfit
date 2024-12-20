from flask import Blueprint, request, jsonify
from database import get_db
from datetime import datetime

coupon_bp = Blueprint('coupon', __name__, url_prefix='/api/coupons')

@coupon_bp.route('/add', methods=['POST'])
def add_coupon():
    """
    API để thêm coupon mới (hỗ trợ nhiều loại coupon).
    """
    try:
        db = get_db()
        data = request.json

        # Kiểm tra trường bắt buộc chung
        required_fields = ["couponId", "code", "expire_date", "type"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        # Kiểm tra trùng lặp coupon code
        if db.coupons.find_one({"code": data["code"]}):
            return jsonify({"error": "Coupon with this code already exists."}), 400

        # Xử lý theo loại coupon
        coupon_type = data["type"]
        new_coupon = {
            "couponId": data["couponId"],
            "code": data["code"],
            "expire_date": datetime.strptime(data["expire_date"], "%Y-%m-%dT%H:%M:%S"),
            "type": coupon_type,
            "createdAt": datetime.now()
        }

        if coupon_type == "freeship":
            # Freeship không yêu cầu giá trị tối thiểu
            new_coupon.update({
                "min_order_value": data.get("min_order_value", None),  # Giá trị tối thiểu (nếu có)
                "description": data.get("description", "Free shipping")
            })

        elif coupon_type == "ship_discount":
            # Giảm phí vận chuyển theo số tiền
            if "discount_amount" not in data:
                return jsonify({"error": "Missing discount_amount for ship_discount type"}), 400
            new_coupon.update({
                "discount_amount": data["discount_amount"],  # Số tiền giảm
                "min_order_value": data.get("min_order_value", None),  # Giá trị tối thiểu (nếu có)
                "description": data.get("description", "Shipping discount")
            })

        elif coupon_type == "discount_percentage":
            # Giảm giá theo %
            if "discount" not in data or "max_discount" not in data or "min_order_value" not in data:
                return jsonify({"error": "Missing fields for discount_percentage type"}), 400
            new_coupon.update({
                "discount": data["discount"],  # Tỷ lệ giảm giá (%)
                "max_discount": data["max_discount"],  # Giá trị giảm tối đa
                "min_order_value": data["min_order_value"],  # Giá trị đơn hàng tối thiểu
                "description": data.get("description", "Percentage discount")
            })

        elif coupon_type == "discount_amount":
            # Giảm giá theo số tiền
            if "discount_amount" not in data or "min_order_value" not in data:
                return jsonify({"error": "Missing fields for discount_amount type"}), 400
            new_coupon.update({
                "discount_amount": data["discount_amount"],  # Số tiền giảm
                "min_order_value": data["min_order_value"],  # Giá trị đơn hàng tối thiểu
                "description": data.get("description", "Amount discount")
            })

        else:
            return jsonify({"error": "Invalid coupon type."}), 400

        # Thêm coupon vào database
        db.coupons.insert_one(new_coupon)
        return jsonify({"message": "Coupon added successfully.", "coupon": new_coupon["code"]}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@coupon_bp.route('/<coupon_id>', methods=['DELETE'])
def delete_coupon(coupon_id):
    """
    API để xóa coupon theo couponId.
    """
    try:
        db = get_db()
        coupon_id = str(coupon_id)
        # Xóa coupon khỏi database
        delete_result = db.coupons.delete_one({"couponId": coupon_id})
        if delete_result.deleted_count == 0:
            return jsonify({"error": "Coupon not found."}), 404

        return jsonify({"message": "Coupon deleted successfully."}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@coupon_bp.route('/<coupon_id>', methods=['GET'])
def view_coupon(coupon_id):
    """
    API để xem thông tin của một coupon theo couponId.
    """
    try:
        db = get_db()
        coupon_id = str(coupon_id)
        # Tìm coupon trong database
        coupon = db.coupons.find_one({"couponId": coupon_id}, {"_id": 0})
        if not coupon:
            return jsonify({"error": "Coupon not found."}), 404

        return jsonify(coupon), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@coupon_bp.route('/all', methods=['GET'])
def view_all_coupons():
    """
    API để xem danh sách tất cả coupon.
    """
    try:
        db = get_db()
        coupons = list(db.coupons.find({}, {"_id": 0}))

        return jsonify({"coupons": coupons}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
