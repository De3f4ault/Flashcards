"""
Chat Message Model - Stores individual messages in chat sessions
"""

from datetime import datetime
from app.extensions import db
from sqlalchemy import Enum
import enum


class MessageRole(enum.Enum):
    """Enumeration for message roles in chat"""
    USER = 'user'
    ASSISTANT = 'assistant'
    SYSTEM = 'system'


class ChatMessage(db.Model):
    """
    Represents a single message in a chat conversation.
    Messages can be from the user, AI assistant, or system.
    """

    __tablename__ = 'chat_messages'

    # Primary Key
    id = db.Column(db.Integer, primary_key=True)

    # Relationships
    session_id = db.Column(db.Integer, db.ForeignKey('chat_sessions.id'), nullable=False)

    # Message Content
    role = db.Column(Enum(MessageRole), nullable=False)
    content = db.Column(db.Text, nullable=False)

    # Metadata
    tokens_used = db.Column(db.Integer, default=0, nullable=False)
    model_used = db.Column(db.String(50), nullable=True)  # e.g., 'gemini-flash-1.5'
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Error tracking (for failed AI responses)
    has_error = db.Column(db.Boolean, default=False, nullable=False)
    error_message = db.Column(db.Text, nullable=True)

    def __repr__(self):
        role_name = self.role.value if isinstance(self.role, MessageRole) else self.role
        content_preview = self.content[:50] + '...' if len(self.content) > 50 else self.content
        return f'<ChatMessage {self.id}: {role_name} - {content_preview}>'

    def estimate_tokens(self):
        """
        Estimate token count for this message.
        Uses rough approximation of 1 token per 4 characters.

        Returns:
            int: Estimated token count
        """
        if self.tokens_used > 0:
            return self.tokens_used
        return len(self.content) // 4

    def format_for_gemini(self):
        """
        Format message for Gemini API request.

        Returns:
            dict: Message in Gemini's expected format
        """
        role_value = self.role.value if isinstance(self.role, MessageRole) else self.role

        # Gemini uses 'model' instead of 'assistant'
        gemini_role = 'model' if role_value == 'assistant' else role_value

        return {
            'role': gemini_role,
            'parts': [{'text': self.content}]
        }

    def is_from_user(self):
        """Check if message is from user"""
        role_value = self.role.value if isinstance(self.role, MessageRole) else self.role
        return role_value == 'user'

    def is_from_assistant(self):
        """Check if message is from AI assistant"""
        role_value = self.role.value if isinstance(self.role, MessageRole) else self.role
        return role_value == 'assistant'

    def is_system_message(self):
        """Check if message is a system message"""
        role_value = self.role.value if isinstance(self.role, MessageRole) else self.role
        return role_value == 'system'

    def get_formatted_timestamp(self):
        """
        Get human-readable timestamp.

        Returns:
            str: Formatted timestamp (e.g., "2:30 PM" or "Jan 15, 2:30 PM")
        """
        now = datetime.utcnow()

        # If message is from today, show only time
        if self.timestamp.date() == now.date():
            return self.timestamp.strftime('%I:%M %p')

        # If from this year, show month/day and time
        if self.timestamp.year == now.year:
            return self.timestamp.strftime('%b %d, %I:%M %p')

        # Otherwise show full date
        return self.timestamp.strftime('%b %d %Y, %I:%M %p')

    def to_dict(self):
        """
        Convert message to dictionary for API responses.

        Returns:
            dict: Message data
        """
        role_value = self.role.value if isinstance(self.role, MessageRole) else self.role

        return {
            'id': self.id,
            'session_id': self.session_id,
            'role': role_value,
            'content': self.content,
            'tokens_used': self.tokens_used,
            'model_used': self.model_used,
            'timestamp': self.timestamp.isoformat(),
            'formatted_timestamp': self.get_formatted_timestamp(),
            'has_error': self.has_error,
            'error_message': self.error_message
        }

    @staticmethod
    def create_user_message(session_id, content):
        """
        Factory method to create a user message.

        Args:
            session_id (int): Chat session ID
            content (str): Message content

        Returns:
            ChatMessage: New user message
        """
        return ChatMessage(
            session_id=session_id,
            role=MessageRole.USER,
            content=content,
            timestamp=datetime.utcnow()
        )

    @staticmethod
    def create_assistant_message(session_id, content, tokens_used=0, model_used=None):
        """
        Factory method to create an assistant message.

        Args:
            session_id (int): Chat session ID
            content (str): Message content
            tokens_used (int): Number of tokens used
            model_used (str): Model identifier

        Returns:
            ChatMessage: New assistant message
        """
        return ChatMessage(
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            content=content,
            tokens_used=tokens_used,
            model_used=model_used,
            timestamp=datetime.utcnow()
        )

    @staticmethod
    def create_system_message(session_id, content):
        """
        Factory method to create a system message.

        Args:
            session_id (int): Chat session ID
            content (str): Message content

        Returns:
            ChatMessage: New system message
        """
        return ChatMessage(
            session_id=session_id,
            role=MessageRole.SYSTEM,
            content=content,
            timestamp=datetime.utcnow()
        )

    @staticmethod
    def create_error_message(session_id, error_text):
        """
        Factory method to create an error message from assistant.

        Args:
            session_id (int): Chat session ID
            error_text (str): Error description

        Returns:
            ChatMessage: New error message
        """
        return ChatMessage(
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            content="I apologize, but I encountered an error processing your request.",
            has_error=True,
            error_message=error_text,
            timestamp=datetime.utcnow()
        )
