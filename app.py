from flask import Flask
from flask_cors import CORS
from database import init_db
from auth import auth_bp
from menu import menu_bp
from orders import orders_bp

app = Flask(__name__)
CORS(app)

# Register all blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(menu_bp)
app.register_blueprint(orders_bp)

# Health check
@app.route("/")
def index():
    return {"status": "Foody Buddy API running!"}

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
