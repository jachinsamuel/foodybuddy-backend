from flask import Blueprint, jsonify
import psycopg2.extras
from db import get_db

menu_routes = Blueprint("menu", __name__)

@menu_routes.route("/menu", methods=["GET"])
def get_menu():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("SELECT * FROM menu_items WHERE available=TRUE")
    items = cur.fetchall()

    cur.close(); conn.close()
    return jsonify(items)
