from flask import request, jsonify
import psycopg2
import psycopg2.extras
from database import get_db

def register_order_routes(app):
    # Get order history for a specific user
    @app.route("/orders/history/<phone>", methods=["GET"])
    def get_user_history(phone):
        conn = get_db(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM orders WHERE phone = %s ORDER BY created_at DESC LIMIT 100", (phone,))
        orders = cur.fetchall(); cur.close(); conn.close()
        return jsonify(orders)

    # Cancel order by user
    @app.route("/orders/<order_id>/cancel", methods=["POST"])
    def user_cancel_order(order_id):
        conn = get_db(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM orders WHERE order_id = %s", (order_id,))
        order = cur.fetchone()
        if not order:
            return jsonify({"error": "Order not found"}), 404
        if order["status"] not in ["new"]:
            return jsonify({"error": "Cannot cancel — order is already being prepared"}), 400
        cur.execute("DELETE FROM orders WHERE order_id = %s", (order_id,))
        conn.commit(); cur.close(); conn.close()
        return jsonify({"status": "cancelled"})
