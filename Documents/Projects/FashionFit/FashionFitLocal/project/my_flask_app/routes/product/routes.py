from flask import Blueprint, request, jsonify
from database import get_db
from datetime import datetime
import pytz

product_bp = Blueprint("product", __name__, url_prefix='/api/product')

def get_current_time():
    tz = pytz.timezone('Asia/Bangkok')
    return datetime.now(tz).isoformat()

@product_bp.route("/search", methods=["GET"])
def search_with_filters():
    """
    API tìm kiếm với từ khóa, chọn trường tìm kiếm, thêm bộ lọc và sắp xếp, hỗ trợ phân trang theo số trang.
    """
    try:
        db = get_db()
        product_collection = db.products
        # Lấy từ khóa và các trường tìm kiếm
        keyword = request.args.get("keyword")  # Từ khóa tìm kiếm
        search_fields = request.args.getlist("search_fields")  # Danh sách các trường tìm kiếm

        # Lấy các bộ lọc
        filters = {key: request.args.get(key) for key in ["Gender", "Category", "ProductType", "Colour", "Usage", "Brand"] if request.args.get(key)}
        limit = request.args.get("limit", default=10, type=int)  # Số lượng sản phẩm mỗi trang
        page = request.args.get("page", default=1, type=int)  # Trang hiện tại (mặc định là 1)

        # Lấy giá trị lọc theo PriceVND
        price_vnd_min = request.args.get("PriceVND_min", type=float)
        price_vnd_max = request.args.get("PriceVND_max", type=float)

        # Lọc còn hàng
        in_stock = request.args.get("in_stock", default=None, type=bool)
        if in_stock:
            filters["Stock"] = {"$gt": 0}

        # Lấy thông tin sắp xếp (sort)
        sort_field = request.args.get("sort_field", default=None)  # Trường để sắp xếp (PriceVND, ProductTitle, Sales, UpdatedDate)
        sort_order = request.args.get("sort_order", default="asc")  # Thứ tự sắp xếp: asc (tăng dần), desc (giảm dần)

        # Kiểm tra page hợp lệ
        if page < 1:
            return jsonify({"success": False, "error": "Page number must be 1 or greater"}), 400

        # Xây dựng truy vấn
        query = {}

        # Tìm kiếm từ khóa trên các trường được chọn
        if keyword and search_fields:
            search_conditions = []
            for field in search_fields:
                if field == "ProductId" and keyword.isdigit():
                    search_conditions.append({"ProductId": keyword})
                elif field in ["ProductTitle", "Description_Paragraph"]:
                    search_conditions.append({field: {"$regex": keyword, "$options": "i"}})
                else:
                    return jsonify({"success": False, "error": f"Invalid search field: {field}"}), 400

            if search_conditions:
                query["$or"] = search_conditions

        # Thêm bộ lọc khác
        query.update(filters)

        # Kiểm tra và thêm lọc theo giá (PriceVND)
        if price_vnd_min is not None or price_vnd_max is not None:
            price_filter = {}
            if price_vnd_min is not None:
                price_filter["$gte"] = price_vnd_min
            if price_vnd_max is not None:
                price_filter["$lte"] = price_vnd_max
            query["PriceVND"] = price_filter

        # Xác định tiêu chí sắp xếp
        sort_criteria = None
        if not sort_field and sort_order:  # Nếu không chỉ định trường sắp xếp
            sort_field = "UpdatedDate"  # Sử dụng UpdatedDate để sắp xếp latest/oldest
            sort_direction = -1 if sort_order == "desc" else 1
            sort_criteria = [(sort_field, sort_direction)]
        elif sort_field:
            if sort_field not in ["PriceVND", "ProductTitle", "Sales", "UpdatedTime"]:
                return jsonify({"success": False, "error": f"Invalid sort field: {sort_field}"}), 400
            sort_direction = 1 if sort_order == "asc" else -1
            sort_criteria = [(sort_field, sort_direction)]

        # Thực hiện truy vấn MongoDB
        total_products = product_collection.count_documents(query)
        total_pages = (total_products + limit - 1) // limit  # Tính tổng số trang

        # Kiểm tra nếu page vượt quá tổng số trang
        if page > total_pages:
            return jsonify({"success": False, "error": "Page number exceeds total pages"}), 400

        # Tính offset dựa trên trang hiện tại
        offset = (page - 1) * limit

        # Lấy dữ liệu từ MongoDB và áp dụng sắp xếp nếu có
        products_cursor = product_collection.find(query, {"_id": 0})
        if sort_criteria:
            products_cursor = products_cursor.sort(sort_criteria)
        products = list(products_cursor.skip(offset).limit(limit))

        # Trả về kết quả
        return jsonify({
            "success": True,
            "total_products": total_products,
            "total_pages": total_pages,
            "current_page": page,
            "products": products
        }), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    
