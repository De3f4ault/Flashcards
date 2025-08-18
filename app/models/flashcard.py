from app.extensions import db
from app.models.base import BaseModel


class Flashcard(BaseModel):
    __tablename__ = 'flashcards'

    front_text = db.Column(db.Text, nullable=False)
    back_text = db.Column(db.Text, nullable=False)
    difficulty = db.Column(db.Integer, default=1)  # 1-5 difficulty scale
    times_studied = db.Column(db.Integer, default=0)
    times_correct = db.Column(db.Integer, default=0)

    # Foreign Keys
    deck_id = db.Column(db.Integer, db.ForeignKey('decks.id'), nullable=False)

    def __repr__(self):
        return f'<Flashcard {self.front_text[:20]}...>'

    def get_accuracy(self):
        """Calculate accuracy percentage"""
        if self.times_studied == 0:
            return 0
        return round((self.times_correct / self.times_studied) * 100, 1)

    def mark_studied(self, correct):
        """Mark card as studied and update statistics"""
        self.times_studied += 1
        if correct:
            self.times_correct += 1

        # Simple difficulty adjustment based on performance
        accuracy = self.get_accuracy()
        if accuracy >= 80 and self.difficulty < 5:
            self.difficulty += 1
        elif accuracy < 50 and self.difficulty > 1:
            self.difficulty -= 1

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'front_text': self.front_text,
            'back_text': self.back_text,
            'difficulty': self.difficulty,
            'times_studied': self.times_studied,
            'times_correct': self.times_correct,
            'accuracy': self.get_accuracy(),
            'created_at': self.created_at.isoformat()
        }
