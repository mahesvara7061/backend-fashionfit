from flask import Blueprint, request, jsonify
from database import get_db
from datetime import datetime
import pytz

# Blueprint setup
rating_bp = Blueprint("rating", __name__, url_prefix='/api/rating')

# Helper function to get current time in GMT+7
def get_current_time():
    tz = pytz.timezone('Asia/Bangkok')
    return datetime.now(tz).isoformat()

# API to submit a product review and rating
@rating_bp.route("/submit", methods=["POST"])
def submit_review():
    """
    API to submit a review and rating for a product.
    """
    try:
        db = get_db()
        data = request.get_json()
        required_fields = ["ProductId", "UserId", "Rating", "Review"]
        
        # Check for missing fields
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({"success": False, "error": f"Missing fields: {', '.join(missing_fields)}"}), 400

        # Validate rating value
        if not (1 <= data["Rating"] <= 5):
            return jsonify({"success": False, "error": "Rating must be between 1 and 5."}), 400

        # Check if UserId exists
        user_exists = db.users.find_one({"UserId": data["UserId"]})
        if not user_exists:
            return jsonify({"success": False, "error": "Invalid UserId."}), 400

        # Check if ProductId exists
        product_exists = db.products.find_one({"ProductId": data["ProductId"]})
        if not product_exists:
            return jsonify({"success": False, "error": "Invalid ProductId."}), 400

        # Generate ReviewId
        last_review = db.ratings.find_one(sort=[("ReviewId", -1)])
        next_review_id = int(last_review["ReviewId"]) + 1 if last_review else 1

        # Create review document
        review = {
            "ReviewId": f"{next_review_id:03}",
            "ProductId": data["ProductId"],
            "UserId": data["UserId"],
            "Rating": data["Rating"],
            "Review": data["Review"],
            "CreatedTime": get_current_time()
        }

        # Insert into database
        db.ratings.insert_one(review)

        return jsonify({"success": True, "message": "Review submitted successfully."}), 201

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# API to fetch reviews for a product
@rating_bp.route("/product/<product_id>", methods=["GET"])
def get_reviews(product_id):
    """
    API to fetch reviews for a specific product.
    """
    try:
        db = get_db()
        reviews = list(db.ratings.find({"ProductId": product_id}, {"_id": 0}))
        
        if not reviews:
            return jsonify({"success": True, "message": "No reviews found.", "reviews": []}), 200

        return jsonify({"success": True, "reviews": reviews}), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# API to get average rating of a product
@rating_bp.route("/product/<product_id>/average", methods=["GET"])
def get_average_rating(product_id):
    """
    API to get the average rating of a product.
    """
    try:
        db = get_db()
        pipeline = [
            {"$match": {"ProductId": product_id}},
            {"$group": {
                "_id": "$ProductId",
                "averageRating": {"$avg": "$Rating"},
                "totalReviews": {"$sum": 1}
            }}
        ]
        result = list(db.ratings.aggregate(pipeline))

        if not result:
            return jsonify({"success": True, "message": "No ratings found.", "averageRating": 0, "totalReviews": 0}), 200

        return jsonify({
            "success": True,
            "averageRating": round(result[0]["averageRating"], 2),
            "totalReviews": result[0]["totalReviews"]
        }), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    
# API to fetch reviews by a specific user
@rating_bp.route("/user/<user_id>", methods=["GET"])
def get_reviews_by_user(user_id):
    """
    API to fetch all reviews submitted by a specific user.
    """
    try:
        db = get_db()
        # Check if UserId exists
        user_exists = db.users.find_one({"UserId": user_id})
        if not user_exists:
            return jsonify({"success": False, "error": "Invalid UserId."}), 400

        reviews = list(db.ratings.find({"UserId": user_id}, {"_id": 0}))

        if not reviews:
            return jsonify({"success": True, "message": "No reviews found.", "reviews": []}), 200

        return jsonify({"success": True, "reviews": reviews}), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# API to delete a review
@rating_bp.route("/delete/<review_id>", methods=["DELETE"])
def delete_review(review_id):
    """
    API to delete a review by its ReviewId.
    """
    try:
        db = get_db()
        result = db.ratings.delete_one({"ReviewId": review_id})

        if result.deleted_count == 0:
            return jsonify({"success": False, "error": "Review not found."}), 404

        return jsonify({"success": True, "message": "Review deleted successfully."}), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
