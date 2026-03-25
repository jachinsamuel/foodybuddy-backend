from flask import Blueprint, jsonify
import psycopg2.extras
from db import get_db

admin_routes = Blueprint("admin", __name__)

@admin_routes.route("/admin/orders", methods=["GET"])
def get_orders():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("SELECT * FROM orders")
    orders = cur.fetchall()

    return jsonify(orders)
