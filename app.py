from flask import Flask, jsonify
from flask_cors import CORS
from config import cloudinary
from database import init_db
from auth_routes import register_auth_routes
from menu_routes import register_menu_routes
from order_routes import register_order_routes
from payment_routes import register_payment_routes
from admin_routes import register_admin_routes
from favorites_routes import register_favorites_routes
from shop_status_routes import register_shop_status_routes
from calculator_routes import register_calculator_routes

app = Flask(__name__)
CORS(app)

# Register all route modules
register_auth_routes(app)
register_menu_routes(app)
register_order_routes(app)
register_payment_routes(app)
register_admin_routes(app)
register_favorites_routes(app)
register_shop_status_routes(app)
register_calculator_routes(app)

@app.route("/")
def index(): 
    return jsonify({"status":"Foody Buddy API running!"})

# Initialize database
init_db()

if __name__ == "__main__":
    app.run(debug=True)
