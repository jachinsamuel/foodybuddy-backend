from flask import request, jsonify
import psycopg2
import psycopg2.extras
import cloudinary.uploader
from database import get_db

def register_menu_routes(app):
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
