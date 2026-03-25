from flask import Flask
from flask_cors import CORS
from db import init_db

from auth import auth_routes
from payments import payment_routes

app = Flask(__name__)
CORS(app)

app.register_blueprint(auth_routes)
app.register_blueprint(payment_routes)

@app.route("/")
def index():
    return {"status":"Foody Buddy API running!"}

init_db()

if __name__ == "__main__":
    app.run(debug=True)
