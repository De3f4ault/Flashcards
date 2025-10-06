#!/usr/bin/env python3
"""
Migration Script: Add document fields to mc_cards table
Run this script from the project root directory
"""

import sys
import os

# Add the project directory to the path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app
from app.extensions import db
from sqlalchemy import text

def run_migration():
    """Add document_id and document_section columns to mc_cards table"""

    app = create_app()

    with app.app_context():
        print("Starting migration: Add document fields to mc_cards")
        print("-" * 60)

        try:
            # Check if columns already exist
            inspector = db.inspect(db.engine)
            existing_columns = [col['name'] for col in inspector.get_columns('mc_cards')]

            columns_to_add = []

            if 'document_id' not in existing_columns:
                columns_to_add.append('document_id')
            else:
                print("✓ Column 'document_id' already exists")

            if 'document_section' not in existing_columns:
                columns_to_add.append('document_section')
            else:
                print("✓ Column 'document_section' already exists")

            if not columns_to_add:
                print("\n✓ All columns already exist. No migration needed.")
                return True

            # Add missing columns
            print(f"\nAdding columns: {', '.join(columns_to_add)}")

            if 'document_id' in columns_to_add:
                print("  Adding document_id column...")
                db.session.execute(text("""
                    ALTER TABLE mc_cards
                    ADD COLUMN document_id INTEGER
                    REFERENCES documents(id) ON DELETE CASCADE
                """))
                print("  ✓ document_id column added")

            if 'document_section' in columns_to_add:
                print("  Adding document_section column...")
                db.session.execute(text("""
                    ALTER TABLE mc_cards
                    ADD COLUMN document_section VARCHAR(200)
                """))
                print("  ✓ document_section column added")

            # Commit changes
            db.session.commit()
            print("\n" + "=" * 60)
            print("✓ Migration completed successfully!")
            print("=" * 60)

            # Verify the migration
            print("\nVerifying migration...")
            inspector = db.inspect(db.engine)
            columns_after = [col['name'] for col in inspector.get_columns('mc_cards')]

            if 'document_id' in columns_after and 'document_section' in columns_after:
                print("✓ Verification passed: All columns present")
                return True
            else:
                print("✗ Verification failed: Columns not found")
                return False

        except Exception as e:
            db.session.rollback()
            print(f"\n✗ Migration failed: {str(e)}")
            print("\nError details:")
            import traceback
            traceback.print_exc()
            return False


def rollback_migration():
    """Remove document fields from mc_cards table (rollback)"""

    app = create_app()

    with app.app_context():
        print("Rolling back migration: Remove document fields from mc_cards")
        print("-" * 60)

        try:
            # Check if columns exist
            inspector = db.inspect(db.engine)
            existing_columns = [col['name'] for col in inspector.get_columns('mc_cards')]

            columns_to_remove = []

            if 'document_id' in existing_columns:
                columns_to_remove.append('document_id')

            if 'document_section' in existing_columns:
                columns_to_remove.append('document_section')

            if not columns_to_remove:
                print("✓ No columns to remove. Already rolled back.")
                return True

            print(f"\nRemoving columns: {', '.join(columns_to_remove)}")

            # SQLite doesn't support DROP COLUMN directly in older versions
            # We'll need to check the database type
            db_type = db.engine.dialect.name

            if db_type == 'sqlite':
                print("\nNote: SQLite detected. This may require recreating the table.")
                print("Consider using Flask-Migrate for proper SQLite migrations.")
                print("Attempting column drop (requires SQLite 3.35.0+)...")

            if 'document_id' in columns_to_remove:
                print("  Removing document_id column...")
                db.session.execute(text("ALTER TABLE mc_cards DROP COLUMN document_id"))
                print("  ✓ document_id column removed")

            if 'document_section' in columns_to_remove:
                print("  Removing document_section column...")
                db.session.execute(text("ALTER TABLE mc_cards DROP COLUMN document_section"))
                print("  ✓ document_section column removed")

            db.session.commit()
            print("\n✓ Rollback completed successfully!")
            return True

        except Exception as e:
            db.session.rollback()
            print(f"\n✗ Rollback failed: {str(e)}")
            print("\nIf using SQLite < 3.35.0, you may need to:")
            print("1. Export your data")
            print("2. Drop and recreate the mc_cards table")
            print("3. Re-import your data")
            return False


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("MC Cards Document Fields Migration")
    print("=" * 60)
    print("\nThis script will add document_id and document_section columns")
    print("to the mc_cards table for Phase 3 implementation.")
    print("\nOptions:")
    print("  1. Run migration (add columns)")
    print("  2. Rollback migration (remove columns)")
    print("  3. Exit")
    print("-" * 60)

    choice = input("\nEnter your choice (1-3): ").strip()

    if choice == '1':
        print("\n" + "=" * 60)
        success = run_migration()
        print("=" * 60)
        sys.exit(0 if success else 1)

    elif choice == '2':
        confirm = input("\nAre you sure you want to rollback? (yes/no): ").strip().lower()
        if confirm == 'yes':
            print("\n" + "=" * 60)
            success = rollback_migration()
            print("=" * 60)
            sys.exit(0 if success else 1)
        else:
            print("Rollback cancelled.")
            sys.exit(0)

    elif choice == '3':
        print("Exiting...")
        sys.exit(0)

    else:
        print("Invalid choice. Exiting...")
        sys.exit(1)
