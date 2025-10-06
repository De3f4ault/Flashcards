"""
Chat Session Model - Stores conversation containers
"""

from datetime import datetime
from app.models.base import BaseModel
from app.extensions import db


class ChatSession(BaseModel):
    """
    Represents a chat conversation session.
    Users can have multiple sessions, each with its own conversation history.
    Sessions can optionally be linked to a document for context-aware conversations.
    """

    __tablename__ = 'chat_sessions'

    # Basic Information
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False, default='New Chat')

    # Document Context (optional)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=True)

    # Session Metadata
    last_message_at = db.Column(db.DateTime, nullable=True)
    message_count = db.Column(db.Integer, default=0, nullable=False)
    total_tokens_used = db.Column(db.Integer, default=0, nullable=False)

    # Relationships
    user = db.relationship('User', backref=db.backref('chat_sessions', lazy='dynamic'))
    document = db.relationship('Document', backref=db.backref('chat_sessions', lazy='dynamic'))
    messages = db.relationship('ChatMessage', backref='session', lazy='dynamic',
                               cascade='all, delete-orphan', order_by='ChatMessage.timestamp')

    def __repr__(self):
        return f'<ChatSession {self.id}: {self.title}>'

    def get_recent_messages(self, limit=20):
        """
        Get the most recent messages from this session for context.
        Returns messages in chronological order (oldest first).

        Args:
            limit (int): Maximum number of messages to retrieve

        Returns:
            list: List of ChatMessage objects
        """
        return self.messages.order_by(ChatMessage.timestamp.asc()).limit(limit).all()

    def calculate_context_tokens(self, message_limit=20):
        """
        Calculate approximate token count for recent conversation history.
        Uses rough estimate of 1 token per 4 characters.

        Args:
            message_limit (int): Number of recent messages to include

        Returns:
            int: Estimated token count
        """
        messages = self.get_recent_messages(limit=message_limit)
        total_chars = sum(len(msg.content) for msg in messages)
        return total_chars // 4  # Rough token estimate

    def update_last_message_time(self):
        """Update the last_message_at timestamp to current time"""
        self.last_message_at = datetime.utcnow()
        db.session.commit()

    def increment_message_count(self):
        """Increment the message counter"""
        self.message_count += 1
        db.session.commit()

    def add_tokens_used(self, tokens):
        """
        Add to the total token count for this session.

        Args:
            tokens (int): Number of tokens to add
        """
        self.total_tokens_used += tokens
        db.session.commit()

    def generate_title_from_first_message(self):
        """
        Generate a title from the first user message if title is still 'New Chat'.
        Returns the first 50 characters of the first message.
        """
        if self.title == 'New Chat' and self.message_count > 0:
            first_message = self.messages.filter_by(role='user').first()
            if first_message:
                # Take first 50 chars and add ellipsis if longer
                content = first_message.content.strip()
                self.title = content[:50] + ('...' if len(content) > 50 else '')
                db.session.commit()

    def attach_document(self, document_id):
        """
        Attach a document to this chat session for context-aware conversations.

        Args:
            document_id (int): ID of the document to attach
        """
        self.document_id = document_id
        db.session.commit()

    def detach_document(self):
        """Remove document attachment from this session"""
        self.document_id = None
        db.session.commit()

    def has_document(self):
        """Check if this session has an attached document"""
        return self.document_id is not None

    def get_conversation_summary(self):
        """
        Get a summary of the conversation for display purposes.

        Returns:
            dict: Summary with title, message count, tokens, etc.
        """
        return {
            'id': self.id,
            'title': self.title,
            'message_count': self.message_count,
            'total_tokens_used': self.total_tokens_used,
            'has_document': self.has_document(),
            'document_name': self.document.original_filename if self.document else None,
            'created_at': self.created_at.isoformat(),
            'last_message_at': self.last_message_at.isoformat() if self.last_message_at else None,
            'time_ago': self._format_time_ago()
        }

    def _format_time_ago(self):
        """Format the last message time as a human-readable string"""
        if not self.last_message_at:
            return 'Never'

        delta = datetime.utcnow() - self.last_message_at

        if delta.days > 0:
            return f"{delta.days} day{'s' if delta.days != 1 else ''} ago"
        elif delta.seconds >= 3600:
            hours = delta.seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif delta.seconds >= 60:
            minutes = delta.seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        else:
            return "Just now"

    def to_dict(self):
        """Convert session to dictionary for API responses"""
        return {
            'id': self.id,
            'title': self.title,
            'user_id': self.user_id,
            'document_id': self.document_id,
            'message_count': self.message_count,
            'total_tokens_used': self.total_tokens_used,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'last_message_at': self.last_message_at.isoformat() if self.last_message_at else None
        }


# Import ChatMessage to avoid circular import issues
from app.models.chat_message import ChatMessage
