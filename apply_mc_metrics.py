#!/usr/bin/env python3
"""
Apply all pending migrations for MC Phase 1
Creates necessary tables and updates schema
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app
from app.extensions import db
from sqlalchemy import inspect, text


def check_table_exists(table_name):
    """Check if table exists in database"""
    inspector = inspect(db.engine)
    return table_name in inspector.get_table_names()


def get_table_columns(table_name):
    """Get list of columns for a table"""
    inspector = inspect(db.engine)
    if check_table_exists(table_name):
        return [col['name'] for col in inspector.get_columns(table_name)]
    return []


def create_mc_metrics_table():
    """Create mc_metrics table for Phase 1 validation tracking"""
    print("\n📊 Creating mc_metrics table...")

    if check_table_exists('mc_metrics'):
        print("   ✓ Table already exists")
        columns = get_table_columns('mc_metrics')
        print(f"   Columns: {', '.join(columns)}")
        return True

    try:
        # Import model to ensure it's registered
        from app.models.mc_metrics import MCMetrics

        # Create table
        db.create_all()

        # Verify
        if check_table_exists('mc_metrics'):
            columns = get_table_columns('mc_metrics')
            print(f"   ✓ Table created successfully")
            print(f"   Columns: {', '.join(columns)}")
            return True
        else:
            print("   ✗ Table creation failed")
            return False

    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


def verify_mc_tables():
    """Verify all MC Phase 1 tables exist"""
    print("\n🔍 Verifying MC Phase 1 tables...")

    required_tables = {
        'mc_cards': 'Multiple choice questions',
        'mc_sessions': 'Study session tracking',
        'mc_attempts': 'Individual answer attempts',
        'mc_metrics': 'Phase 1 validation metrics'
    }

    all_exist = True
    for table_name, description in required_tables.items():
        exists = check_table_exists(table_name)
        status = "✓" if exists else "✗"
        print(f"   {status} {table_name} - {description}")

        if exists:
            columns = get_table_columns(table_name)
            print(f"      {len(columns)} columns: {', '.join(columns[:5])}{'...' if len(columns) > 5 else ''}")
        else:
            all_exist = False

    return all_exist


def add_mc_cards_relationship():
    """Ensure deck model has mc_cards relationship"""
    print("\n🔗 Checking deck relationships...")

    try:
        from app.models.deck import Deck

        # Check if relationship exists
        if hasattr(Deck, 'mc_cards'):
            print("   ✓ Deck.mc_cards relationship exists")
            return True
        else:
            print("   ⚠️  Deck.mc_cards relationship missing")
            print("   → Update app/models/deck.py to add:")
            print("      mc_cards = db.relationship('MCCard', backref='deck', lazy=True, cascade='all, delete-orphan')")
            return False

    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


def run_all_migrations():
    """Run all migrations and verify setup"""
    print("=" * 60)
    print("MC PHASE 1 MIGRATION SCRIPT")
    print("=" * 60)

    app = create_app()

    with app.app_context():
        results = []

        # 1. Verify base tables exist
        print("\n1️⃣  Checking base tables...")
        base_tables_ok = verify_mc_tables()

        if not base_tables_ok:
            print("\n   Creating missing base tables...")
            db.create_all()
            base_tables_ok = verify_mc_tables()

        results.append(("Base MC tables", base_tables_ok))

        # 2. Create metrics table
        print("\n2️⃣  Setting up metrics tracking...")
        metrics_ok = create_mc_metrics_table()
        results.append(("Metrics table", metrics_ok))

        # 3. Verify relationships
        print("\n3️⃣  Verifying model relationships...")
        relationships_ok = add_mc_cards_relationship()
        results.append(("Model relationships", relationships_ok))

        # 4. Test database connectivity
        print("\n4️⃣  Testing database connectivity...")
        try:
            result = db.session.execute(text("SELECT 1")).scalar()
            db_ok = result == 1
            print("   ✓ Database connection working")
            results.append(("Database connection", True))
        except Exception as e:
            print(f"   ✗ Database error: {e}")
            results.append(("Database connection", False))
            db_ok = False

        # Summary
        print("\n" + "=" * 60)
        print("MIGRATION SUMMARY")
        print("=" * 60)

        for name, status in results:
            status_icon = "✓" if status else "✗"
            print(f"{status_icon} {name}")

        all_passed = all(status for _, status in results)

        if all_passed:
            print("\n✅ All migrations completed successfully!")
            print("\n📋 Next steps:")
            print("   1. Update app/routes.py to register mc_metrics_bp")
            print("   2. Add tracking calls to mc_generation.py and mc_study.py")
            print("   3. Create templates/mc_metrics/ directory")
            print("   4. Copy dashboard templates")
            print("   5. Test at: /mc/metrics/dashboard")
            return 0
        else:
            print("\n⚠️  Some migrations had issues - see details above")
            return 1


if __name__ == '__main__':
    sys.exit(run_all_migrations())
