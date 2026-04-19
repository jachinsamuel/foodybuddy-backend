from flask import request, jsonify
from database import get_db
import psycopg2.extras

def register_favorites_routes(app):
    
    @app.route("/favorites", methods=['GET'])
    def get_favorites():
        """Get list of favorited items for current user"""
        try:
            user_id = request.args.get('user_id', type=int)
            
            if not user_id:
                return jsonify({"error": "user_id required"}), 400
            
            conn = get_db()
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # Get all favorite items for this user
            cur.execute("""
                SELECT 
                    m.id, m.name, m.price, m.category, m.type, m.image_url
                FROM favorites f
                JOIN menu_items m ON f.item_id = m.id
                WHERE f.user_id = %s
                ORDER BY f.created_at DESC
            """, (user_id,))
            
            items = [dict(row) for row in cur.fetchall()]
            cur.close()
            conn.close()
            
            return jsonify(items), 200
        except Exception as e:
            print(f"Error getting favorites: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/favorites/<int:item_id>", methods=['POST'])
    def toggle_favorite(item_id):
        """Toggle favorite status for an item"""
        try:
            data = request.json or {}
            user_id = data.get('user_id') or request.args.get('user_id', type=int)
            
            if not user_id:
                return jsonify({"error": "user_id required"}), 400
            
            conn = get_db()
            cur = conn.cursor()
            
            # Check if favorite already exists
            cur.execute("""
                SELECT id FROM favorites 
                WHERE user_id = %s AND item_id = %s
            """, (user_id, item_id))
            
            existing = cur.fetchone()
            
            if existing:
                # Remove favorite
                cur.execute("""
                    DELETE FROM favorites 
                    WHERE user_id = %s AND item_id = %s
                """, (user_id, item_id))
            else:
                # Add favorite
                cur.execute("""
                    INSERT INTO favorites (user_id, item_id) 
                    VALUES (%s, %s)
                """, (user_id, item_id))
            
            conn.commit()
            cur.close()
            conn.close()
            
            return jsonify({"success": True}), 200
        except Exception as e:
            print(f"Error toggling favorite: {e}")
            return jsonify({"error": str(e)}), 500

