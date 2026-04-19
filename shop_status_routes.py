from flask import request, jsonify
from database import get_db

def register_shop_status_routes(app):
    
    @app.route("/shop-status", methods=['GET'])
    def get_shop_status():
        """Get current shop open/closed status"""
        try:
            conn = get_db()
            cur = conn.cursor()
            
            cur.execute("SELECT is_open FROM shop_status ORDER BY id DESC LIMIT 1")
            row = cur.fetchone()
            
            is_open = row[0] if row else True
            
            cur.close()
            conn.close()
            
            return jsonify({"is_open": is_open}), 200
        except Exception as e:
            print(f"Error getting shop status: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/shop-status", methods=['POST'])
    def set_shop_status():
        """Set shop open/closed status (admin only)"""
        try:
            data = request.json or {}
            is_open = data.get('is_open')
            
            if is_open is None:
                return jsonify({"error": "is_open required"}), 400
            
            conn = get_db()
            cur = conn.cursor()
            
            # Try to update existing record
            cur.execute(
                "UPDATE shop_status SET is_open = %s, updated_at = NOW() WHERE id = 1",
                (is_open,)
            )
            
            # If no rows updated, insert new
            if cur.rowcount == 0:
                cur.execute(
                    "INSERT INTO shop_status (id, is_open) VALUES (1, %s)",
                    (is_open,)
                )
            
            conn.commit()
            cur.close()
            conn.close()
            
            return jsonify({"success": True, "is_open": is_open}), 200
        except Exception as e:
            print(f"Error setting shop status: {e}")
            return jsonify({"error": str(e)}), 500
