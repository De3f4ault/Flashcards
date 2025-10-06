"""
Migration: Create MC (Multiple Choice) System Tables - Phase 1
Creates three tables: mc_cards, mc_sessions, mc_attempts

Run this migration with:
    python create_mc_phase1.py
"""

from app import create_app
from app.extensions import db
from app.models import MCCard, MCSession, MCAttempt
from sqlalchemy import inspect


def check_table_exists(table_name):
    """Check if a table already exists"""
    inspector = inspect(db.engine)
    return table_name in inspector.get_table_names()


def create_mc_tables():
    """Create the three MC system tables"""
    app = create_app()

    with app.app_context():
        print("=" * 60)
        print("MC System Phase 1 Migration")
        print("=" * 60)

        # Check existing tables
        tables_to_create = []

        if not check_table_exists("mc_cards"):
            tables_to_create.append("mc_cards")
        else:
            print("⚠️  Table 'mc_cards' already exists - skipping")

        if not check_table_exists("mc_sessions"):
            tables_to_create.append("mc_sessions")
        else:
            print("⚠️  Table 'mc_sessions' already exists - skipping")

        if not check_table_exists("mc_attempts"):
            tables_to_create.append("mc_attempts")
        else:
            print("⚠️  Table 'mc_attempts' already exists - skipping")

        if not tables_to_create:
            print("\n✓ All MC tables already exist. No migration needed.")
            return

        print(f"\nCreating tables: {', '.join(tables_to_create)}")
        print("-" * 60)

        try:
            # Create all tables defined in models
            db.create_all()

            print("\n✓ Successfully created MC system tables!")
            print("-" * 60)

            # Verify creation
            print("\nVerifying table creation:")
            for table_name in ["mc_cards", "mc_sessions", "mc_attempts"]:
                if check_table_exists(table_name):
                    print(f"  ✓ {table_name}")
                else:
                    print(f"  ✗ {table_name} - FAILED")

            print("\n" + "=" * 60)
            print("Migration Complete!")
            print("=" * 60)
            print("\nNext Steps:")
            print("1. Verify tables in your database")
            print("2. Create MC generation service")
            print("3. Build MC study routes")

        except Exception as e:
            print(f"\n✗ Migration failed: {str(e)}")
            raise


def show_table_info():
    """Display information about the created tables"""
    app = create_app()

    with app.app_context():
        inspector = inspect(db.engine)

        print("\n" + "=" * 60)
        print("MC System Table Structure")
        print("=" * 60)

        for table_name in ["mc_cards", "mc_sessions", "mc_attempts"]:
            if check_table_exists(table_name):
                print(f"\n{table_name.upper()}:")
                columns = inspector.get_columns(table_name)
                for col in columns:
                    nullable = "NULL" if col["nullable"] else "NOT NULL"
                    default = f"DEFAULT {col['default']}" if col["default"] else ""
                    print(f"  - {col['name']}: {col['type']} {nullable} {default}")
            else:
                print(f"\n{table_name.upper()}: Not found")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--info":
        show_table_info()
    else:
        create_mc_tables()
