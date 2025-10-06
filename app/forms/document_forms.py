"""
Document Forms
Forms for document upload and management
"""

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from wtforms import StringField, SelectField, ValidationError
from wtforms.validators import Optional, Length
from flask import current_app


def allowed_document_file(form, field):
    """Custom validator for document file uploads"""
    if not field.data:
        return

    filename = field.data.filename
    if not filename:
        raise ValidationError('No filename provided')

    print(f"DEBUG: Processing filename: '{filename}'")  # DEBUG

    # Check if file has extension
    if '.' not in filename:
        print(f"DEBUG: No extension found in filename")  # DEBUG
        raise ValidationError('File must have an extension')

    # Get extension (case-insensitive)
    ext = filename.rsplit('.', 1)[1].lower()
    print(f"DEBUG: Detected extension: '{ext}'")  # DEBUG

    # Check against allowed extensions from current app config
    allowed_extensions = current_app.config.get('ALLOWED_DOCUMENT_EXTENSIONS', {'pdf', 'txt', 'epub', 'docx'})
    print(f"DEBUG: Allowed extensions: {allowed_extensions}")  # DEBUG
    print(f"DEBUG: Extension in allowed? {ext in allowed_extensions}")  # DEBUG

    if ext not in allowed_extensions:
        allowed = ', '.join(sorted(allowed_extensions))
        raise ValidationError(f'File type ".{ext}" not allowed. Allowed types: {allowed}')


class DocumentUploadForm(FlaskForm):
    """Form for uploading documents"""

    document = FileField(
        'Document File',
        validators=[
            FileRequired(message='Please select a file to upload'),
            allowed_document_file
        ]
    )

    title = StringField(
        'Custom Title (Optional)',
        validators=[
            Optional(),
            Length(max=255, message='Title must be less than 255 characters')
        ],
        description='Leave blank to use the filename'
    )


class DocumentSearchForm(FlaskForm):
    """Form for searching/filtering documents"""

    sort_by = SelectField(
        'Sort By',
        choices=[
            ('upload_date', 'Upload Date'),
            ('original_filename', 'Name'),
            ('file_size', 'File Size')
        ],
        default='upload_date'
    )

    order = SelectField(
        'Order',
        choices=[
            ('desc', 'Newest First'),
            ('asc', 'Oldest First')
        ],
        default='desc'
    )

    file_type = SelectField(
        'File Type',
        choices=[
            ('all', 'All Types'),
            ('pdf', 'PDF'),
            ('txt', 'Text'),
            ('epub', 'EPUB'),
            ('docx', 'Word Document')
        ],
        default='all'
    )
