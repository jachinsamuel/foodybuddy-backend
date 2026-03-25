from flask import Blueprint, request, jsonify
import random, psycopg2.extras
from db import get_db

payment_routes = Blueprint("payments", __name__)

@payment_routes.route("/place-cash-order", methods=["POST"])
def place_cash_order():
    data = request.json

    order_id = f"FB{random.randint(10000,99999)}"

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO orders (order_id,payment_id,name,phone,items,total,token_type,status) VALUES (%s,%s,%s,%s,%s,%s,%s,'new')",
        (
            order_id,
            "CASH",
            data["name"],
            data["phone"],
            psycopg2.extras.Json(data["items"]),
            data["total"],
            data.get("token_type","dine-in")
        )
    )

    conn.commit()
    cur.close(); conn.close()

    return jsonify({
        "status": "success",
        "order_id": order_id
    })
