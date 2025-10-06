"""
Migration script to add chat_sessions and chat_messages tables for Phase 2: AI Chat Interface
Run this script from the project root: python add_chat_tables.py
"""

import os
import sys
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app, db
from sqlalchemy import inspect, text


def table_exists(table_name):
    """Check if a table exists in the database"""
    inspector = inspect(db.engine)
    return table_name in inspector.get_table_names()


def add_chat_sessions_table():
    """Add chat_sessions table to the database"""

    if table_exists("chat_sessions"):
        print("✓ 'chat_sessions' table already exists. Skipping creation.")
        return False

    print("Creating 'chat_sessions' table...")

    # Create chat_sessions table
    db.engine.execute(
        text("""
        CREATE TABLE chat_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title VARCHAR(255) NOT NULL DEFAULT 'New Chat',
            document_id INTEGER,
            last_message_at DATETIME,
            message_count INTEGER NOT NULL DEFAULT 0,
            total_tokens_used INTEGER NOT NULL DEFAULT 0,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE SET NULL
        )
    """)
    )

    # Create indexes for better query performance
    print("Creating indexes for chat_sessions...")
    db.engine.execute(
        text("CREATE INDEX idx_chat_sessions_user_id ON chat_sessions(user_id)")
    )
    db.engine.execute(
        text("CREATE INDEX idx_chat_sessions_document_id ON chat_sessions(document_id)")
    )
    db.engine.execute(
        text(
            "CREATE INDEX idx_chat_sessions_last_message_at ON chat_sessions(last_message_at DESC)"
        )
    )

    print("✓ 'chat_sessions' table created successfully!")
    return True


def add_chat_messages_table():
    """Add chat_messages table to the database"""

    if table_exists("chat_messages"):
        print("✓ 'chat_messages' table already exists. Skipping creation.")
        return False

    print("Creating 'chat_messages' table...")

    # Create chat_messages table
    db.engine.execute(
        text("""
        CREATE TABLE chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            role VARCHAR(20) NOT NULL,
            content TEXT NOT NULL,
            tokens_used INTEGER NOT NULL DEFAULT 0,
            model_used VARCHAR(50),
            timestamp DATETIME NOT NULL,
            has_error BOOLEAN NOT NULL DEFAULT 0,
            error_message TEXT,
            FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
        )
    """)
    )

    # Create indexes for better query performance
    print("Creating indexes for chat_messages...")
    db.engine.execute(
        text("CREATE INDEX idx_chat_messages_session_id ON chat_messages(session_id)")
    )
    db.engine.execute(
        text("CREATE INDEX idx_chat_messages_timestamp ON chat_messages(timestamp ASC)")
    )
    db.engine.execute(
        text("CREATE INDEX idx_chat_messages_role ON chat_messages(role)")
    )

    print("✓ 'chat_messages' table created successfully!")
    return True


def verify_migration():
    """Verify the migration was successful"""
    inspector = inspect(db.engine)

    # Check chat_sessions table
    if not table_exists("chat_sessions"):
        print("✗ Migration failed: 'chat_sessions' table not found")
        return False

    sessions_columns = [col["name"] for col in inspector.get_columns("chat_sessions")]
    expected_sessions_columns = [
        "id",
        "user_id",
        "title",
        "document_id",
        "last_message_at",
        "message_count",
        "total_tokens_used",
        "created_at",
        "updated_at",
    ]

    missing_sessions_columns = [
        col for col in expected_sessions_columns if col not in sessions_columns
    ]
    if missing_sessions_columns:
        print(
            f"✗ Migration verification failed: Missing columns in chat_sessions: {missing_sessions_columns}"
        )
        return False

    # Check chat_messages table
    if not table_exists("chat_messages"):
        print("✗ Migration failed: 'chat_messages' table not found")
        return False

    messages_columns = [col["name"] for col in inspector.get_columns("chat_messages")]
    expected_messages_columns = [
        "id",
        "session_id",
        "role",
        "content",
        "tokens_used",
        "model_used",
        "timestamp",
        "has_error",
        "error_message",
    ]

    missing_messages_columns = [
        col for col in expected_messages_columns if col not in messages_columns
    ]
    if missing_messages_columns:
        print(
            f"✗ Migration verification failed: Missing columns in chat_messages: {missing_messages_columns}"
        )
        return False

    print("✓ Migration verification passed!")
    print(f"  - Table: chat_sessions")
    print(f"    Columns: {len(sessions_columns)}")
    print(f"    Indexes: 3 (user_id, document_id, last_message_at)")
    print(f"  - Table: chat_messages")
    print(f"    Columns: {len(messages_columns)}")
    print(f"    Indexes: 3 (session_id, timestamp, role)")

    return True


def main():
    """Main migration function"""
    print("=" * 60)
    print("AI Chat Interface Migration - Phase 2")
    print("=" * 60)
    print()

    # Create Flask app context
    app = create_app()

    with app.app_context():
        try:
            # Run migrations
            print("Step 1: Adding 'chat_sessions' table...")
            sessions_added = add_chat_sessions_table()
            print()

            print("Step 2: Adding 'chat_messages' table...")
            messages_added = add_chat_messages_table()
            print()

            # Verify migration
            print("Step 3: Verifying migration...")
            verification_passed = verify_migration()
            print()

            # Summary
            print("=" * 60)
            if (sessions_added or messages_added) and verification_passed:
                print("✓ Migration completed successfully!")
                print()
                print("Next steps:")
                print("  1. Restart your Flask application")
                print("  2. Navigate to /chat to access the AI Chat interface")
                print("  3. Create a new chat session to test the feature")
                print()
                print("Phase 2 Complete! You now have:")
                print("  ✓ Chat sessions with conversation history")
                print("  ✓ AI-powered responses using Gemini")
                print("  ✓ Document attachment for context-aware conversations")
                print("  ✓ Real-time chat interface")
            elif not (sessions_added or messages_added) and verification_passed:
                print("✓ Migration skipped (tables already exist)")
            else:
                print("✗ Migration verification failed")
            print("=" * 60)

        except Exception as e:
            print(f"\n✗ Migration failed with error:")
            print(f"  {str(e)}")
            print("\nPlease check your database configuration and try again.")
            import traceback

            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    main()
