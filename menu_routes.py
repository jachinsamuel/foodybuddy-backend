from flask import request, jsonify
import psycopg2
import psycopg2.extras
import cloudinary.uploader
from database import get_db

def register_menu_routes(app):
    # ── helpers ──────────────────────────────────────────────────────────────
    def _fetch_addons(cur, item_ids):
        """Return a dict: menu_item_id → [addon, ...]"""
        if not item_ids:
            return {}
        cur.execute(
            "SELECT * FROM menu_addons WHERE menu_item_id = ANY(%s) ORDER BY id",
            (list(item_ids),)
        )
        rows = cur.fetchall()
        result = {i: [] for i in item_ids}
        for r in rows:
            result[r["menu_item_id"]].append(dict(r))
        return result

    def _items_with_addons(cur, items):
        ids = [i["id"] for i in items]
        addons_map = _fetch_addons(cur, ids)
        out = []
        for i in items:
            d = dict(i)
            d["addons"] = addons_map.get(i["id"], [])
            out.append(d)
        return out

    # ── public menu ──────────────────────────────────────────────────────────
    @app.route("/menu", methods=["GET"])
    def get_menu():
        conn = get_db(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM menu_items WHERE available=TRUE ORDER BY category, name")
        items = cur.fetchall()
        result = _items_with_addons(cur, items)
        cur.close(); conn.close()
        return jsonify(result)

    # ── admin menu ────────────────────────────────────────────────────────────
    @app.route("/admin/menu", methods=["GET"])
    def get_admin_menu():
        conn = get_db(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM menu_items ORDER BY category, name")
        items = cur.fetchall()
        result = _items_with_addons(cur, items)
        cur.close(); conn.close()
        return jsonify(result)

    @app.route("/admin/menu", methods=["POST"])
    def add_menu_item():
        name     = request.form.get("name")
        price    = request.form.get("price")
        category = request.form.get("category")
        type_    = request.form.get("type", "veg")
        addons   = request.form.get("addons", "[]")   # JSON string
        image    = request.files.get("image")

        if not all([name, price, category]):
            return jsonify({"error": "Missing fields"}), 400

        import json
        print(f"[ADD_ITEM] Raw addons field: {repr(addons)}")
        try:
            addons_list = json.loads(addons)   # [{name, price}, ...]
            print(f"[ADD_ITEM] Parsed addons_list: {addons_list}")
        except Exception as e:
            print(f"[ADD_ITEM] JSON parse error: {e}")
            addons_list = []

        image_url = None
        if image:
            result = cloudinary.uploader.upload(image, folder="foodybuddy")
            image_url = result["secure_url"]

        conn = get_db(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "INSERT INTO menu_items (name,price,category,type,image_url) VALUES (%s,%s,%s,%s,%s) RETURNING *",
            (name, int(price), category, type_, image_url)
        )
        item = cur.fetchone()
        item_id = item["id"]
        print(f"[ADD_ITEM] Created item {item_id}")

        # insert addons
        for addon in addons_list:
            if addon.get("name","").strip():
                print(f"[ADD_ITEM] Inserting addon: {addon}")
                cur.execute(
                    "INSERT INTO menu_addons (menu_item_id, name, price) VALUES (%s,%s,%s)",
                    (item_id, addon["name"].strip(), int(addon.get("price", 0)))
                )
                print(f"[ADD_ITEM] Inserted successfully")

        conn.commit()
        print(f"[ADD_ITEM] Committed transaction")

        # fetch addons back
        cur.execute("SELECT * FROM menu_addons WHERE menu_item_id=%s ORDER BY id", (item_id,))
        fetched = cur.fetchall()
        print(f"[ADD_ITEM] Fetched {len(fetched)} addons: {fetched}")
        item = dict(item)
        item["addons"] = [dict(r) for r in fetched]
        cur.close(); conn.close()
        return jsonify(item), 201

    @app.route("/admin/menu/<int:item_id>", methods=["PUT"])
    def edit_menu_item(item_id):
        name     = request.form.get("name")
        price    = request.form.get("price")
        category = request.form.get("category")
        type_    = request.form.get("type")
        addons   = request.form.get("addons")          # JSON string or None
        image    = request.files.get("image")

        print(f"[EDIT_ITEM] item_id={item_id}, addons={repr(addons)}")

        conn = get_db(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        if image:
            result = cloudinary.uploader.upload(image, folder="foodybuddy")
            cur.execute("UPDATE menu_items SET image_url=%s WHERE id=%s", (result["secure_url"], item_id))
        if name:     cur.execute("UPDATE menu_items SET name=%s     WHERE id=%s", (name, item_id))
        if price:    cur.execute("UPDATE menu_items SET price=%s    WHERE id=%s", (int(price), item_id))
        if category: cur.execute("UPDATE menu_items SET category=%s WHERE id=%s", (category, item_id))
        if type_:    cur.execute("UPDATE menu_items SET type=%s     WHERE id=%s", (type_, item_id))

        # replace addons if provided
        if addons is not None:
            import json
            try:
                addons_list = json.loads(addons)
                print(f"[EDIT_ITEM] Parsed addons_list: {addons_list}")
            except Exception as e:
                print(f"[EDIT_ITEM] JSON parse error: {e}")
                addons_list = []
            print(f"[EDIT_ITEM] Deleting old addons and inserting {len(addons_list)} new ones")
            cur.execute("DELETE FROM menu_addons WHERE menu_item_id=%s", (item_id,))
            for addon in addons_list:
                if addon.get("name", "").strip():
                    print(f"[EDIT_ITEM] Inserting addon: {addon}")
                    cur.execute(
                        "INSERT INTO menu_addons (menu_item_id, name, price) VALUES (%s,%s,%s)",
                        (item_id, addon["name"].strip(), int(addon.get("price", 0)))
                    )

        cur.execute("SELECT * FROM menu_items WHERE id=%s", (item_id,))
        item = dict(cur.fetchone())
        cur.execute("SELECT * FROM menu_addons WHERE menu_item_id=%s ORDER BY id", (item_id,))
        fetched = cur.fetchall()
        print(f"[EDIT_ITEM] Fetched {len(fetched)} addons for item {item_id}")
        item["addons"] = [dict(r) for r in fetched]
        conn.commit(); cur.close(); conn.close()
        return jsonify(item)

    @app.route("/admin/menu/<int:item_id>/toggle", methods=["PATCH"])
    def toggle_item(item_id):
        conn = get_db(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("UPDATE menu_items SET available=NOT available WHERE id=%s RETURNING *", (item_id,))
        item = dict(cur.fetchone())
        cur.execute("SELECT * FROM menu_addons WHERE menu_item_id=%s ORDER BY id", (item_id,))
        item["addons"] = [dict(r) for r in cur.fetchall()]
        conn.commit(); cur.close(); conn.close()
        return jsonify(item)

    @app.route("/admin/menu/<int:item_id>", methods=["DELETE"])
    def delete_item(item_id):
        conn = get_db(); cur = conn.cursor()
        # addons deleted automatically via CASCADE
        cur.execute("DELETE FROM menu_items WHERE id=%s", (item_id,))
        conn.commit(); cur.close(); conn.close()
        return jsonify({"status": "deleted"})

    # ── addon-only endpoints (for live add/remove without re-saving full form) ─
    @app.route("/admin/menu/<int:item_id>/addons", methods=["GET"])
    def get_addons(item_id):
        conn = get_db(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM menu_addons WHERE menu_item_id=%s ORDER BY id", (item_id,))
        addons = cur.fetchall(); cur.close(); conn.close()
        return jsonify(addons)

    @app.route("/admin/menu/<int:item_id>/addons", methods=["POST"])
    def add_addon(item_id):
        data  = request.get_json()
        name  = (data.get("name") or "").strip()
        price = int(data.get("price", 0))
        if not name:
            return jsonify({"error": "Addon name is required"}), 400
        conn = get_db(); cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "INSERT INTO menu_addons (menu_item_id, name, price) VALUES (%s,%s,%s) RETURNING *",
            (item_id, name, price)
        )
        addon = cur.fetchone(); conn.commit(); cur.close(); conn.close()
        return jsonify(addon), 201

    @app.route("/admin/addons/<int:addon_id>", methods=["DELETE"])
    def delete_addon(addon_id):
        conn = get_db(); cur = conn.cursor()
        cur.execute("DELETE FROM menu_addons WHERE id=%s", (addon_id,))
        conn.commit(); cur.close(); conn.close()
        return jsonify({"status": "deleted"})