@product_bp.route("/add", methods=["POST"])
def add_product():
    """
    API thêm sản phẩm mới.
    """
    try:
        db = get_db()
        product_collection = db.products
        # Lấy dữ liệu từ request
        product_data = request.get_json()

        # Các trường bắt buộc
        required_fields = ["ProductTitle", "ProductType"]

        # Các trường không được phép gán thủ công
        prohibited_fields = ["ProductId", "CreatedTime", "UpdatedTime"]

        # Các trường không bắt buộc nhưng cần để trống nếu không được cung cấp
        optional_fields = [
            "Category", "Colour", "Description_Paragraph", "Gender", "PriceUSD", 
            "PriceVND", "Sales", "Sizes", "SubCategory", "Usage", "Image", "ImageURL", "Stock"
        ]

        # Kiểm tra các trường bắt buộc
        missing_fields = [field for field in required_fields if field not in product_data]
        if missing_fields:
            return jsonify({
                "success": False,
                "error": f"Missing required fields: {', '.join(missing_fields)}"
            }), 400

        # Kiểm tra các trường không được phép gán thủ công
        manual_fields = [field for field in prohibited_fields if field in product_data]
        if manual_fields:
            return jsonify({
                "success": False,
                "error": f"Fields not allowed to be manually set: {', '.join(manual_fields)}"
            }), 400

        # Gán giá trị mặc định cho các trường không bắt buộc nếu không được cung cấp
        for field in optional_fields:
            if field not in product_data:
                product_data[field] = None if field != "Sizes" else []

        # Lấy ProductId tiếp theo
        last_product = product_collection.find_one(sort=[("ProductId", -1)])
        next_id = int(last_product["ProductId"]) + 1 if last_product else 1
        product_data["ProductId"] = f"{next_id:03}"

        # Gán thời gian tạo và cập nhật
        current_time = get_current_time()
        product_data["CreatedTime"] = current_time
        product_data["UpdatedTime"] = current_time

        # Thêm sản phẩm vào cơ sở dữ liệu
        product_collection.insert_one(product_data)

        return jsonify({"success": True, "message": "Product added successfully."}), 201

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    
@product_bp.route("/update/<product_id>", methods=["PUT"])
def update_product(product_id):
    """
    API cập nhật sản phẩm.
    """
    try:
        db = get_db()
        product_collection = db.products
        # Lấy dữ liệu từ request
        update_data = request.get_json()

        # Các trường không được phép cập nhật
        prohibited_fields = ["ProductId", "CreatedTime", "UpdatedTime"]

        # Kiểm tra các trường không được phép
        manual_fields = [field for field in prohibited_fields if field in update_data]
        if manual_fields:
            return jsonify({
                "success": False,
                "error": f"Fields not allowed to be manually updated: {', '.join(manual_fields)}"
            }), 400

        # Gán thời gian cập nhật
        update_data["UpdatedTime"] = get_current_time()

        # Cập nhật sản phẩm trong cơ sở dữ liệu
        result = product_collection.update_one({"ProductId": product_id}, {"$set": update_data})

        if result.matched_count == 0:
            return jsonify({"success": False, "error": "Product not found."}), 404

        return jsonify({"success": True, "message": "Product updated successfully."}), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    
@product_bp.route("/delete/<product_id>", methods=["DELETE"])
def delete_product(product_id):
    """
    API xóa sản phẩm.
    """
    try:
        db = get_db()
        product_collection = db.products
        # Xóa sản phẩm khỏi cơ sở dữ liệu
        result = product_collection.delete_one({"ProductId": product_id})

        if result.deleted_count == 0:
            return jsonify({"success": False, "error": "Product not found."}), 404

        return jsonify({"success": True, "message": "Product deleted successfully."}), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
