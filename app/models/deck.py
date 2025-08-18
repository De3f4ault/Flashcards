from app.extensions import db
from app.models.base import BaseModel


class Deck(BaseModel):
    __tablename__ = 'decks'

    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    is_public = db.Column(db.Boolean, default=False, nullable=False)

    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Relationships
    flashcards = db.relationship('Flashcard', backref='deck', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Deck {self.name}>'

    def get_card_count(self):
        """Get number of flashcards in this deck"""
        return len(self.flashcards)

    def can_be_studied(self):
        """Check if deck has cards to study"""
        return self.get_card_count() > 0

    def get_next_card_for_study(self):
        """Get the next card for study session (simple implementation)"""
        if self.flashcards:
            return self.flashcards[0]  # For MVP, just return first card
        return None

    def to_dict_summary(self):
        """Convert to dictionary with summary info"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'card_count': self.get_card_count(),
            'created_at': self.created_at.isoformat(),
            'is_public': self.is_public
        }
