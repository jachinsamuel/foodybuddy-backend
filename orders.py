import os
import hmac
import hashlib
import razorpay
import psycopg2.extras
from datetime import datetime
from flask import Blueprint, request, jsonify
from twilio.rest import Client as TwilioClient
from database import get_db

orders_bp = Blueprint("orders", __name__)

# ── Razorpay ──────────────────────────────────────────────────────────────────
razorpay_client = razorpay.Client(auth=(
    os.environ.get("RAZORPAY_KEY_ID"),
    os.environ.get("RAZORPAY_KEY_SECRET")
))

# ── Twilio ────────────────────────────────────────────────────────────────────
twilio_client  = TwilioClient(
    os.environ.get("TWILIO_ACCOUNT_SID"),
    os.environ.get("TWILIO_AUTH_TOKEN")
)
TWILIO_NUMBER  = "whatsapp:+14155238886"
CANTEEN_NUMBER = "whatsapp:+91XXXXXXXXXX"   # replace with canteen number


# ── Create Razorpay order ─────────────────────────────────────────────────────
@orders_bp.route("/create-order", methods=["POST"])
def create_order():
    data   = request.json
    amount = data["total"] * 100
    order  = razorpay_client.order.create({
        "amount":   amount,
        "currency": "INR",
        "receipt":  f"fb_{data['name']}_{int(datetime.now().timestamp())}",
        "notes":    {"name": data["name"], "phone": data["phone"]}
    })
    return jsonify({
        "order_id": order["id"],
        "amount":   amount,
        "key_id":   os.environ.get("RAZORPAY_KEY_ID")
    })


# ── Verify payment and save order ─────────────────────────────────────────────
@orders_bp.route("/verify-payment", methods=["POST"])
def verify_payment():
    data     = request.json
    body     = data["razorpay_order_id"] + "|" + data["razorpay_payment_id"]
    expected = hmac.new(
        os.environ.get("RAZORPAY_KEY_SECRET").encode(),
        body.encode(), hashlib.sha256
    ).hexdigest()

    if expected != data["razorpay_signature"]:
        return jsonify({"status": "failed"}), 400

    conn = get_db(); cur = conn.cursor()
    cur.execute(
        "INSERT INTO orders (order_id,payment_id,name,phone,items,total,token_type) VALUES (%s,%s,%s,%s,%s,%s,%s)",
        (data["razorpay_order_id"], data["razorpay_payment_id"],
         data["name"], data["phone"],
         psycopg2.extras.Json(data["items"]),
         data["total"], data.get("token_type") or data.get("tokenType","dine-in"))
    )
    conn.commit(); cur.close(); conn.close()

    _send_wa_customer(data)
    _send_wa_canteen(data)
    return jsonify({"status": "success", "order_id": data["razorpay_order_id"]})


# ── Cash order ────────────────────────────────────────────────────────────────
@orders_bp.route("/place-cash-order", methods=["POST"])
def place_cash_order():
    import random
    data       = request.json
    order_id   = f"FB{random.randint(10000,99999)}"
    token_type = data.get("token_type") or data.get("tokenType", "dine-in")

    conn = get_db(); cur = conn.cursor()
    cur.execute(
        "INSERT INTO orders (order_id,payment_id,name,phone,items,total,token_type,status) VALUES (%s,%s,%s,%s,%s,%s,%s,'new')",
        (order_id, "CASH", data["name"], data["phone"],
         psycopg2.extras.Json(data["items"]),
         data["total"], token_type)
    )
    conn.commit(); cur.close(); conn.close()

    _send_wa_customer({**data, "razorpay_order_id": order_id})
    _send_wa_canteen({**data,  "razorpay_order_id": order_id})
    return jsonify({"status": "success", "order_id": order_id})


