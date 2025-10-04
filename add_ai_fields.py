"""
Migration script to add AI features fields to database
Run this script to add AI-related columns to users, flashcards, and create ai_usage_logs table

Usage:
    python add_ai_fields.py
"""

import sqlite3
import os
import sys


def get_database_path():
    """Find the actual database location"""
    possible_paths = [
        os.path.join("instance", "flashcards.db"),
        os.path.join("app", "flashcards.db"),
        "flashcards.db",
    ]

    for path in possible_paths:
        if os.path.exists(path):
            return path

    print("❌ Database not found in any of these locations:")
    for path in possible_paths:
        print(f"   - {path}")
    return None


def migrate_database(db_path):
    """Add AI feature fields to the database"""

    print(f"📂 Using database: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        print("\n🔄 Starting AI fields migration...\n")

        # ============================================================
        # 1. ADD AI FIELDS TO USERS TABLE
        # ============================================================
        print("1️⃣  Adding AI fields to 'users' table...")

        # Check if columns already exist
        cursor.execute("PRAGMA table_info(users)")
        existing_columns = [column[1] for column in cursor.fetchall()]

        changes_made = False

        if "ai_enabled" not in existing_columns:
            cursor.execute("""
                ALTER TABLE users 
                ADD COLUMN ai_enabled BOOLEAN NOT NULL DEFAULT 0
            """)
            print("   ✓ Added 'ai_enabled' column")
            changes_made = True
        else:
            print("   ⏭  'ai_enabled' column already exists")

        if "ai_credits" not in existing_columns:
            cursor.execute("""
                ALTER TABLE users 
                ADD COLUMN ai_credits INTEGER DEFAULT 100
            """)
            print("   ✓ Added 'ai_credits' column")
            changes_made = True
        else:
            print("   ⏭  'ai_credits' column already exists")

        if "ai_provider" not in existing_columns:
            cursor.execute("""
                ALTER TABLE users 
                ADD COLUMN ai_provider VARCHAR(20) DEFAULT 'gemini'
            """)
            print("   ✓ Added 'ai_provider' column")
            changes_made = True
        else:
            print("   ⏭  'ai_provider' column already exists")

        # ============================================================
        # 2. ADD AI FIELDS TO FLASHCARDS TABLE
        # ============================================================
        print("\n2️⃣  Adding AI fields to 'flashcards' table...")

        cursor.execute("PRAGMA table_info(flashcards)")
        existing_columns = [column[1] for column in cursor.fetchall()]

        if "ai_generated" not in existing_columns:
            cursor.execute("""
                ALTER TABLE flashcards 
                ADD COLUMN ai_generated BOOLEAN NOT NULL DEFAULT 0
            """)
            print("   ✓ Added 'ai_generated' column")
            changes_made = True
        else:
            print("   ⏭  'ai_generated' column already exists")

        if "generation_prompt" not in existing_columns:
            cursor.execute("""
                ALTER TABLE flashcards 
                ADD COLUMN generation_prompt TEXT
            """)
            print("   ✓ Added 'generation_prompt' column")
            changes_made = True
        else:
            print("   ⏭  'generation_prompt' column already exists")

        if "ai_provider" not in existing_columns:
            cursor.execute("""
                ALTER TABLE flashcards 
                ADD COLUMN ai_provider VARCHAR(20)
            """)
            print("   ✓ Added 'ai_provider' column to flashcards")
            changes_made = True
        else:
            print("   ⏭  'ai_provider' column already exists in flashcards")

        # ============================================================
        # 3. CREATE AI_USAGE_LOGS TABLE
        # ============================================================
        print("\n3️⃣  Creating 'ai_usage_logs' table...")

        # Check if table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='ai_usage_logs'
        """)

        if not cursor.fetchone():
            cursor.execute("""
                CREATE TABLE ai_usage_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    operation_type VARCHAR(50) NOT NULL,
                    tokens_used INTEGER DEFAULT 0,
                    cost DECIMAL(10, 6) DEFAULT 0.0,
                    success BOOLEAN DEFAULT 1,
                    error_message TEXT,
                    request_data TEXT,
                    response_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            print("   ✓ Created 'ai_usage_logs' table")
            changes_made = True
        else:
            print("   ⏭  'ai_usage_logs' table already exists")

        # ============================================================
        # 4. CREATE INDEXES FOR PERFORMANCE
        # ============================================================
        print("\n4️⃣  Creating indexes for AI tables...")

        # Check existing indexes
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        existing_indexes = [row[0] for row in cursor.fetchall()]

        if "idx_ai_usage_user_id" not in existing_indexes:
            cursor.execute("""
                CREATE INDEX idx_ai_usage_user_id 
                ON ai_usage_logs(user_id)
            """)
            print("   ✓ Created index on ai_usage_logs.user_id")
            changes_made = True
        else:
            print("   ⏭  Index idx_ai_usage_user_id already exists")

        if "idx_ai_usage_created_at" not in existing_indexes:
            cursor.execute("""
                CREATE INDEX idx_ai_usage_created_at 
                ON ai_usage_logs(created_at)
            """)
            print("   ✓ Created index on ai_usage_logs.created_at")
            changes_made = True
        else:
            print("   ⏭  Index idx_ai_usage_created_at already exists")

        if "idx_flashcards_ai_generated" not in existing_indexes:
            cursor.execute("""
                CREATE INDEX idx_flashcards_ai_generated 
                ON flashcards(ai_generated)
            """)
            print("   ✓ Created index on flashcards.ai_generated")
            changes_made = True
        else:
            print("   ⏭  Index idx_flashcards_ai_generated already exists")

        # ============================================================
        # 5. COMMIT CHANGES
        # ============================================================
        if changes_made:
            conn.commit()
            print("\n✅ AI fields migration completed successfully!")
        else:
            print("\n✅ All AI fields already exist - no changes needed!")

        # ============================================================
        # 6. VERIFY CHANGES
        # ============================================================
        print("\n🔍 Verifying database structure...")

        # Check users table
        cursor.execute("PRAGMA table_info(users)")
        user_columns = [col[1] for col in cursor.fetchall()]
        ai_user_fields = ["ai_enabled", "ai_credits", "ai_provider"]
        all_good = True

        for field in ai_user_fields:
            if field in user_columns:
                print(f"   ✓ users.{field} exists")
            else:
                print(f"   ❌ users.{field} missing!")
                all_good = False

        # Check flashcards table
        cursor.execute("PRAGMA table_info(flashcards)")
        card_columns = [col[1] for col in cursor.fetchall()]
        ai_card_fields = ["ai_generated", "generation_prompt", "ai_provider"]

        for field in ai_card_fields:
            if field in card_columns:
                print(f"   ✓ flashcards.{field} exists")
            else:
                print(f"   ❌ flashcards.{field} missing!")
                all_good = False

        # Check ai_usage_logs table
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='ai_usage_logs'
        """)
        if cursor.fetchone():
            print("   ✓ ai_usage_logs table exists")
        else:
            print("   ❌ ai_usage_logs table missing!")
            all_good = False

        if all_good:
            print("\n" + "=" * 60)
            print("🎉 Migration complete! Your database is ready for AI features.")
            print("=" * 60)
            print("\n📝 Next steps:")
            print("   1. Add AI_ENABLED=true to your .env file")
            print("   2. Add GEMINI_API_KEY=your_key to your .env file")
            print("   3. Restart your Flask app")

        return all_good

    except sqlite3.Error as e:
        print(f"\n❌ Database error: {e}")
        conn.rollback()
        return False

    finally:
        conn.close()


if __name__ == "__main__":
    print("=" * 60)
    print("AI FEATURES DATABASE MIGRATION")
    print("=" * 60)
    print("\nThis script will add AI-related fields to your database:")
    print("  • Add ai_enabled, ai_credits, ai_provider to users")
    print("  • Add ai_generated, generation_prompt, ai_provider to flashcards")
    print("  • Create ai_usage_logs table")
    print("  • Create performance indexes")
    print("\n⚠️  Make sure to backup your database first!")
    print("=" * 60)

    # Find database
    db_path = get_database_path()
    if not db_path:
        print("\n❌ Cannot proceed without a database file.")
        print("Please ensure your Flask app has created the database first.")
        sys.exit(1)

    response = input("\nProceed with migration? (yes/no): ").strip().lower()

    if response in ["yes", "y"]:
        success = migrate_database(db_path)
        if success:
            print("\n✅ You can now use AI features in your application!")
        else:
            print("\n❌ Migration failed. Please check the error messages above.")
            sys.exit(1)
    else:
        print("\n⏸  Migration cancelled.")
        sys.exit(0)
