from flask import request, jsonify, redirect
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
            
            # PayU hash format: key|txnid|amount|productinfo|firstname|email|udf1|udf2|udf3|udf4|udf5||||||salt
            hash_string = f"{merchant_key}|{txnid}|{amount}|{productinfo}|{firstname}|{email}|||||||||||{merchant_salt}"
            hash_value = generate_hash(hash_string, merchant_salt)
            
            print(f"DEBUG: PayU Order created - txnid: {txnid}, amount: {amount}")
            print(f"DEBUG: Hash string: {hash_string}")
            print(f"DEBUG: Hash value: {hash_value}")
            
            # Store in session for callback
            import json
            order_info = {
                "txnid": txnid,
                "name": firstname,
                "phone": phone,
                "email": email,
                "amount": amount,
                "items": data.get("items", []),
                "total": data.get("total", 0),
                "token_type": data.get("token_type", "dine-in"),
                "specialInstructions": data.get("specialInstructions", "")
            }
            
            return jsonify({
                "txnid": txnid,
                "amount": amount,
                "merchant_key": merchant_key,
                "productinfo": productinfo,
                "firstname": firstname,
                "email": email,
                "phone": phone,
                "hash": hash_value,
                "payu_api_base": os.environ.get("PAYU_API_BASE", "https://test.payu.in"),
                "order_info": order_info
            }), 200
            
        except Exception as e:
            print(f"ERROR in payu_create_order: {str(e)}")
            return jsonify({"error": str(e)}), 500
    
    
    @app.route("/payu/success", methods=["POST"])
    def payu_success():
        """PayU success callback"""
        try:
            data = request.form
            print(f"DEBUG: PayU Success Response: {dict(data)}")
            
            txnid = data.get("txnid")
            status = data.get("status")
            
            if status != "success":
                print(f"ERROR: Payment failed with status: {status}")
                # Redirect to failure page
                return redirect(f"/#/failed?txnid={txnid}&reason={data.get('error', 'Payment failed')}")
            
            # Verify hash
            merchant_salt = os.environ.get("PAYU_MERCHANT_SALT")
            hash_value = data.get("hash")
            
            # Verify hash - response format: salt|status|txnid
            verify_string = f"{merchant_salt}|{status}|{txnid}"
            expected_hash_v1 = hashlib.sha512((verify_string + merchant_salt).encode()).hexdigest()
            
            print(f"DEBUG: Expected hash: {expected_hash_v1}")
            print(f"DEBUG: Received hash: {hash_value}")
            
            # PayU returns both v1 and v2 hashes, check against v1
            if hash_value != expected_hash_v1:
                print("ERROR: Hash verification failed!")
                return redirect(f"/#/failed?txnid={txnid}&reason=Hash%20verification%20failed")
            
            print("DEBUG: Hash verified successfully")
            
            # Extract order details from PayU response
            firstname = data.get("firstname", "")
            phone = data.get("phone", "")
            productinfo = data.get("productinfo", "")
            
            # Get order data from sessionStorage (passed via hidden field or from DB)
            # For now, we'll store minimal info and retrieve from sessionStorage on frontend
            
            # Store order in database
            try:
                conn = get_db()
                cur = conn.cursor()
                
                # Get items and total from the productinfo or use default
                items = []
                total = float(data.get("amount", 0))
                
                cur.execute(
                    "INSERT INTO orders (order_id, payment_id, name, phone, items, total, token_type, special_instructions, status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'new')",
                    (txnid, data.get("payuMoneyId", ""), firstname, phone, psycopg2.extras.Json(items), total, "dine-in", "")
                )
                conn.commit()
                cur.close()
                conn.close()
                
                print(f"DEBUG: Order created: {txnid}")
            except Exception as db_error:
                print(f"WARNING: Could not save order to DB: {str(db_error)}")
            
            # Send WhatsApp
            try:
                _send_wa_customer({
                    "name": firstname,
                    "phone": phone,
                    "order_id": txnid,
                    "total": total
                })
                print("DEBUG: WhatsApp notification sent")
            except Exception as e:
                print(f"WARNING: WhatsApp notification failed: {str(e)}")
            
            # Redirect to success page with order ID
            return redirect(f"/#/success?order_id={txnid}")
            
        except Exception as e:
            print(f"ERROR in payu_success: {str(e)}")
            return redirect(f"/#/failed?reason={str(e)}")
    
    
    @app.route("/payu/failed", methods=["POST"])
    def payu_failed():
        """PayU failure callback"""
        try:
            data = request.form
            print(f"DEBUG: PayU Failed Response: {dict(data)}")
            
            txnid = data.get("txnid")
            error = data.get("error", "Payment failed")
            
            return redirect(f"/#/failed?txnid={txnid}&reason={error}")
            
        except Exception as e:
            print(f"ERROR in payu_failed: {str(e)}")
            return redirect(f"/#/failed?reason={str(e)}")
    
    
    @app.route("/place-cash-order", methods=["POST"])
    def place_cash_order():
        """Place cash order"""
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
