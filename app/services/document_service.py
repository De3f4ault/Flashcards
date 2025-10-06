"""
Document Service
Business logic for document upload, storage, and management
"""

import os
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import current_app
from app.models import Document
from app.extensions import db
from app.config import Config
from app.services.gemini_file_service import GeminiFileService


class DocumentService:
    """Service for managing document uploads and processing"""

    @staticmethod
    def allowed_file(filename):
        """Check if file extension is allowed"""
        if '.' not in filename:
            return False
        ext = filename.rsplit('.', 1)[1].lower()
        # Use current app config instead of importing Config directly
        allowed_extensions = current_app.config.get('ALLOWED_DOCUMENT_EXTENSIONS', {'pdf', 'txt', 'epub', 'docx'})
        return ext in allowed_extensions

    @staticmethod
    def get_file_extension(filename):
        """Extract file extension"""
        if '.' in filename:
            return filename.rsplit('.', 1)[1].lower()
        return None

    @staticmethod
    def generate_unique_filename(original_filename):
        """Generate unique filename while preserving extension"""
        ext = DocumentService.get_file_extension(original_filename)
        if not ext:
            raise ValueError("File has no extension")
        unique_id = str(uuid.uuid4())
        return f"{unique_id}.{ext}"

    @staticmethod
    def ensure_upload_directory(user_id):
        """Create user's upload directory if it doesn't exist"""
        user_dir = os.path.join(Config.UPLOAD_FOLDER, str(user_id))
        os.makedirs(user_dir, exist_ok=True)
        return user_dir

    @staticmethod
    def create_document(user_id, file, original_filename=None):
        """
        Handle file upload: save locally, upload to Gemini, create DB record

        Args:
            user_id: ID of user uploading the file
            file: FileStorage object from Flask request
            original_filename: Optional override for display name

        Returns:
            Document: Created document instance or None on error
        """
        file_path = None
        document = None

        try:
            # Validate file
            if not file:
                raise ValueError("No file provided")

            filename = original_filename or file.filename
            if not DocumentService.allowed_file(filename):
                allowed_extensions = current_app.config.get('ALLOWED_DOCUMENT_EXTENSIONS', {'pdf', 'txt', 'epub', 'docx'})
                allowed = ', '.join(sorted(allowed_extensions))
                raise ValueError(f"File type not allowed. Allowed types: {allowed}")

            # Get file size
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)

            if file_size > Config.MAX_CONTENT_LENGTH:
                max_mb = Config.MAX_CONTENT_LENGTH / (1024 * 1024)
                raise ValueError(f"File too large. Maximum size: {max_mb}MB")

            # Generate unique filename and save locally
            unique_filename = DocumentService.generate_unique_filename(filename)
            user_dir = DocumentService.ensure_upload_directory(user_id)
            file_path = os.path.join(user_dir, unique_filename)

            file.save(file_path)
            print(f"✓ File saved locally: {file_path}")

            # Create database record (initially pending)
            file_type = DocumentService.get_file_extension(filename)
            relative_path = os.path.join(str(user_id), unique_filename)

            document = Document(
                filename=unique_filename,
                original_filename=filename,
                file_path=relative_path,
                file_type=file_type,
                file_size=file_size,
                user_id=user_id,
                processing_status='uploading'
            )
            db.session.add(document)
            db.session.commit()
            print(f"✓ Database record created: Document ID {document.id}")

            # Upload to Gemini File API
            print(f"\n=== Starting Gemini Upload ===")
            gemini_service = GeminiFileService()
            file_uri, file_name, expires_at, error_msg = gemini_service.upload_file_to_gemini(
                file_path,
                filename
            )

            if file_uri:
                document.update_gemini_info(file_uri, file_name, expires_at)
                print(f"✓ Document created successfully: ID {document.id}")
                print(f"  Status: {document.processing_status}")
                return document
            else:
                # Gemini upload failed
                error_message = error_msg or "Failed to upload to Gemini File API"
                print(f"✗ Gemini upload failed: {error_message}")
                document.mark_error(error_message)
                db.session.commit()
                # Return document even on error so user can see what went wrong
                return document

        except ValueError as e:
            # Validation errors - these should be shown to user
            print(f"✗ Validation error: {e}")
            # Cleanup
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
                print(f"Cleaned up local file: {file_path}")
            if document and document.id:
                db.session.delete(document)
                db.session.commit()
                print(f"Cleaned up database record")
            raise  # Re-raise ValueError so it can be caught in the view

        except Exception as e:
            print(f"✗ Unexpected error creating document: {type(e).__name__}: {e}")
            # Cleanup local file if it was saved
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    print(f"Cleaned up local file: {file_path}")
                except:
                    pass
            # Mark document as error if it was created
            if document and document.id:
                try:
                    document.mark_error(f"System error: {str(e)}")
                    db.session.commit()
                except:
                    db.session.rollback()
            return None



    @staticmethod
    def get_user_documents(user_id, order_by='upload_date', ascending=False):
        """
        Get all documents for a user

        Args:
            user_id: User ID
            order_by: Field to sort by (upload_date, file_size, original_filename)
            ascending: Sort direction

        Returns:
            list: List of Document instances
        """
        query = Document.query.filter_by(user_id=user_id)

        # Apply sorting
        order_field = getattr(Document, order_by, Document.upload_date)
        if ascending:
            query = query.order_by(order_field.asc())
        else:
            query = query.order_by(order_field.desc())

        return query.all()

    @staticmethod
    def get_document(document_id, user_id):
        """
        Get document with permission check

        Args:
            document_id: Document ID
            user_id: User ID for permission check

        Returns:
            Document: Document instance or None
        """
        document = Document.query.filter_by(id=document_id, user_id=user_id).first()
        if document:
            document.mark_accessed()
        return document

    @staticmethod
    def delete_document(document_id, user_id):
        """
        Delete document: remove from filesystem, Gemini, and database

        Args:
            document_id: Document ID
            user_id: User ID for permission check

        Returns:
            bool: True if deleted successfully
        """
        try:
            document = Document.query.filter_by(id=document_id, user_id=user_id).first()
            if not document:
                return False

            # Delete from Gemini if uploaded
            if document.gemini_file_name:
                gemini_service = GeminiFileService()
                gemini_service.delete_gemini_file(document.gemini_file_name)

            # Delete local file
            file_path = document.get_storage_path()
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"Local file deleted: {file_path}")

            # Delete from database
            db.session.delete(document)
            db.session.commit()

            print(f"Document deleted successfully: {document_id}")
            return True

        except Exception as e:
            print(f"Error deleting document: {e}")
            db.session.rollback()
            return False

    @staticmethod
    def ensure_document_cached(document_id):
        """
        Ensure document is cached in Gemini, refresh if expired

        Args:
            document_id: Document ID

        Returns:
            bool: True if document is cached and ready
        """
        try:
            document = Document.query.get(document_id)
            if not document:
                return False

            # Check if cache is expired
            if document.is_gemini_cache_expired():
                print(f"Cache expired for document {document_id}, refreshing...")
                gemini_service = GeminiFileService()
                return gemini_service.refresh_expired_file(document)

            return True

        except Exception as e:
            print(f"Error ensuring document cached: {e}")
            return False

    @staticmethod
    def get_document_stats(document_id):
        """
        Get usage statistics for a document

        Args:
            document_id: Document ID

        Returns:
            dict: Statistics including access count, questions generated, etc.
        """
        document = Document.query.get(document_id)
        if not document:
            return None

        # TODO: Add more stats when chat and Q&A features are implemented
        stats = {
            'file_size': document.get_file_size_formatted(),
            'upload_date': document.upload_date,
            'last_accessed': document.last_accessed,
            'gemini_cache_status': 'active' if not document.is_gemini_cache_expired() else 'expired',
            'processing_status': document.processing_status,
            # Placeholder for future features
            'questions_generated': 0,
            'chat_sessions': 0,
            'total_accesses': 0
        }

        return stats

    @staticmethod
    def get_user_storage_usage(user_id):
        """
        Calculate total storage used by user

        Args:
            user_id: User ID

        Returns:
            dict: Storage statistics
        """
        documents = Document.query.filter_by(user_id=user_id).all()

        total_bytes = sum(doc.file_size for doc in documents)
        total_count = len(documents)

        # Format size
        size = total_bytes
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                formatted_size = f"{size:.1f} {unit}"
                break
            size /= 1024.0
        else:
            formatted_size = f"{size:.1f} TB"

        return {
            'total_documents': total_count,
            'total_bytes': total_bytes,
            'total_formatted': formatted_size
        }
