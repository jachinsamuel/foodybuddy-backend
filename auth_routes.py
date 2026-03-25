from flask import request, jsonify
import psycopg2
import psycopg2.extras
import bcrypt
from config import ADMIN_PASSWORD
from database import get_db

def register_auth_routes(app):
    @app.route("/auth/register", methods=["POST"])
    def register():
        data     = request.json
        name     = data.get("name","").strip()
        password = data.get("password","")
        phone    = data.get("phone","").strip()

        if not name or not password:
            return jsonify({"error": "Name and password are required"}), 400
        if len(password) < 6:
            return jsonify({"error": "Password must be at least 6 characters"}), 400

        # Check if admin password
        role = "admin" if password == ADMIN_PASSWORD else "user"

        # Hash password
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

        conn = get_db(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Check if name already exists
        cur.execute("SELECT id FROM users WHERE LOWER(name) = LOWER(%s)", (name,))
        if cur.fetchone():
            cur.close(); conn.close()
            return jsonify({"error": "This name is already taken. Please use a different name."}), 400

        cur.execute(
            "INSERT INTO users (name, phone, password, role) VALUES (%s,%s,%s,%s) RETURNING id, name, phone, role",
            (name, phone, hashed, role)
        )
        user = dict(cur.fetchone())
        conn.commit(); cur.close(); conn.close()
        return jsonify({"user": user}), 201

    @app.route("/auth/login", methods=["POST"])
    def login():
        data     = request.json
        name     = data.get("name","").strip()
        password = data.get("password","")

        if not name or not password:
            return jsonify({"error": "Name and password are required"}), 400

        conn = get_db(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM users WHERE LOWER(name) = LOWER(%s)", (name,))
        user = cur.fetchone()
        cur.close(); conn.close()

        if not user:
            return jsonify({"error": "No account found with that name"}), 401
        if not bcrypt.checkpw(password.encode(), user["password"].encode()):
            return jsonify({"error": "Incorrect password"}), 401

        return jsonify({"user": { "id":user["id"], "name":user["name"], "phone":user["phone"], "role":user["role"] }})

    @app.route("/auth/update-profile", methods=["POST"])
    def update_profile():
        data     = request.json
        user_id  = data.get("user_id")
        name     = data.get("name","").strip()
        phone    = data.get("phone","").strip()

        if not user_id or not name:
            return jsonify({"error": "User ID and name are required"}), 400

        conn = get_db(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Check if name is taken by someone else
        cur.execute("SELECT id FROM users WHERE LOWER(name) = LOWER(%s) AND id != %s", (name, user_id))
        if cur.fetchone():
            cur.close(); conn.close()
            return jsonify({"error": "This name is already taken"}), 400

        cur.execute(
            "UPDATE users SET name=%s, phone=%s WHERE id=%s RETURNING name, phone, role",
            (name, phone, user_id)
        )
        user = cur.fetchone()
        conn.commit(); cur.close(); conn.close()
        return jsonify({ "name": user["name"], "phone": user["phone"], "role": user["role"] })
