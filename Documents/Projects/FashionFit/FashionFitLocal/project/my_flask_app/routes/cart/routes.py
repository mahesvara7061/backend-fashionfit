from flask import Blueprint, request, jsonify
from datetime import datetime
from database import get_db, exchange_rate

cart_bp = Blueprint('cart', __name__, url_prefix='/api/cart')

# Add product to cart
@cart_bp.route("/add", methods=["POST"])
def add_product():
    """
    API thêm sản phẩm vào giỏ hàng.
    Hiển thị giá của từng sản phẩm và tính tổng số tiền trong giỏ hàng.
    """
    try:
        db = get_db()
        data = request.json

        # Lấy dữ liệu từ request
        user_id = str(data.get("userId"))
        product_id = str(data.get("productId"))
        quantity = data.get("quantity", 1)

        # Validate input
        if not user_id:
            return jsonify({"error": "User ID is required!"}), 400
        if not product_id:
            return jsonify({"error": "Product ID is required!"}), 400
        if not isinstance(quantity, int) or quantity <= 0:
            return jsonify({"error": "Quantity must be a positive integer!"}), 400

        # Kiểm tra sản phẩm có tồn tại
        product = db.products.find_one({"ProductId": product_id})
        if not product:
            return jsonify({"error": "Product does not exist!"}), 404

        # Kiểm tra số lượng tồn kho
        if product["Stock"] < quantity:
            return jsonify({"error": "Not enough stock for this product!"}), 400

        # Tạo thông tin sản phẩm mới
        product_info = {
            "productId": product_id,
            "name": product["ProductTitle"],
            "quantity": quantity,
            "priceUSD": product["PriceUSD"],
            "priceVND": product["PriceVND"]
        }

        # Kiểm tra xem người dùng đã có giỏ hàng hay chưa
        user_cart = db.carts.find_one({"userId": user_id})

        if user_cart:
            # Nếu đã có giỏ hàng, kiểm tra xem sản phẩm đã tồn tại trong giỏ chưa
            existing_product = next((item for item in user_cart["items"] if item["productId"] == product_id), None)

            if existing_product:
                # Nếu sản phẩm đã tồn tại, cập nhật số lượng
                new_quantity = existing_product["quantity"] + quantity
                if new_quantity > product["Stock"]:
                    return jsonify({"error": "Cannot add more products than in stock!"}), 400
                existing_product["quantity"] = new_quantity
            else:
                # Nếu sản phẩm chưa tồn tại, thêm vào giỏ hàng
                user_cart["items"].append(product_info)

            # Tính lại tổng số tiền
            total_usd = round(sum(item["quantity"] * item["priceUSD"] for item in user_cart["items"]), 2)
            total_vnd = round(sum(item["quantity"] * item["priceVND"] for item in user_cart["items"]), 2)

            # Cập nhật giỏ hàng
            db.carts.update_one(
                {"userId": user_id},
                {"$set": {"items": user_cart["items"], "totalUSD": total_usd, "totalVND": total_vnd}}
            )
        else:
            # Nếu chưa có giỏ hàng, tạo giỏ hàng mới
            total_usd = quantity * product["PriceUSD"]
            total_vnd = quantity * product["PriceVND"]
            new_cart = {
                "userId": user_id,
                "items": [product_info],
                "totalUSD": total_usd,
                "totalVND": total_vnd
            }
            db.carts.insert_one(new_cart)

        return jsonify({"message": "Product added to cart."}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Remove product from cart
@cart_bp.route("/remove", methods=["DELETE"])
def remove_from_cart():
    """
    API để xóa sản phẩm khỏi giỏ hàng và tính lại tổng tiền.
    """
    try:
        db = get_db()
        data = request.json

        # Lấy dữ liệu từ request
        user_id = str(data.get("userId"))
        product_id = str(data.get("productId"))

        # Validate input
        if not user_id:
            return jsonify({"error": "User ID is required!"}), 400
        if not product_id:
            return jsonify({"error": "Product ID is required!"}), 400

        # Tìm giỏ hàng của người dùng
        user_cart = db.carts.find_one({"userId": user_id})

        if not user_cart:
            return jsonify({"error": "Cart not found for this user!"}), 404

        # Kiểm tra sản phẩm trong giỏ và xóa
        product_found = False
        for item in user_cart["items"]:
            if item["productId"] == product_id:
                user_cart["items"].remove(item)
                product_found = True
                break

        if not product_found:
            return jsonify({"error": "Product not found in cart!"}), 404

        # Nếu giỏ hàng còn sản phẩm, tính lại tổng tiền
        if user_cart["items"]:
            total_usd = round(sum(item["quantity"] * item["priceUSD"] for item in user_cart["items"]), 2)
            total_vnd = round(sum(item["quantity"] * item["priceVND"] for item in user_cart["items"]), 2)

            # Cập nhật giỏ hàng trong database
            db.carts.update_one(
                {"userId": user_id},
                {"$set": {"items": user_cart["items"], "totalUSD": total_usd, "totalVND": total_vnd}}
            )
        else:
            # Nếu giỏ hàng trống, xóa giỏ hàng khỏi database
            db.carts.delete_one({"userId": user_id})

        return jsonify({"message": "Product removed from cart."}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# View cart
@cart_bp.route("/<user_id>", methods=["GET"])
def view_cart(user_id):
    try:
        db = get_db()
        user_id = str(user_id)
        # Find the user's cart
        user_cart = db.carts.find_one({"userId": user_id}, {"_id": 0})

        if not user_cart:
            return jsonify({"error": "Cart not found for this user!"}), 404
        # Return the user's cart items
        return jsonify(user_cart), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Apply coupon to cart
@cart_bp.route('/apply_coupon', methods=['POST'])
def apply_coupon():
    """
    API để áp dụng mã giảm giá vào giỏ hàng.
    """
    try:
        db = get_db()
        data = request.json

        # Lấy thông tin từ request
        user_id = str(data.get("userId"))
        coupon_code = data.get("couponCode")

        # Validate input
        if not user_id or not coupon_code:
            return jsonify({"error": "Missing userId or couponCode"}), 400

        # Tìm giỏ hàng của người dùng
        cart = db.carts.find_one({"userId": user_id})
        if not cart or not cart.get("items"):
            return jsonify({"error": "Cart is empty or not found for the user"}), 404

        # Tìm mã giảm giá
        coupon = db.coupons.find_one({"code": coupon_code})
        if not coupon:
            return jsonify({"error": "Invalid coupon code"}), 404

        # Kiểm tra ngày hết hạn
        if coupon["expire_date"] < datetime.now():
            return jsonify({"error": "Coupon has expired"}), 400

        # Tính tổng giá trị giỏ hàng
        total_price_vnd = sum(item["quantity"] * db.products.find_one({"ProductId": item["productId"]})["PriceVND"] for item in cart["items"])
        total_price_usd = sum(item["quantity"] * db.products.find_one({"ProductId": item["productId"]})["PriceUSD"] for item in cart["items"])

        # Áp dụng mã giảm giá theo loại
        discount_amount_vnd = 0
        discount_amount_usd = 0

        if coupon["type"] == "freeship":
            discount_description = "Free shipping applied"
        elif coupon["type"] == "ship_discount":
            if total_price_vnd < coupon.get("min_order_value", 0):
                return jsonify({"error": f"Order must be at least {coupon['min_order_value']} VND to apply this coupon"}), 400
            discount_shipping_vnd = coupon["discount_amount"]
            discount_description = f"Shipping discount of {coupon['discount_amount']} VND applied"
        elif coupon["type"] == "discount_percentage":
            if total_price_vnd < coupon.get("min_order_value", 0):
                return jsonify({"error": f"Order must be at least {coupon['min_order_value']} VND to apply this coupon"}), 400
            discount_amount_vnd = min((total_price_vnd * coupon["discount"]) / 100, coupon["max_discount"])
            discount_amount_usd = min((total_price_usd * coupon["discount"]) / 100, coupon["max_discount"] / exchange_rate)  # USD conversion
            discount_description = f"{coupon['discount']}% discount applied (Max {coupon['max_discount']} VND)"
        elif coupon["type"] == "discount_amount":
            if total_price_vnd < coupon.get("min_order_value", 0):
                return jsonify({"error": f"Order must be at least {coupon['min_order_value']} VND to apply this coupon"}), 400
            discount_amount_vnd = coupon["discount_amount"]
            discount_amount_usd = coupon["discount_amount"] / exchange_rate  # USD conversion
            discount_description = f"{coupon['discount_amount']} VND discount applied"
        else:
            return jsonify({"error": "Invalid coupon type"}), 400

        # Tính tổng tiền sau khi giảm giá
        discounted_total_vnd = max(total_price_vnd - discount_amount_vnd, 0)
        discounted_total_usd = max(total_price_usd - discount_amount_usd, 0)

        # Cập nhật giỏ hàng
        db.carts.update_one(
            {"userId": user_id},
            {"$set": {
                "totalVND": round(discounted_total_vnd, 2),
                "totalUSD": round(discounted_total_usd, 2),
                "couponApplied": coupon_code,
                "discountType": coupon["type"],
                "discountDescription": discount_description
            }}
        )
        
        if coupon["type"] == "ship_discount":
            db.carts.update_one(
            {"userId": user_id},
            {"$set": {
                "discountedShippingVND": discount_shipping_vnd
            }}
            )

        return jsonify({
            "message": "Coupon applied successfully.",
            "originalTotalVND": round(total_price_vnd, 2),
            "originalTotalUSD": round(total_price_usd, 2),
            "discountAmountVND": round(discount_amount_vnd, 2),
            "discountAmountUSD": round(discount_amount_usd, 2),
            "discountedTotalVND": round(discounted_total_vnd, 2),
            "discountedTotalUSD": round(discounted_total_usd, 2),
            "couponCode": coupon_code,
            "discountDescription": discount_description,
            "discountedShippingVND": discount_shipping_vnd
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

