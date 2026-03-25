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

    if not name or not password:
        return jsonify({"error": "Name and password are required"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    role = "admin" if password == ADMIN_PASSWORD else "user"
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    conn = get_db(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("SELECT id FROM users WHERE LOWER(name) = LOWER(%s)", (name,))
    if cur.fetchone():
        return jsonify({"error": "This name is already taken."}), 400

    cur.execute(
        "INSERT INTO users (name, phone, password, role) VALUES (%s,%s,%s,%s) RETURNING id, name, phone, role",
        (name, phone, hashed, role)
    )
    user = dict(cur.fetchone())
    conn.commit(); cur.close(); conn.close()
    return jsonify({"user": user}), 201

@auth_routes.route("/auth/login", methods=["POST"])
def login():
    data = request.json
    name = data.get("name","").strip()
    password = data.get("password","")

    conn = get_db(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM users WHERE LOWER(name) = LOWER(%s)", (name,))
    user = cur.fetchone()
    cur.close(); conn.close()

    if not user:
        return jsonify({"error": "No account found"}), 401
    if not bcrypt.checkpw(password.encode(), user["password"].encode()):
        return jsonify({"error": "Incorrect password"}), 401

    return jsonify({"user": { "id":user["id"], "name":user["name"], "phone":user["phone"], "role":user["role"] }})
