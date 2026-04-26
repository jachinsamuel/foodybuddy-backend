from flask import request, jsonify
import os
import hashlib
from datetime import datetime
import random
import psycopg2
import psycopg2.extras
from database import get_db
from whatsapp import _send_wa_customer

def generate_hash(data, salt):
    """Generate PayU hash signature using SHA-512"""
    text = data + salt
    hashObj = hashlib.sha512(text.encode('utf-8'))
    return hashObj.hexdigest()

def register_payu_routes(app):
    
    @app.route("/payu/create-order", methods=["POST"])
    def payu_create_order():
        """Create PayU order"""
        try:
            # Check shop status
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT is_open FROM shop_status ORDER BY id DESC LIMIT 1")
            row = cur.fetchone()
            is_open = row[0] if row else True
            cur.close()
            conn.close()
            
            if not is_open:
                return jsonify({"error": "Shop is currently closed"}), 400
            
            data = request.json
            
            # Generate unique transaction ID
            txnid = f"FB{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(100,999)}"
            
            amount = str(int(data["total"]))
            productinfo = "FoodyBuddy Order"
            firstname = data["name"]
            email = data.get("email", "customer@foodybuddy.in")
            phone = data["phone"]
            
            # Create hash
            merchant_key = os.environ.get("PAYU_MERCHANT_KEY")
            merchant_salt = os.environ.get("PAYU_MERCHANT_SALT")
            
            if not merchant_key or not merchant_salt:
                print("ERROR: PayU credentials not configured!")
                return jsonify({"error": "Payment gateway not configured"}), 500
            
            # PayU hash format: key|txnid|amount|productinfo|firstname|email|phone|||||||||salt
            hash_string = f"{merchant_key}|{txnid}|{amount}|{productinfo}|{firstname}|{email}|{phone}|||||||||{merchant_salt}"
            hash_value = generate_hash(hash_string, merchant_salt)
            
            print(f"DEBUG: PayU Order created - txnid: {txnid}, amount: {amount}")
            
            return jsonify({
                "txnid": txnid,
                "amount": amount,
                "merchant_key": merchant_key,
                "productinfo": productinfo,
                "firstname": firstname,
                "email": email,
                "phone": phone,
                "hash": hash_value,
                "payu_api_base": os.environ.get("PAYU_API_BASE", "https://api.payumoney.com")
            }), 200
            
        except Exception as e:
            print(f"ERROR in payu_create_order: {str(e)}")
            return jsonify({"error": str(e)}), 500
    
    
    @app.route("/payu/verify-payment", methods=["POST"])
    def payu_verify_payment():
        """Verify PayU payment"""
        try:
            data = request.json
            print(f"DEBUG: PayU Response: {data}")
            
            txnid = data.get("txnid")
            status = data.get("status")  # success or failure
            
            if status != "success":
                print(f"ERROR: Payment failed with status: {status}")
                return jsonify({"status": "failed", "error": "Payment failed"}), 400
            
            # Verify hash
            merchant_salt = os.environ.get("PAYU_MERCHANT_SALT")
            hash_value = data.get("hash")
            
            # PayU sends hash in format: salt|status|txnid
            verify_string = f"{merchant_salt}|{status}|{txnid}"
            expected_hash = generate_hash(verify_string, merchant_salt)
            
            print(f"DEBUG: Expected hash: {expected_hash}")
            print(f"DEBUG: Received hash: {hash_value}")
            
            if hash_value != expected_hash:
                print("ERROR: Hash verification failed!")
                return jsonify({"status": "failed", "error": "Hash verification failed"}), 400
            
            print("DEBUG: Hash verified successfully")
            
            # Get additional data from request
            order_data = data.get("orderData", {})
            name = data.get("firstname", order_data.get("name", ""))
            phone = data.get("phone", order_data.get("phone", ""))
            items = order_data.get("items", [])
            total = order_data.get("total", 0)
            token_type = order_data.get("token_type", "dine-in")
            special_instructions = order_data.get("specialInstructions", "")
            
            # Store order in database
            conn = get_db()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO orders (order_id, payment_id, name, phone, items, total, token_type, special_instructions, status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'new')",
                (txnid, data.get("payuMoneyId", ""), name, phone, psycopg2.extras.Json(items), total, token_type, special_instructions)
            )
            conn.commit()
            cur.close()
            conn.close()
            
            print(f"DEBUG: Order created: {txnid}")
            
            # Send WhatsApp
            try:
                combined_data = {**order_data, "order_id": txnid}
                _send_wa_customer(combined_data)
                print("DEBUG: WhatsApp notification sent")
            except Exception as e:
                print(f"WARNING: WhatsApp notification failed: {str(e)}")
            
            return jsonify({"status": "success", "order_id": txnid}), 200
            
        except Exception as e:
            print(f"ERROR in payu_verify_payment: {str(e)}")
            return jsonify({"status": "failed", "error": str(e)}), 500
    
    
    @app.route("/place-cash-order", methods=["POST"])
    def place_cash_order():
        """Place cash order (existing code)"""
        try:
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
                "INSERT INTO orders (order_id, name, phone, items, total, token_type, special_instructions, status) VALUES (%s,%s,%s,%s,%s,%s,%s,'new')",
                (order_id, data["name"], data["phone"], psycopg2.extras.Json(data["items"]),
                 data["total"], token_type, data.get("specialInstructions", ""))
            )
            conn.commit()
            cur.close()
            conn.close()
            
            print(f"DEBUG: Cash order created: {order_id}")
            
            try:
                _send_wa_customer({**data, "order_id": order_id})
            except Exception as e:
                print(f"WARNING: WhatsApp notification failed: {str(e)}")
            
            return jsonify({"status": "success", "order_id": order_id}), 200
        except Exception as e:
            print(f"ERROR in place_cash_order: {str(e)}")
            return jsonify({"error": str(e)}), 500
