from flask import Flask, request, jsonify
from flask_cors import CORS
import os, hmac, hashlib, psycopg2, psycopg2.extras
import razorpay, cloudinary, cloudinary.uploader
from twilio.rest import Client as TwilioClient
from datetime import datetime
import bcrypt

app = Flask(__name__)
CORS(app)

# ── Cloudinary ────────────────────────────────────────────────────────────────
cloudinary.config(
    cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key    = os.environ.get("CLOUDINARY_API_KEY"),
    api_secret = os.environ.get("CLOUDINARY_API_SECRET")
)

# ── Razorpay ──────────────────────────────────────────────────────────────────
razorpay_client = razorpay.Client(auth=(
    os.environ.get("RAZORPAY_KEY_ID"),
    os.environ.get("RAZORPAY_KEY_SECRET")
))

# ── Twilio ────────────────────────────────────────────────────────────────────
twilio_client  = TwilioClient(os.environ.get("TWILIO_ACCOUNT_SID"), os.environ.get("TWILIO_AUTH_TOKEN"))
TWILIO_NUMBER = "whatsapp:+14155238886"  # Twilio sandbox number for WhatsApp
CANTEEN_NUMBER = "whatsapp:+919944001925"   # replace with canteen number

# ── Admin password (set this in Render env vars) ──────────────────────────────
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "canteen@admin123")

# ── DB ────────────────────────────────────────────────────────────────────────
def get_db():
    return psycopg2.connect(os.environ.get("DATABASE_URL"))

