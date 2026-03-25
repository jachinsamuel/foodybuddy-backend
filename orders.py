from flask import Blueprint, jsonify
import psycopg2.extras
from db import get_db

order_routes = Blueprint("orders", __name__)

@order_routes.route("/orders/history/<phone>", methods=["GET"])
def history(phone):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("SELECT * FROM orders WHERE phone=%s", (phone,))
    data = cur.fetchall()

    return jsonify(data)
