from flask import Flask
from app.routes.product_routes import bp as product_bp
from app.routes.payment_routes import bp as payment_bp
from app.routes.user_routes import bp as user_bp
from app.routes.rating_routes import bp as rating_bp
from flask_cors import CORS

def create_app():
    app = Flask(__name__)
    app.config.from_object("app.config.Config")

    # Đăng ký route cho sản phẩm và thanh toán
    app.register_blueprint(product_bp, url_prefix="/api/products")
    app.register_blueprint(payment_bp, url_prefix="/api/payment")
    app.register_blueprint(user_bp, url_prefix="/api/users")
    app.register_blueprint(rating_bp, url_prefix="/api/ratings")
    CORS(app)

    return app
