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
