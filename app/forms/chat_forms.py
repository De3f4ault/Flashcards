"""
Chat Forms - Forms for chat interface interactions
"""

from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, HiddenField
from wtforms.validators import DataRequired, Length, Optional, ValidationError


class ChatMessageForm(FlaskForm):
    """Form for sending chat messages"""

    message = TextAreaField(
        'Message',
        validators=[
            DataRequired(message='Message cannot be empty'),
            Length(min=1, max=10000, message='Message must be between 1 and 10000 characters')
        ],
        render_kw={
            'placeholder': 'Type your message here...',
            'rows': 3,
            'class': 'form-control'
        }
    )

    session_id = HiddenField('Session ID')


class NewChatSessionForm(FlaskForm):
    """Form for creating a new chat session"""

    title = StringField(
        'Session Title',
        validators=[
            Optional(),
            Length(max=255, message='Title cannot exceed 255 characters')
        ],
        render_kw={
            'placeholder': 'New Chat (optional)',
            'class': 'form-control'
        }
    )

    document_id = SelectField(
        'Attach Document (Optional)',
        coerce=int,
        validators=[Optional()],
        render_kw={'class': 'form-select'}
    )

    def __init__(self, *args, **kwargs):
        super(NewChatSessionForm, self).__init__(*args, **kwargs)
        # Choices will be set in the view with user's documents
        self.document_id.choices = [(0, 'No document')]


class RenameSessionForm(FlaskForm):
    """Form for renaming a chat session"""

    title = StringField(
        'New Title',
        validators=[
            DataRequired(message='Title is required'),
            Length(min=1, max=255, message='Title must be between 1 and 255 characters')
        ],
        render_kw={
            'placeholder': 'Enter new title',
            'class': 'form-control'
        }
    )

    session_id = HiddenField('Session ID')


class AttachDocumentForm(FlaskForm):
    """Form for attaching a document to a chat session"""

    document_id = SelectField(
        'Select Document',
        coerce=int,
        validators=[DataRequired(message='Please select a document')],
        render_kw={'class': 'form-select'}
    )

    session_id = HiddenField('Session ID')

    def __init__(self, *args, **kwargs):
        super(AttachDocumentForm, self).__init__(*args, **kwargs)
        # Choices will be set in the view with user's documents
        self.document_id.choices = []

    def validate_document_id(self, field):
        """Ensure a valid document is selected"""
        if field.data == 0:
            raise ValidationError('Please select a valid document')


class SearchSessionsForm(FlaskForm):
    """Form for searching and filtering chat sessions"""

    search = StringField(
        'Search',
        validators=[
            Optional(),
            Length(max=100, message='Search query too long')
        ],
        render_kw={
            'placeholder': 'Search sessions...',
            'class': 'form-control'
        }
    )

    sort_by = SelectField(
        'Sort By',
        choices=[
            ('recent', 'Most Recent'),
            ('oldest', 'Oldest First'),
            ('title', 'Title (A-Z)'),
            ('messages', 'Most Messages')
        ],
        default='recent',
        validators=[Optional()],
        render_kw={'class': 'form-select'}
    )

    filter_document = SelectField(
        'Filter by Document',
        coerce=int,
        choices=[(0, 'All Sessions')],
        default=0,
        validators=[Optional()],
        render_kw={'class': 'form-select'}
    )


class ExportChatForm(FlaskForm):
    """Form for exporting chat conversation (future feature)"""

    format = SelectField(
        'Export Format',
        choices=[
            ('txt', 'Plain Text'),
            ('md', 'Markdown'),
            ('pdf', 'PDF'),
            ('json', 'JSON')
        ],
        default='txt',
        validators=[DataRequired()],
        render_kw={'class': 'form-select'}
    )

    include_timestamps = SelectField(
        'Include Timestamps',
        choices=[
            ('yes', 'Yes'),
            ('no', 'No')
        ],
        default='yes',
        validators=[DataRequired()],
        render_kw={'class': 'form-select'}
    )

    session_id = HiddenField('Session ID')
