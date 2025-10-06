from datetime import datetime, timedelta
from app.models.base import BaseModel
from app.extensions import db


class Document(BaseModel):
    """Model for storing uploaded document metadata"""
    __tablename__ = 'documents'

    # File Information
    filename = db.Column(db.String(255), nullable=False)  # Sanitized filename
    original_filename = db.Column(db.String(255), nullable=False)  # User's original filename
    file_path = db.Column(db.String(500), nullable=False)  # Local storage path
    file_type = db.Column(db.String(10), nullable=False)  # pdf, txt, epub, docx
    file_size = db.Column(db.Integer, nullable=False)  # Size in bytes

    # Gemini File API Fields
    gemini_file_uri = db.Column(db.String(500), nullable=True)  # URI from Gemini File API
    gemini_file_name = db.Column(db.String(255), nullable=True)  # Gemini's file identifier
    gemini_expires_at = db.Column(db.DateTime, nullable=True)  # 48hr expiry from upload

    # Processing Status
    processing_status = db.Column(
        db.String(20),
        default='pending',
        nullable=False
    )  # pending, uploading, ready, error
    error_message = db.Column(db.Text, nullable=True)  # Error details if failed

    # Metadata
    upload_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_accessed = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('documents', lazy='dynamic'))

    def __repr__(self):
        return f'<Document {self.original_filename}>'

    def is_gemini_cache_expired(self):
        """Check if Gemini file cache has expired"""
        if not self.gemini_expires_at:
            return True
        return datetime.utcnow() >= self.gemini_expires_at

    def get_storage_path(self):
        """Get full path to stored file"""
        from app.config import Config
        import os
        return os.path.join(Config.UPLOAD_FOLDER, self.file_path)

    def mark_accessed(self):
        """Update last accessed timestamp"""
        self.last_accessed = datetime.utcnow()
        db.session.commit()

    def update_gemini_info(self, file_uri, file_name, expires_at):
        """Update Gemini File API information"""
        self.gemini_file_uri = file_uri
        self.gemini_file_name = file_name
        self.gemini_expires_at = expires_at
        self.processing_status = 'ready'
        self.error_message = None
        db.session.commit()

    def mark_error(self, error_message):
        """Mark document processing as failed"""
        self.processing_status = 'error'
        self.error_message = error_message
        db.session.commit()

    def get_file_size_formatted(self):
        """Return human-readable file size"""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    def to_dict(self):
        """Convert to dictionary for JSON responses"""
        return {
            'id': self.id,
            'filename': self.original_filename,
            'file_type': self.file_type,
            'file_size': self.file_size,
            'file_size_formatted': self.get_file_size_formatted(),
            'processing_status': self.processing_status,
            'upload_date': self.upload_date.isoformat() if self.upload_date else None,
            'last_accessed': self.last_accessed.isoformat() if self.last_accessed else None,
            'gemini_cache_expired': self.is_gemini_cache_expired(),
            'gemini_expires_at': self.gemini_expires_at.isoformat() if self.gemini_expires_at else None,
            'error_message': self.error_message
        }
