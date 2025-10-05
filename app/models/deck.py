from app.extensions import db
from app.models.base import BaseModel
from sqlalchemy import func, case, or_
from datetime import datetime, timedelta


class Deck(BaseModel):
    __tablename__ = 'decks'

    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    is_public = db.Column(db.Boolean, default=False, nullable=False)

    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Relationships
    flashcards = db.relationship('Flashcard', backref='deck', lazy=True, cascade='all, delete-orphan')
    mc_cards = db.relationship('MCCard', backref='deck', lazy=True, cascade='all, delete-orphan')  # NEW

    def __repr__(self):
        return f'<Deck {self.name}>'

    # ============================================================================
    # ORIGINAL METHODS (Preserved)
    # ============================================================================

    def get_card_count(self):
        """Get number of flashcards in this deck"""
        return len(self.flashcards)

    def get_mc_card_count(self):
        """Get number of MC cards in this deck"""
        return len(self.mc_cards)

    def can_be_studied(self):
        """Check if deck has cards to study"""
        return self.get_card_count() > 0 or self.get_mc_card_count() > 0

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
            'mc_card_count': self.get_mc_card_count(),
            'created_at': self.created_at.isoformat(),
            'is_public': self.is_public
        }

    # Rest of the class remains the same...
    def search_cards(self, query=None, learning_state=None, difficulty=None,
                     sort_by='created_desc', date_from=None, date_to=None):
        from app.models.flashcard import Flashcard
        cards_query = Flashcard.query.filter_by(deck_id=self.id)
        if query:
            search_term = f"%{query.lower()}%"
            cards_query = cards_query.filter(
                or_(
                    func.lower(Flashcard.front_text).like(search_term),
                    func.lower(Flashcard.back_text).like(search_term)
                )
            )
        if learning_state:
            cards_query = cards_query.filter(Flashcard.learning_state == learning_state)
        if difficulty:
            cards_query = self._apply_difficulty_filter(cards_query, difficulty)
        if date_from:
            cards_query = cards_query.filter(Flashcard.created_at >= date_from)
        if date_to:
            cards_query = cards_query.filter(Flashcard.created_at <= date_to)
        cards_query = self._apply_sorting(cards_query, sort_by)
        return cards_query

    def _apply_difficulty_filter(self, query, difficulty):
        from app.models.flashcard import Flashcard
        accuracy = case(
            (Flashcard.times_studied > 0,
             (Flashcard.times_correct * 100.0) / Flashcard.times_studied),
            else_=100.0
        )
        if difficulty == 'easy':
            query = query.filter(
                or_(
                    accuracy >= 80,
                    Flashcard.ease_factor > 2.5
                )
            )
        elif difficulty == 'medium':
            query = query.filter(
                or_(
                    accuracy.between(50, 80),
                    Flashcard.ease_factor.between(2.0, 2.5)
                )
            )
        elif difficulty == 'hard':
            query = query.filter(
                or_(
                    accuracy < 50,
                    Flashcard.ease_factor < 2.0
                )
            )
        return query

    def _apply_sorting(self, query, sort_by):
        from app.models.flashcard import Flashcard
        accuracy = case(
            (Flashcard.times_studied > 0,
             (Flashcard.times_correct * 100.0) / Flashcard.times_studied),
            else_=0.0
        )
        sort_options = {
            'created_desc': Flashcard.created_at.desc(),
            'created_asc': Flashcard.created_at.asc(),
            'alpha_asc': Flashcard.front_text.asc(),
            'alpha_desc': Flashcard.front_text.desc(),
            'accuracy_high': accuracy.desc(),
            'accuracy_low': accuracy.asc(),
            'studied_most': Flashcard.times_studied.desc(),
            'studied_least': Flashcard.times_studied.asc(),
            'difficulty_high': Flashcard.ease_factor.asc(),
            'difficulty_low': Flashcard.ease_factor.desc(),
            'due_soon': Flashcard.next_review_date.asc(),
        }
        sort_expression = sort_options.get(sort_by, Flashcard.created_at.desc())
        return query.order_by(sort_expression)

    def get_cards_by_state(self, state):
        from app.models.flashcard import Flashcard
        return Flashcard.query.filter_by(
            deck_id=self.id,
            learning_state=state
        ).all()

    def get_cards_statistics(self):
        from app.models.flashcard import Flashcard
        stats = {
            'total': 0,
            'new': 0,
            'learning': 0,
            'review': 0,
            'mastered': 0,
            'due_today': 0,
            'avg_accuracy': 0.0,
            'avg_difficulty': 0.0,
            'total_studied': 0
        }
        cards = Flashcard.query.filter_by(deck_id=self.id).all()
        if not cards:
            return stats
        today = datetime.utcnow()
        stats['total'] = len(cards)
        stats['new'] = sum(1 for c in cards if c.learning_state == 'new')
        stats['learning'] = sum(1 for c in cards if c.learning_state == 'learning')
        stats['review'] = sum(1 for c in cards if c.learning_state == 'review')
        stats['mastered'] = sum(1 for c in cards if c.learning_state == 'mastered')
        stats['due_today'] = sum(1 for c in cards if c.is_due_for_review())
        stats['total_studied'] = sum(c.times_studied for c in cards)
        studied_cards = [c for c in cards if c.times_studied > 0]
        if studied_cards:
            total_accuracy = sum(
                (c.times_correct / c.times_studied * 100)
                for c in studied_cards
            )
            stats['avg_accuracy'] = round(total_accuracy / len(studied_cards), 1)
        stats['avg_difficulty'] = round(
            sum(c.ease_factor for c in cards) / len(cards), 1
        ) if cards else 0
        return stats

    def get_difficulty_distribution(self):
        from app.models.flashcard import Flashcard
        cards = Flashcard.query.filter_by(deck_id=self.id).all()
        distribution = {
            'easy': 0,
            'medium': 0,
            'hard': 0,
            'unstudied': 0
        }
        for card in cards:
            if card.times_studied == 0:
                distribution['unstudied'] += 1
            else:
                accuracy = (card.times_correct / card.times_studied) * 100
                if accuracy >= 80 or card.ease_factor > 2.5:
                    distribution['easy'] += 1
                elif accuracy >= 50 or card.ease_factor >= 2.0:
                    distribution['medium'] += 1
                else:
                    distribution['hard'] += 1
        return distribution

    def to_dict_detailed(self):
        stats = self.get_cards_statistics()
        difficulty_dist = self.get_difficulty_distribution()
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'is_public': self.is_public,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'statistics': stats,
            'difficulty_distribution': difficulty_dist,
            'user_id': self.user_id,
            'mc_card_count': self.get_mc_card_count()
        }