def init_db():
    conn = get_db(); cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id         SERIAL PRIMARY KEY,
            name       TEXT    NOT NULL,
            phone      TEXT,
            password   TEXT    NOT NULL,
            role       TEXT    NOT NULL DEFAULT 'user',
            created_at TIMESTAMP DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS menu_items (
            id         SERIAL PRIMARY KEY,
            name       TEXT    NOT NULL,
            price      INTEGER NOT NULL,
            category   TEXT    NOT NULL,
            type       TEXT    NOT NULL DEFAULT 'veg',
            image_url  TEXT,
            available  BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS orders (
            id         SERIAL PRIMARY KEY,
            order_id   TEXT    UNIQUE NOT NULL,
            payment_id TEXT,
            name       TEXT    NOT NULL,
            phone      TEXT    NOT NULL,
            items      JSONB   NOT NULL,
            total      INTEGER NOT NULL,
            token_type TEXT    NOT NULL,
            status     TEXT    NOT NULL DEFAULT 'new',
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)
    conn.commit(); cur.close(); conn.close()


# ══════════════════════════════════════════════════════════════════════════════
#  AUTH
# ══════════════════════════════════════════════════════════════════════════════

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


# ══════════════════════════════════════════════════════════════════════════════
#  MENU
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/menu", methods=["GET"])
def get_menu():
    conn = get_db(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM menu_items WHERE available=TRUE ORDER BY category, name")
    items = cur.fetchall(); cur.close(); conn.close()
    return jsonify(items)

@app.route("/admin/menu", methods=["GET"])
def get_admin_menu():
    conn = get_db(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM menu_items ORDER BY category, name")
    items = cur.fetchall(); cur.close(); conn.close()
    return jsonify(items)

@app.route("/admin/menu", methods=["POST"])
def add_menu_item():
    name=request.form.get("name"); price=request.form.get("price")
    category=request.form.get("category"); type_=request.form.get("type","veg")
    image=request.files.get("image")
    if not all([name, price, category]): return jsonify({"error":"Missing fields"}), 400
    image_url = None
    if image:
        result = cloudinary.uploader.upload(image, folder="foodybuddy")
        image_url = result["secure_url"]
    conn=get_db(); cur=conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("INSERT INTO menu_items (name,price,category,type,image_url) VALUES (%s,%s,%s,%s,%s) RETURNING *",(name,int(price),category,type_,image_url))
    item=cur.fetchone(); conn.commit(); cur.close(); conn.close()
    return jsonify(item), 201

@app.route("/admin/menu/<int:item_id>", methods=["PUT"])
def edit_menu_item(item_id):
    name=request.form.get("name"); price=request.form.get("price")
    category=request.form.get("category"); type_=request.form.get("type")
    image=request.files.get("image")
    conn=get_db(); cur=conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if image:
        result=cloudinary.uploader.upload(image,folder="foodybuddy")
        cur.execute("UPDATE menu_items SET image_url=%s WHERE id=%s",(result["secure_url"],item_id))
    if name:     cur.execute("UPDATE menu_items SET name=%s     WHERE id=%s",(name,item_id))
    if price:    cur.execute("UPDATE menu_items SET price=%s    WHERE id=%s",(int(price),item_id))
    if category: cur.execute("UPDATE menu_items SET category=%s WHERE id=%s",(category,item_id))
    if type_:    cur.execute("UPDATE menu_items SET type=%s     WHERE id=%s",(type_,item_id))
    cur.execute("SELECT * FROM menu_items WHERE id=%s",(item_id,))
    item=cur.fetchone(); conn.commit(); cur.close(); conn.close()
    return jsonify(item)

@app.route("/admin/menu/<int:item_id>/toggle", methods=["PATCH"])
def toggle_item(item_id):
    conn=get_db(); cur=conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("UPDATE menu_items SET available=NOT available WHERE id=%s RETURNING *",(item_id,))
    item=cur.fetchone(); conn.commit(); cur.close(); conn.close()
    return jsonify(item)

@app.route("/admin/menu/<int:item_id>", methods=["DELETE"])
def delete_item(item_id):
    conn=get_db(); cur=conn.cursor()
    cur.execute("DELETE FROM menu_items WHERE id=%s",(item_id,))
    conn.commit(); cur.close(); conn.close()
    return jsonify({"status":"deleted"})

# Get order history for a specific user
@app.route("/orders/history/<phone>", methods=["GET"])
def get_user_history(phone):
    conn = get_db(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM orders WHERE phone = %s ORDER BY created_at DESC", (phone,))
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

# ══════════════════════════════════════════════════════════════════════════════
#  PAYMENTS
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/create-order", methods=["POST"])
def create_order():
    data=request.json; amount=data["total"]*100
    order=razorpay_client.order.create({"amount":amount,"currency":"INR","receipt":f"fb_{data['name']}_{int(datetime.now().timestamp())}","notes":{"name":data["name"],"phone":data["phone"]}})
    return jsonify({"order_id":order["id"],"amount":amount,"key_id":os.environ.get("RAZORPAY_KEY_ID")})

@app.route("/verify-payment", methods=["POST"])
def verify_payment():
    data=request.json
    body=data["razorpay_order_id"]+"|"+data["razorpay_payment_id"]
    expected=hmac.new(os.environ.get("RAZORPAY_KEY_SECRET").encode(),body.encode(),hashlib.sha256).hexdigest()
    if expected!=data["razorpay_signature"]: return jsonify({"status":"failed"}),400
    conn=get_db(); cur=conn.cursor()
    cur.execute("INSERT INTO orders (order_id,payment_id,name,phone,items,total,token_type) VALUES (%s,%s,%s,%s,%s,%s,%s)",
        (data["razorpay_order_id"],data["razorpay_payment_id"],data["name"],data["phone"],psycopg2.extras.Json(data["items"]),data["total"],data["token_type"]))
    conn.commit(); cur.close(); conn.close()
    _send_wa_customer(data); _send_wa_canteen(data)
    return jsonify({"status":"success","order_id":data["razorpay_order_id"]})

@app.route("/place-cash-order", methods=["POST"])
def place_cash_order():
    data = request.json
    import random
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

    _send_wa_customer({**data, "razorpay_order_id": order_id})
    _send_wa_canteen({**data, "razorpay_order_id": order_id})

    return jsonify({"status": "success", "order_id": order_id})
# ══════════════════════════════════════════════════════════════════════════════
#  WHATSAPP
# ══════════════════════════════════════════════════════════════════════════════

def _send_wa_customer(data):
    items="\n".join([f"  {i['name']} x{i['qty']} — ₹{i['price']*i['qty']}" for i in data["items"]])
    token_type = data.get("token_type") or data.get("tokenType", "dine-in")
    twilio_client.messages.create(
        body=f"Hi {data['name']}! Your order is confirmed.\n\nOrder: {data['razorpay_order_id']}\n{items}\n\nTotal: ₹{data['total']}\nType: {token_type.title()}\n\nWe'll notify you when it's ready.",
        from_=TWILIO_NUMBER, to=f"whatsapp:+91{data['phone']}")

def _send_wa_canteen(data):
    items="\n".join([f"  {i['name']} x{i['qty']}" for i in data["items"]])
    token_type = data.get("token_type") or data.get("tokenType", "dine-in")
    twilio_client.messages.create(
        body=f"New Order\nID: {data['razorpay_order_id']}\nFrom: {data['name']} ({token_type.title()})\n{items}\nTotal: ₹{data['total']}",
        from_=TWILIO_NUMBER, to=CANTEEN_NUMBER)


# ══════════════════════════════════════════════════════════════════════════════
#  ADMIN ORDERS
# ══════════════════════════════════════════════════════════════════════════════

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
        twilio_client.messages.create(
            body=f"Your order is ready for collection!\n\nOrder: {order['order_id']}\nType: {order['token_type'].title()}\n\nPlease collect from the counter.",
            from_=TWILIO_NUMBER, to=f"whatsapp:+91{order['phone']}")
    return jsonify({"status":"updated"})

@app.route("/admin/orders/<order_id>/cancel", methods=["POST"])
def cancel_order(order_id):
    conn=get_db(); cur=conn.cursor()
    cur.execute("DELETE FROM orders WHERE order_id=%s",(order_id,))
    conn.commit(); cur.close(); conn.close(); return jsonify({"status":"cancelled"})

@app.route("/")
def index(): return jsonify({"status":"Foody Buddy API running!"})
init_db()
if __name__ == "__main__":
    app.run(debug=True)
