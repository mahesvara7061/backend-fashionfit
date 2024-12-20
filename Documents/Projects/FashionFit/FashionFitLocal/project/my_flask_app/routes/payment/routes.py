from flask import Blueprint, request, jsonify
from services.paypal_service import create_order, capture_order

payment_bp = Blueprint("payment", __name__, url_prefix='/api/payment')

@payment_bp.route("/create", methods=["POST"])
def create_order_route():
    try:
        data = request.json
        amount = data.get("amount")
        currency = data.get("currency", "USD")
        return_url = data.get("return_url")
        cancel_url = data.get("cancel_url")
        if not amount or not return_url or not cancel_url:
            return jsonify({"error": "Missing required fields"}), 400
        result = create_order(amount, currency, return_url, cancel_url)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@payment_bp.route("/capture", methods=["POST"])
def capture_order_route():
    try:
        data = request.json
        order_id = data.get("order_id")
        if not order_id:
            return jsonify({"error": "Missing order_id"}), 400
        result = capture_order(order_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
