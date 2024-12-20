from flask import Blueprint, request, jsonify
from database import get_db
from datetime import datetime

stats_bp = Blueprint("stats", __name__, url_prefix='/api/stats')

@stats_bp.route("/revenue", methods=["GET"])
def calculate_revenue():
    """
    API Tính doanh thu và thống kê số lượng hàng bán ra theo tháng.
    """
    try:
        db = get_db()
        # Lấy tham số tháng và năm từ query parameters
        month = request.args.get("month", type=int)
        year = request.args.get("year", type=int)

        if not month or not year:
            return jsonify({"error": "Month and year are required!"}), 400

        # Định dạng thời gian bắt đầu và kết thúc của tháng
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)

        # Tìm các đơn hàng trong khoảng thời gian này
        orders = db.orders.find({"orderTime": {"$gte": start_date, "$lt": end_date}, "status": "Completed"})

        # Tính tổng doanh thu và thống kê số lượng bán ra
        total_revenue_usd = 0
        total_revenue_vnd = 0
        product_sales = {}

        for order in orders:
            for item in order["items"]:
                product_id = item["productId"]
                quantity = item["quantity"]

                # Tính doanh thu cho sản phẩm
                total_revenue_usd += item["priceUSD"] * quantity
                total_revenue_vnd += item["priceVND"] * quantity
                
                product = db.products.find_one({"ProductId": product_id})

                # Cập nhật số lượng bán ra theo sản phẩm
                if product_id not in product_sales:
                    product_sales[product_id] = {
                        "productTitle": product["ProductTitle"],
                        "quantity": 0,
                        "category": product["Category"],
                        "subCategory": product["SubCategory"],
                        "productType": product["ProductType"]
                    }
                product_sales[product_id]["quantity"] += quantity

        # Trả về kết quả
        return jsonify({
            "month": month,
            "year": year,
            "totalRevenueUSD": round(total_revenue_usd, 2),
            "totalRevenueVND": int(total_revenue_vnd),
            "productSales": list(product_sales.values())
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
