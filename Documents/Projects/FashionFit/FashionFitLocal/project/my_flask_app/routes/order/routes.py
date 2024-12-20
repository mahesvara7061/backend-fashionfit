from flask import Blueprint, request, jsonify
from datetime import datetime
from database import get_db, exchange_rate
from services.ghtk_service import create_order, calculate_shipping_fee, cancel_order, get_order_status
import pytz

order_bp = Blueprint('order', __name__, url_prefix='/api/order')

def get_current_time():
    tz = pytz.timezone('Asia/Bangkok')
    return datetime.now(tz).isoformat()

@order_bp.route('/view', methods=['GET'])
def get_orders():
    """
    Lấy danh sách tất cả đơn hàng.
    Hỗ trợ bộ lọc theo trạng thái hiện tại hoặc thời gian.
    """
    try:
        db = get_db()
        
        # Lấy query params
        current_status = request.args.get("status")  # Lọc theo trạng thái hiện tại
        start_time = request.args.get("start_time")  # Thời gian bắt đầu
        end_time = request.args.get("end_time")  # Thời gian kết thúc
        
        # Tạo truy vấn MongoDB
        query = {}
        if current_status:
            query["status"] = current_status  # Lọc theo trạng thái hiện tại

        if start_time or end_time:
            query["time"] = {}
            if start_time:
                query["time"]["$gte"] = datetime.fromisoformat(start_time)
            if end_time:
                query["time"]["$lte"] = datetime.fromisoformat(end_time)

        # Truy vấn MongoDB
        orders = list(db.orders.find(query, {"_id": 0}))
        return jsonify({"orders": orders}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Create order from cart
@order_bp.route('/create-from-cart', methods=['POST'])
def create_order_from_cart():
    """
    API để chuyển giỏ hàng thành đơn hàng.
    """
    try:
        db = get_db()
        data = request.json

        # Lấy thông tin từ request
        user_id = str(data.get("userId"))
        user = db.users.find_one({"UserId": user_id})

        # Xác minh giỏ hàng
        cart = db.carts.find_one({"userId": user_id})
        if not cart or not cart.get("items"):
            return jsonify({"error": "Cart is empty or not found for the user"}), 404

        # Lấy tổng tiền và thông tin giỏ hàng
        items = cart["items"]
        total_vnd = cart.get("totalVND", 0)
        total_usd = cart.get("totalUSD", 0)
        discount_type = cart.get("discountType", None)
        
        # Tính phí ship
        cart_weight = calculate_cart_weight(user_id)
        
        order_data = {
            "pick_province": "Hồ Chí Minh",
            "pick_district": "Quận 5",
            "address": str(user["Address"]),
            "province": str(user["Province"]),
            "district": str(user["District"]),
            "weight": float(cart_weight),
            "value": cart.get("totalVND", "none"),
        }
        
        fee_ship_vnd = calculate_shipping_fee(order_data)["fee"]["ship_fee_only"]
        if not fee_ship_vnd:
            return jsonify({"error": "Cannot calculate shipping fee"}), 500
        # Free ship applied
        if discount_type == "freeship": 
            fee_ship_vnd = 0
        elif discount_type == "ship_discount":
            discount_amout = cart.get("discountedShippingVND")
            fee_ship_vnd = max(fee_ship_vnd - discount_amout, 0)
            
        # Cập nhật tổng tiền
        total_vnd = total_vnd + fee_ship_vnd
        total_usd = total_usd + fee_ship_vnd / exchange_rate
        
        # Tạo order bên GHTK
        order_id = str(int(datetime.now().timestamp()))  # Sử dụng timestamp làm orderId
        order_data = {
            "products": [{
                "weight": float(cart_weight/1000)
            }],
            "order": {
                "id": order_id, # order_id
                "pick_name": "FashionFit",
                "pick_address": "227 Nguyễn Văn Cừ",
                "pick_province": "TP. Hồ Chí Minh",
                "pick_district": "Quận 5",
                "pick_ward": "Phường 4",
                "pick_street": "Nguyen Van Cu",
                "pick_tel": "0911122233",
                "name": str(user["FullName"]),
                "address": str(user["Address"]),
                "province": str(user["Province"]),
                "district": str(user["District"]),
                "ward": str(user["Ward"]),
                "tel": str(user["PhoneNumber"]),
                "email": str(user["Email"]),
                "hamlet": "Khác",
                "pick_money": 0,
                "value": float(total_vnd),
                "booking_id": "123"
            }
        }
        
        order_created = create_order(order_data)["order"]
        label = order_created["label"]
        estimated_deliver_time = order_created["estimated_deliver_time"]
        if not label:
            return jsonify({"error": "Cannot create order to GHTK"}), 500
        
        # Tạo đơn hàng mới
        new_order = {
            "orderId": order_id,
            "userId": user_id,
            "items": items,
            "feeShip": fee_ship_vnd,
            "totalVND": round(total_vnd, 2),
            "totalUSD": round(total_usd, 2),
            "status": "Pending",
            "statusHistory": [{"status": "Pending", "time": datetime.now()}],
            "orderTime": datetime.now(),
            "orderLabel": label,
            "deliverTime": estimated_deliver_time
        }
        
        # Lưu đơn hàng vào collection orders
        db.orders.insert_one(new_order)

        # Xóa giỏ hàng khỏi collection carts
        db.carts.delete_one({"userId": user_id})

        return jsonify({
            "message": "Order created successfully.",
            "orderId": order_id,
            "orderLabel": label
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Update order status
@order_bp.route("/<order_id>/status", methods=["PUT"])
def update_order_status(order_id):
    """
    Cập nhật trạng thái đơn hàng.
    """
    try:
        db = get_db()
        data = request.json
        
        order_id = str(order_id)
        order = db.orders.find_one({"orderId": str(order_id)})
        label = order["orderLabel"]
        
        response = get_order_status(label)["order"]
        status = response["status_text"]
        time = response["created"]
        
        if not order:
            return jsonify({"error": "Order not found!"}), 404
        if order.get("currentStatus") == status:
            return jsonify({"status": status}), 200
        
        # Create entry
        status_entry = {
            "status": status, 
            "time": time, # Lấy thời gian hiện tại
        }

        # Insert to 'statusHistory'
        db.orders.update_one(
            {"orderId": order_id},
            {
                "$set": {"status": status},
                "$push": { "statusHistory": status_entry}
            }
        )

        return jsonify({"message": "Order status updated successfully."}), 200

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

# Check order status
@order_bp.route('/<order_id>/status-history', methods=['GET'])
def get_order_status_history(order_id):
    """
    Lấy lịch sử trạng thái của đơn hàng.
    """
    try:
        db = get_db()
        order_id = str(order_id)
        # Tìm đơn hàng theo order_id
        order = db.orders.find_one({"orderId": order_id})
        if not order:
            return jsonify({"error": "Order not found"}), 404

        # Lấy trường statusHistory
        status_history = order.get("statusHistory", [])
        return jsonify({"orderId": order_id, "statusHistory": status_history}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Cancel order
@order_bp.route("/<order_id>/cancel", methods=["PUT"])
def cancel_order(order_id):
    try:
        db = get_db()
        order_id = str(order_id)
        # Tìm đơn hàng và kiểm tra trạng thái
        order = db.orders.find_one({"orderId": str(order_id)})
        if not order:
            return jsonify({"error": "Order not found!!"}), 404
        if order["status"] == "Completed":
            return jsonify({"error": "Cannot cancel a completed order"}), 400
        
        # Create entry
        status_entry = {
            "status": "Cancelled", 
            "time": datetime.now(), # Lấy thời gian hiện tại
        }
        
        db.orders.update_one(
            {"orderId": str(order_id)},
            {
                "$set": {"status": "Cancelled"},
                "$push": { "statusHistory": status_entry}
            }
        )
        
        label = order["orderLabel"]
        if not label:
            return jsonify({"error": "Label not found!"}), 404
        response = cancel_order(label)
        if not response:
            return jsonify({"error": "Cannot cancel order"}), 500
        
        return jsonify({"message": "Order cancelled", "label": label}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
# Đặt trạng thái đơn hàng thành 'Completed'
@order_bp.route("/<order_id>/completed", methods=["PUT"])
def mark_order_completed(order_id):
    try:
        db = get_db()
        order_id = str(order_id)
        
        order = db.orders.find_one({"orderId": order_id})
        if not order:
            return jsonify({"error": "Order not found!!"}), 404
        if order["status"] == "Cancelled":
            return jsonify({"error": "Order is cancelled!"}), 400
        
        # Create entry
        status_entry = {
            "status": "Completed", 
            "time": datetime.now(), # Lấy thời gian hiện tại
        }
        
        db.orders.update_one(
            {"orderId": str(order_id)},
            {
                "$set": {"status": "Completed"},
                "$push": { "statusHistory": status_entry}
            }
        )
        
        for item in order["items"]:
            quantity = int(item["quantity"])
            db.products.update_one(
                {"ProductId": item["productId"]},
                {"$inc": {
                    "Stock": -quantity,
                    "Sales": quantity
                }}
            )
        
        return jsonify({"message": "Marked order completed"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Lấy chi tiết đơn hàng
@order_bp.route('/<order_id>', methods=['GET'])
def get_order_details(order_id):
    """
    Lấy chi tiết một đơn hàng theo order_id.
    """
    try:
        db = get_db()

        # Tìm đơn hàng theo order_id
        order = db.orders.find_one({"orderId": str(order_id)}, {"_id": 0})
        if not order:
            return jsonify({"error": "Order not found"}), 404
        
        return jsonify({"order": order}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Tính trọng lượng của cart 
def calculate_cart_weight(user_id):
    db = get_db()
    pipeline = [
        { "$match": { "userId": user_id } },
        { "$unwind": "$items" },
        {
            "$lookup": {
                "from": "products",
                "localField": "items.productId",
                "foreignField": "ProductId",
                "as": "productDetails"
            }
        },
        { "$unwind": "$productDetails" },
        {
            "$group": {
                "_id": "$cartId",
                "totalWeight": {
                    "$sum": {
                        "$multiply": ["$items.quantity", "$productDetails.Weight"]
                    }
                }
            }
        }
    ]

    result = list(db.carts.aggregate(pipeline))
    return result[0]["totalWeight"] if result else 0


    
