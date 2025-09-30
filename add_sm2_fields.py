"""
Standalone migration script to add SM-2 spaced repetition fields
Run this directly: python add_sm2_fields.py
"""

import sqlite3
from datetime import datetime
import os

# Database path
DB_PATH = 'instance/flashcards.db'

def run_migration():
    """Add SM-2 fields to flashcards table"""
    
    if not os.path.exists(DB_PATH):
        print(f"❌ Error: Database not found at {DB_PATH}")
        return False
    
    print("\n" + "="*60)
    print("SM-2 SPACED REPETITION MIGRATION")
    print("="*60)
    
    try:
        # Connect to database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        print("\n🔄 Adding SM-2 fields to flashcards table...")
        
        # Add columns (SQLite allows NULL columns easily)
        columns_to_add = [
            ("ease_factor", "REAL DEFAULT 2.5"),
            ("interval", "INTEGER DEFAULT 0"),
            ("repetitions", "INTEGER DEFAULT 0"),
            ("next_review_date", "DATETIME"),
            ("last_reviewed", "DATETIME"),
            ("learning_state", "VARCHAR(20) DEFAULT 'new'")
        ]
        
        for column_name, column_type in columns_to_add:
            try:
                cursor.execute(f"ALTER TABLE flashcards ADD COLUMN {column_name} {column_type}")
                print(f"   ✓ Added column: {column_name}")
            except sqlite3.OperationalError as e:
                if "duplicate column" in str(e).lower():
                    print(f"   ⚠️  Column {column_name} already exists, skipping...")
                else:
                    raise
        
        conn.commit()
        print("\n✅ All columns added successfully!")
        
        # Initialize existing cards
        print("\n🔄 Initializing existing flashcards with SM-2 defaults...")
        
        now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute("""
            UPDATE flashcards 
            SET 
                ease_factor = COALESCE(ease_factor, 2.5),
                interval = COALESCE(interval, 0),
                repetitions = COALESCE(repetitions, 0),
                next_review_date = COALESCE(next_review_date, ?),
                learning_state = COALESCE(
                    learning_state,
                    CASE 
                        WHEN times_studied = 0 THEN 'new'
                        WHEN (times_correct * 100.0 / NULLIF(times_studied, 0)) >= 80 THEN 'review'
                        ELSE 'learning'
                    END
                )
        """, (now,))
        
        affected_rows = cursor.rowcount
        conn.commit()
        
        print(f"✅ Initialized {affected_rows} flashcards with defaults")
        
        # Verify migration
        print("\n🔍 Verifying migration...")
        cursor.execute("PRAGMA table_info(flashcards)")
        columns = cursor.fetchall()
        
        sm2_columns = ['ease_factor', 'interval', 'repetitions', 'next_review_date', 'last_reviewed', 'learning_state']
        found_columns = [col[1] for col in columns]
        
        all_present = all(col in found_columns for col in sm2_columns)
        
        if all_present:
            print("✅ All SM-2 columns verified!")
        else:
            missing = [col for col in sm2_columns if col not in found_columns]
            print(f"⚠️  Missing columns: {missing}")
        
        # Show sample data
        cursor.execute("SELECT COUNT(*) FROM flashcards")
        total_cards = cursor.fetchone()[0]
        
        if total_cards > 0:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN learning_state = 'new' THEN 1 ELSE 0 END) as new,
                    SUM(CASE WHEN learning_state = 'learning' THEN 1 ELSE 0 END) as learning,
                    SUM(CASE WHEN learning_state = 'review' THEN 1 ELSE 0 END) as review,
                    SUM(CASE WHEN learning_state = 'mastered' THEN 1 ELSE 0 END) as mastered
                FROM flashcards
            """)
            stats = cursor.fetchone()
            
            print("\n📊 Card Distribution:")
            print(f"   Total: {stats[0]}")
            print(f"   New: {stats[1]}")
            print(f"   Learning: {stats[2]}")
            print(f"   Review: {stats[3]}")
            print(f"   Mastered: {stats[4]}")
        else:
            print("\n📊 No cards in database yet")
        
        conn.close()
        
        print("\n" + "="*60)
        print("🎉 MIGRATION COMPLETE!")
        print("="*60)
        print("\nSM-2 Spaced Repetition is now active!")
        print("Start your app with: python run.py")
        print("\n")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during migration: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_migration()
    exit(0 if success else 1)
