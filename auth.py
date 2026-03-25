from flask import Blueprint, request, jsonify
import bcrypt, psycopg2.extras
from db import get_db
from config import ADMIN_PASSWORD

auth_routes = Blueprint("auth", __name__)

@auth_routes.route("/auth/register", methods=["POST"])
def register():
    data = request.json
    name = data.get("name","").strip()
    password = data.get("password","")
    phone = data.get("phone","").strip()

    role = "admin" if password == ADMIN_PASSWORD else "user"
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("SELECT id FROM users WHERE LOWER(name)=LOWER(%s)", (name,))
    if cur.fetchone():
        return jsonify({"error":"Name taken"}),400

    cur.execute(
        "INSERT INTO users (name,phone,password,role) VALUES (%s,%s,%s,%s) RETURNING id,name,phone,role",
        (name, phone, hashed, role)
    )

    user = dict(cur.fetchone())
    conn.commit()
    cur.close(); conn.close()

    return jsonify({"user": user}), 201
