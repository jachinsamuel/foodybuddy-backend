from flask import request, jsonify
import os
import hmac
import hashlib
import psycopg2
import psycopg2.extras
import random
from config import razorpay_client
from database import get_db
from whatsapp import _send_wa_customer

def register_payment_routes(app):
    @app.route("/create-order", methods=["POST"])
    def create_order():
        # Check if shop is open
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT is_open FROM shop_status ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        is_open = row[0] if row else True
        cur.close()
        conn.close()
        
        if not is_open:
            return jsonify({"error": "Shop is currently closed"}), 400
        
        data=request.json; amount=data["total"]*100
        from datetime import datetime
        order=razorpay_client.order.create({"amount":amount,"currency":"INR","receipt":f"fb_{data['name']}_{int(datetime.now().timestamp())}","notes":{"name":data["name"],"phone":data["phone"]}})
        return jsonify({"order_id":order["id"],"amount":amount,"key_id":os.environ.get("RAZORPAY_KEY_ID")})

    @app.route("/verify-payment", methods=["POST"])
    def verify_payment():
        data=request.json
        body=data["razorpay_order_id"]+"|"+data["razorpay_payment_id"]
        expected=hmac.new(os.environ.get("RAZORPAY_KEY_SECRET").encode(),body.encode(),hashlib.sha256).hexdigest()
        if expected!=data["razorpay_signature"]: return jsonify({"status":"failed"}),400
        conn=get_db(); cur=conn.cursor()
        cur.execute("INSERT INTO orders (order_id,payment_id,name,phone,items,total,token_type,special_instructions) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            (data["razorpay_order_id"],data["razorpay_payment_id"],data["name"],data["phone"],psycopg2.extras.Json(data["items"]),data["total"],data["token_type"],data.get("specialInstructions","")))
        conn.commit(); cur.close(); conn.close()
        _send_wa_customer(data)
        return jsonify({"status":"success","order_id":data["razorpay_order_id"]})

    @app.route("/place-cash-order", methods=["POST"])
    def place_cash_order():
        # Check if shop is open
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT is_open FROM shop_status ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        is_open = row[0] if row else True
        
        if not is_open:
            cur.close()
            conn.close()
            return jsonify({"error": "Shop is currently closed"}), 400
        
        data = request.json
        order_id = f"FB{random.randint(10000,99999)}"
        token_type = data.get("token_type") or data.get("tokenType", "dine-in")

        cur.execute(
            "INSERT INTO orders (order_id, payment_id, name, phone, items, total, token_type, special_instructions, status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'new')",
            (order_id, "CASH", data["name"], data["phone"],
             psycopg2.extras.Json(data["items"]),
             data["total"], token_type, data.get("specialInstructions",""))
        )
        conn.commit(); cur.close(); conn.close()

        _send_wa_customer({**data, "razorpay_order_id": order_id})

        return jsonify({"status": "success", "order_id": order_id})
