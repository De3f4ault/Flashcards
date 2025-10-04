from app import create_app
from app.extensions import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    # For SQLite, we need to recreate the table without the column
    with db.engine.connect() as conn:
        conn.execute(text("PRAGMA foreign_keys=off;"))
        conn.commit()

        conn.execute(
            text("""
            CREATE TABLE users_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(80) NOT NULL UNIQUE,
                email VARCHAR(120) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                ai_enabled BOOLEAN NOT NULL DEFAULT 1,
                ai_provider VARCHAR(20) DEFAULT 'gemini',
                created_at DATETIME,
                updated_at DATETIME
            );
        """)
        )
        conn.commit()

        conn.execute(
            text("""
            INSERT INTO users_new 
            SELECT id, username, email, password_hash, is_active, ai_enabled, ai_provider, created_at, updated_at 
            FROM users;
        """)
        )
        conn.commit()

        conn.execute(text("DROP TABLE users;"))
        conn.commit()

        conn.execute(text("ALTER TABLE users_new RENAME TO users;"))
        conn.commit()

        conn.execute(text("PRAGMA foreign_keys=on;"))
        conn.commit()

        print("✅ Migration complete! ai_credits column removed.")
