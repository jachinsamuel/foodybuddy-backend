import os
import psycopg2
import psycopg2.extras

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
        CREATE TABLE IF NOT EXISTS menu_addons (
            id           SERIAL PRIMARY KEY,
            menu_item_id INTEGER NOT NULL REFERENCES menu_items(id) ON DELETE CASCADE,
            name         TEXT    NOT NULL,
            price        INTEGER NOT NULL DEFAULT 0,
            created_at   TIMESTAMP DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS orders (
            id                SERIAL PRIMARY KEY,
            order_id          TEXT    UNIQUE NOT NULL,
            payment_id        TEXT,
            name              TEXT    NOT NULL,
            phone             TEXT    NOT NULL,
            items             JSONB   NOT NULL,
            total             INTEGER NOT NULL,
            token_type        TEXT    NOT NULL,
            status            TEXT    NOT NULL DEFAULT 'new',
            hidden_from_admin BOOLEAN NOT NULL DEFAULT FALSE,
            special_instructions TEXT,
            created_at        TIMESTAMP DEFAULT NOW()
        );
        ALTER TABLE orders ADD COLUMN IF NOT EXISTS hidden_from_admin BOOLEAN NOT NULL DEFAULT FALSE;
        ALTER TABLE orders ADD COLUMN IF NOT EXISTS special_instructions TEXT;
        
        -- Create indexes for faster queries
        CREATE INDEX IF NOT EXISTS idx_orders_phone ON orders(phone);
        CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
        CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at);
        CREATE INDEX IF NOT EXISTS idx_orders_date ON orders(DATE(created_at));
        CREATE INDEX IF NOT EXISTS idx_menu_category ON menu_items(category);
        CREATE INDEX IF NOT EXISTS idx_menu_available ON menu_items(available);
        CREATE INDEX IF NOT EXISTS idx_users_name ON users(LOWER(name));
        
        -- Favorites table
        CREATE TABLE IF NOT EXISTS favorites (
            id         SERIAL PRIMARY KEY,
            user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            item_id    INTEGER NOT NULL REFERENCES menu_items(id) ON DELETE CASCADE,
            created_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(user_id, item_id)
        );
        CREATE INDEX IF NOT EXISTS idx_favorites_user ON favorites(user_id);
        CREATE INDEX IF NOT EXISTS idx_favorites_item ON favorites(item_id);
    """)
    conn.commit(); cur.close(); conn.close()
