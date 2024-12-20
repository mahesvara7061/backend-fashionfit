from flask import Flask
from flask_cors import CORS
from database import close_db
from dotenv import load_dotenv

import os

load_dotenv()

def create_app():

    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
    app.config["MONGO_URI"] = os.getenv("MONGO_URI")
    
    from routes.cart.routes import cart_bp
    from routes.order.routes import order_bp
    from routes.coupon.routes import coupon_bp
    from routes.manager.routes import manager_bp
    from routes.stats.routes import stats_bp
    from services.ghtk_service import ghtk_bp
    from routes.product.routes import product_bp
    from routes.rating.routes import rating_bp
    from routes.user.routes import user_bp
    from routes.payment.routes import payment_bp

    # Đăng ký Blueprints
    app.register_blueprint(cart_bp)
    app.register_blueprint(order_bp)
    app.register_blueprint(coupon_bp)
    app.register_blueprint(ghtk_bp)
    app.register_blueprint(manager_bp)
    app.register_blueprint(stats_bp)
    app.register_blueprint(product_bp)
    app.register_blueprint(rating_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(payment_bp)

    # Đăng ký teardown app context để đóng kết nối MongoDB
    app.teardown_appcontext(close_db)

    # Đăng ký CORS
    CORS(app)
    
    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