# ── User order history ────────────────────────────────────────────────────────
@orders_bp.route("/orders/history/<phone>", methods=["GET"])
def get_user_history(phone):
    conn = get_db(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM orders WHERE phone=%s ORDER BY created_at DESC", (phone,))
    orders = cur.fetchall(); cur.close(); conn.close()
    return jsonify(orders)


# ── User cancel order ─────────────────────────────────────────────────────────
@orders_bp.route("/orders/<order_id>/cancel", methods=["POST"])
def user_cancel_order(order_id):
    conn = get_db(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM orders WHERE order_id=%s", (order_id,))
    order = cur.fetchone()
    if not order:
        return jsonify({"error": "Order not found"}), 404
    if order["status"] != "new":
        return jsonify({"error": "Cannot cancel — order is already being prepared"}), 400
    cur.execute("DELETE FROM orders WHERE order_id=%s", (order_id,))
    conn.commit(); cur.close(); conn.close()
    return jsonify({"status": "cancelled"})


# ── Admin — get live orders ───────────────────────────────────────────────────
@orders_bp.route("/admin/orders", methods=["GET"])
def get_live_orders():
    conn = get_db(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM orders WHERE status != 'done' ORDER BY created_at DESC")
    orders = cur.fetchall(); cur.close(); conn.close()
    return jsonify(orders)


# ── Admin — order history ─────────────────────────────────────────────────────
@orders_bp.route("/admin/history", methods=["GET"])
def get_history():
    conn = get_db(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM orders WHERE status='done' ORDER BY created_at DESC LIMIT 50")
    orders = cur.fetchall(); cur.close(); conn.close()
    return jsonify(orders)


# ── Admin — update order status ───────────────────────────────────────────────
@orders_bp.route("/admin/orders/<order_id>/status", methods=["POST"])
def update_status(order_id):
    new_status = request.json["status"]
    conn = get_db(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "UPDATE orders SET status=%s WHERE order_id=%s RETURNING *",
        (new_status, order_id)
    )
    order = cur.fetchone()
    conn.commit(); cur.close(); conn.close()

    if new_status == "ready" and order:
        twilio_client.messages.create(
            body=(f"Your order is ready for collection!\n\n"
                  f"Order: {order['order_id']}\nType: {order['token_type'].title()}\n\n"
                  f"Please collect from the counter."),
            from_=TWILIO_NUMBER,
            to=f"whatsapp:+91{order['phone']}"
        )
    return jsonify({"status": "updated"})


# ── Admin — cancel order ──────────────────────────────────────────────────────
@orders_bp.route("/admin/orders/<order_id>/cancel", methods=["POST"])
def cancel_order(order_id):
    conn = get_db(); cur = conn.cursor()
    cur.execute("DELETE FROM orders WHERE order_id=%s", (order_id,))
    conn.commit(); cur.close(); conn.close()
    return jsonify({"status": "cancelled"})


# ── WhatsApp helpers ──────────────────────────────────────────────────────────
def _send_wa_customer(data):
    items      = "\n".join([f"  {i['name']} x{i['qty']} — ₹{i['price']*i['qty']}" for i in data["items"]])
    token_type = data.get("token_type") or data.get("tokenType", "dine-in")
    twilio_client.messages.create(
        body=(f"Hi {data['name']}! Your order is confirmed.\n\n"
              f"Order: {data['razorpay_order_id']}\n{items}\n\n"
              f"Total: ₹{data['total']}\nType: {token_type.title()}\n\n"
              f"We'll notify you when it's ready!"),
        from_=TWILIO_NUMBER,
        to=f"whatsapp:+91{data['phone']}"
    )

def _send_wa_canteen(data):
    items      = "\n".join([f"  {i['name']} x{i['qty']}" for i in data["items"]])
    token_type = data.get("token_type") or data.get("tokenType", "dine-in")
    twilio_client.messages.create(
        body=(f"New Order!\nID: {data['razorpay_order_id']}\n"
              f"From: {data['name']} ({token_type.title()})\n"
              f"{items}\nTotal: ₹{data['total']}"),
        from_=TWILIO_NUMBER,
        to=CANTEEN_NUMBER
    )
