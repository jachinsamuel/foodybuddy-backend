from flask import request, jsonify
import psycopg2
import psycopg2.extras
from database import get_db
from whatsapp import _send_wa_ready

def register_admin_routes(app):
    @app.route("/admin/orders", methods=["GET"])
    def get_live_orders():
        conn=get_db(); cur=conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM orders WHERE status!='done' ORDER BY created_at DESC")
        orders=cur.fetchall(); cur.close(); conn.close(); return jsonify(orders)

    @app.route("/admin/history", methods=["GET"])
    def get_history():
        conn=get_db(); cur=conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM orders WHERE status='done' ORDER BY created_at DESC LIMIT 50")
        orders=cur.fetchall(); cur.close(); conn.close(); return jsonify(orders)

    @app.route("/admin/orders/<order_id>/status", methods=["POST"])
    def update_status(order_id):
        new_status=request.json["status"]
        conn=get_db(); cur=conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("UPDATE orders SET status=%s WHERE order_id=%s RETURNING *",(new_status,order_id))
        order=cur.fetchone(); conn.commit(); cur.close(); conn.close()
        if new_status=="ready" and order:
            _send_wa_ready(order['phone'], order['order_id'], order['token_type'])
        return jsonify({"status":"updated"})

    @app.route("/admin/orders/<order_id>/cancel", methods=["POST"])
    def cancel_order(order_id):
        conn=get_db(); cur=conn.cursor()
        cur.execute("DELETE FROM orders WHERE order_id=%s",(order_id,))
        conn.commit(); cur.close(); conn.close(); return jsonify({"status":"cancelled"})

    @app.route("/admin/clear-history", methods=["POST"])
    def clear_history():
        conn=get_db(); cur=conn.cursor()
        cur.execute("DELETE FROM orders WHERE status='done'")
        deleted = cur.rowcount
        conn.commit(); cur.close(); conn.close()
        return jsonify({"status": "cleared", "deleted": deleted})
