from flask import request, jsonify
import os
import psycopg2
import psycopg2.extras
import random
from database import get_db
from whatsapp import _send_wa_customer, _send_wa_canteen

def register_payment_routes(app):
    @app.route("/place-upi-order", methods=["POST"])
    def place_upi_order():
        data = request.json
        order_id = f"FB{random.randint(10000,99999)}"
        token_type = data.get("token_type") or data.get("tokenType", "dine-in")

        conn = get_db(); cur = conn.cursor()
        cur.execute(
            "INSERT INTO orders (order_id, payment_id, name, phone, items, total, token_type, status) VALUES (%s,%s,%s,%s,%s,%s,%s,'new')",
            (order_id, "UPI", data["name"], data["phone"],
             psycopg2.extras.Json(data["items"]),
             data["total"], token_type)
        )
        conn.commit(); cur.close(); conn.close()

        _send_wa_customer({**data, "razorpay_order_id": order_id, "payment_method": "UPI"})
        _send_wa_canteen({**data, "razorpay_order_id": order_id, "payment_method": "UPI"})

        return jsonify({"status": "success", "order_id": order_id})

    @app.route("/place-cash-order", methods=["POST"])
    def place_cash_order():
        data = request.json
        order_id = f"FB{random.randint(10000,99999)}"
        token_type = data.get("token_type") or data.get("tokenType", "dine-in")

        conn = get_db(); cur = conn.cursor()
        cur.execute(
            "INSERT INTO orders (order_id, payment_id, name, phone, items, total, token_type, status) VALUES (%s,%s,%s,%s,%s,%s,%s,'new')",
            (order_id, "CASH", data["name"], data["phone"],
             psycopg2.extras.Json(data["items"]),
             data["total"], token_type)
        )
        conn.commit(); cur.close(); conn.close()

        _send_wa_customer({**data, "razorpay_order_id": order_id, "payment_method": "CASH"})
        _send_wa_canteen({**data, "razorpay_order_id": order_id, "payment_method": "CASH"})

        return jsonify({"status": "success", "order_id": order_id})
