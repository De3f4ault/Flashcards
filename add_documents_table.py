"""
Migration script to add documents table for Phase 1: Document Upload & Gemini File API Integration
Run this script from the project root: python add_documents_table.py
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


def add_documents_table():
    """Add documents table to the database"""

    if table_exists('documents'):
        print("✓ 'documents' table already exists. Skipping creation.")
        return False

    print("Creating 'documents' table...")

    # Create documents table
    db.engine.execute(text("""
        CREATE TABLE documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            filename VARCHAR(255) NOT NULL,
            original_filename VARCHAR(255) NOT NULL,
            file_path VARCHAR(500) NOT NULL,
            file_type VARCHAR(20) NOT NULL,
            file_size INTEGER NOT NULL,
            gemini_file_uri VARCHAR(500),
            gemini_file_name VARCHAR(255),
            gemini_expires_at DATETIME,
            upload_date DATETIME NOT NULL,
            last_accessed DATETIME,
            processing_status VARCHAR(20) NOT NULL DEFAULT 'pending',
            error_message TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """))

    # Create indexes for better query performance
    print("Creating indexes...")
    db.engine.execute(text("CREATE INDEX idx_documents_user_id ON documents(user_id)"))
    db.engine.execute(text("CREATE INDEX idx_documents_processing_status ON documents(processing_status)"))
    db.engine.execute(text("CREATE INDEX idx_documents_upload_date ON documents(upload_date DESC)"))

    print("✓ 'documents' table created successfully!")
    return True


def verify_migration():
    """Verify the migration was successful"""
    inspector = inspect(db.engine)

    if not table_exists('documents'):
        print("✗ Migration failed: 'documents' table not found")
        return False

    columns = [col['name'] for col in inspector.get_columns('documents')]
    expected_columns = [
        'id', 'user_id', 'filename', 'original_filename', 'file_path',
        'file_type', 'file_size', 'gemini_file_uri', 'gemini_file_name',
        'gemini_expires_at', 'upload_date', 'last_accessed',
        'processing_status', 'error_message'
    ]

    missing_columns = [col for col in expected_columns if col not in columns]

    if missing_columns:
        print(f"✗ Migration verification failed: Missing columns: {missing_columns}")
        return False

    print("✓ Migration verification passed!")
    print(f"  - Table: documents")
    print(f"  - Columns: {len(columns)}")
    print(f"  - Indexes: 3 (user_id, processing_status, upload_date)")

    return True


def create_uploads_directory():
    """Create the uploads/documents directory if it doesn't exist"""
    uploads_dir = os.path.join(os.path.dirname(__file__), 'uploads', 'documents')

    if os.path.exists(uploads_dir):
        print(f"✓ Uploads directory already exists: {uploads_dir}")
        return

    try:
        os.makedirs(uploads_dir, exist_ok=True)
        print(f"✓ Created uploads directory: {uploads_dir}")

        # Create a .gitkeep file to track the directory in git
        gitkeep_path = os.path.join(uploads_dir, '.gitkeep')
        with open(gitkeep_path, 'w') as f:
            f.write('')
        print(f"✓ Created .gitkeep file")

    except Exception as e:
        print(f"✗ Failed to create uploads directory: {e}")


def main():
    """Main migration function"""
    print("=" * 60)
    print("Document Upload Migration - Phase 1")
    print("=" * 60)
    print()

    # Create Flask app context
    app = create_app()

    with app.app_context():
        try:
            # Run migration
            print("Step 1: Adding 'documents' table...")
            table_added = add_documents_table()
            print()

            # Verify migration
            print("Step 2: Verifying migration...")
            verification_passed = verify_migration()
            print()

            # Create uploads directory
            print("Step 3: Setting up file storage...")
            create_uploads_directory()
            print()

            # Summary
            print("=" * 60)
            if table_added and verification_passed:
                print("✓ Migration completed successfully!")
                print()
                print("Next steps:")
                print("  1. Ensure GEMINI_API_KEY is set in your .env file")
                print("  2. Restart your Flask application")
                print("  3. Navigate to /documents/upload to test file uploads")
            else:
                print("✓ Migration skipped (table already exists)")
            print("=" * 60)

        except Exception as e:
            print(f"\n✗ Migration failed with error:")
            print(f"  {str(e)}")
            print("\nPlease check your database configuration and try again.")
            sys.exit(1)


if __name__ == '__main__':
    main()
