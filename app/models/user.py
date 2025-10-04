from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db
from app.models.base import BaseModel


class User(UserMixin, BaseModel):
    __tablename__ = 'users'

    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # AI Features
    ai_enabled = db.Column(db.Boolean, default=True, nullable=False)  # Changed default to True
    ai_provider = db.Column(db.String(20), default='gemini', nullable=True)

    # Relationships
    decks = db.relationship('Deck', backref='owner', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<User {self.username}>'

    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check if password matches hash"""
        return check_password_hash(self.password_hash, password)

    def get_deck_count(self):
        """Get total number of decks owned by user"""
        return len(self.decks)

    def get_total_cards(self):
        """Get total number of cards across all decks"""
        return sum(len(deck.flashcards) for deck in self.decks)

    def has_ai_access(self):
        """Check if user has access to AI features"""
        return self.ai_enabled
