from datetime import datetime, timedelta
from app.extensions import db
from app.models.base import BaseModel


class Flashcard(BaseModel):
    __tablename__ = 'flashcards'

    # ========== ORIGINAL FIELDS (Unchanged) ==========
    front_text = db.Column(db.Text, nullable=False)
    back_text = db.Column(db.Text, nullable=False)
    difficulty = db.Column(db.Integer, default=1)  # 1-5 difficulty scale (legacy)
    times_studied = db.Column(db.Integer, default=0)
    times_correct = db.Column(db.Integer, default=0)

    # ========== SM-2 SPACED REPETITION FIELDS ==========
    ease_factor = db.Column(db.Float, default=2.5)  # How "easy" card is (1.3-3.0)
    interval = db.Column(db.Integer, default=0)  # Days until next review
    repetitions = db.Column(db.Integer, default=0)  # Consecutive correct answers
    next_review_date = db.Column(db.DateTime, default=lambda: datetime.utcnow())
    last_reviewed = db.Column(db.DateTime, nullable=True)
    learning_state = db.Column(db.String(20), default='new')  # new/learning/review/mastered

    # ========== AI FEATURES FIELDS ==========
    ai_generated = db.Column(db.Boolean, default=False, nullable=False)
    generation_prompt = db.Column(db.Text, nullable=True)  # Store the prompt that generated this card
    ai_provider = db.Column(db.String(20), nullable=True)  # Which AI generated it (gemini, openai, etc.)

    # Foreign Keys
    deck_id = db.Column(db.Integer, db.ForeignKey('decks.id'), nullable=False)

    def __repr__(self):
        return f'<Flashcard {self.front_text[:20]}...>'

    # ========== PROPERTY ACCESSORS (for backward compatibility) ==========

    @property
    def front(self):
        """Alias for front_text (backward compatibility)"""
        return self.front_text

    @front.setter
    def front(self, value):
        self.front_text = value

    @property
    def back(self):
        """Alias for back_text (backward compatibility)"""
        return self.back_text

    @back.setter
    def back(self, value):
        self.back_text = value

    # ========== ORIGINAL METHODS (Preserved) ==========

    def get_accuracy(self):
        """Calculate accuracy percentage"""
        if self.times_studied == 0:
            return 0
        return round((self.times_correct / self.times_studied) * 100, 1)

    def mark_studied(self, correct):
        """
        Mark card as studied and update statistics (LEGACY METHOD)

        ⚠️ Note: This method is preserved for backward compatibility.
        New code should use process_sm2_review() for spaced repetition.
        """
        self.times_studied += 1
        if correct:
            self.times_correct += 1

        # Simple difficulty adjustment based on performance
        accuracy = self.get_accuracy()
        if accuracy >= 80 and self.difficulty < 5:
            self.difficulty += 1
        elif accuracy < 50 and self.difficulty > 1:
            self.difficulty -= 1

    # ========== SM-2 SPACED REPETITION METHODS ==========

    def is_due_for_review(self):
        """Check if card is due for review today"""
        if self.learning_state == 'new':
            return True
        return datetime.utcnow() >= self.next_review_date

    def days_until_due(self):
        """Calculate days until card is due for review"""
        if self.learning_state == 'new':
            return 0
        if not self.next_review_date:
            return 0
        delta = self.next_review_date - datetime.utcnow()
        return max(0, delta.days)

    def process_sm2_review(self, quality):
        """
        Process a review using the SM-2 spaced repetition algorithm

        This is the CORE method for spaced repetition learning!

        Args:
            quality (int): Quality of recall (0-5)
                5 = Perfect recall (immediate, confident)
                4 = Correct after hesitation
                3 = Correct with difficulty
                2 = Incorrect, but answer seemed familiar
                1 = Incorrect, but remembered after seeing answer
                0 = Complete blackout, no recollection

        Returns:
            dict: Updated scheduling information
                - ease_factor: New ease factor
                - interval: Days until next review
                - repetitions: Number of successful reviews
                - next_review_date: When to show this card next
                - learning_state: Current learning state

        Algorithm Source: https://www.supermemo.com/en/archives1990-2015/english/ol/sm2
        """
        # Update basic statistics
        self.times_studied += 1
        self.last_reviewed = datetime.utcnow()

        # Quality >= 3 means correct answer
        is_correct = quality >= 3
        if is_correct:
            self.times_correct += 1

        # ========== SM-2 ALGORITHM CORE ==========

        if quality < 3:
            # FAILED: Reset card to beginning
            self.repetitions = 0
            self.interval = 0
            self.learning_state = 'learning'
        else:
            # CORRECT: Advance to next interval
            if self.repetitions == 0:
                # First successful review: 1 day
                self.interval = 1
                self.learning_state = 'learning'
            elif self.repetitions == 1:
                # Second successful review: 6 days
                self.interval = 6
                self.learning_state = 'review'
            else:
                # Subsequent reviews: multiply by ease factor
                self.interval = round(self.interval * self.ease_factor)
                self.learning_state = 'review'

            self.repetitions += 1

            # Mark as mastered if interval exceeds 21 days
            if self.interval > 21:
                self.learning_state = 'mastered'

        # Update ease factor based on quality
        # Formula: EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
        ease_change = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
        self.ease_factor = max(1.3, self.ease_factor + ease_change)

        # Calculate next review date
        self.next_review_date = datetime.utcnow() + timedelta(days=self.interval)

        # Update legacy difficulty field for backward compatibility
        if self.ease_factor >= 2.5:
            self.difficulty = min(5, int(self.ease_factor))
        else:
            self.difficulty = max(1, int(self.ease_factor))

        return {
            'ease_factor': round(self.ease_factor, 2),
            'interval': self.interval,
            'repetitions': self.repetitions,
            'next_review_date': self.next_review_date,
            'learning_state': self.learning_state
        }

    def get_quality_from_boolean(self, correct, confidence='medium'):
        """
        Convert simple correct/incorrect to SM-2 quality rating

        This helper allows backward compatibility with existing boolean-based study code.

        Args:
            correct (bool): Whether the answer was correct
            confidence (str): Confidence level - 'low', 'medium', 'high'

        Returns:
            int: Quality rating (0-5) for SM-2 algorithm

        Examples:
            >>> card.get_quality_from_boolean(True, 'high')  # Returns 5 (perfect)
            >>> card.get_quality_from_boolean(True, 'low')   # Returns 3 (difficult)
            >>> card.get_quality_from_boolean(False, 'low')  # Returns 1 (recognized)
        """
        if not correct:
            return 1  # Incorrect, but recognized after seeing answer

        # Map confidence levels to quality ratings
        confidence_map = {
            'low': 3,      # Correct with difficulty
            'medium': 4,   # Correct after hesitation
            'high': 5      # Perfect recall
        }
        return confidence_map.get(confidence, 4)

    # ========== ENHANCED to_dict METHOD ==========

    def to_dict(self):
        """
        Convert flashcard to dictionary representation

        Includes both original fields and new SM-2 fields for complete data export.
        """
        return {
            # Original fields
            'id': self.id,
            'front_text': self.front_text,
            'back_text': self.back_text,
            'difficulty': self.difficulty,
            'times_studied': self.times_studied,
            'times_correct': self.times_correct,
            'accuracy': self.get_accuracy(),
            'created_at': self.created_at.isoformat(),

            # SM-2 fields
            'ease_factor': round(self.ease_factor, 2),
            'interval': self.interval,
            'repetitions': self.repetitions,
            'next_review_date': self.next_review_date.isoformat() if self.next_review_date else None,
            'last_reviewed': self.last_reviewed.isoformat() if self.last_reviewed else None,
            'learning_state': self.learning_state,

            # AI fields
            'ai_generated': self.ai_generated,
            'generation_prompt': self.generation_prompt,
            'ai_provider': self.ai_provider,

            # Computed fields
            'is_due': self.is_due_for_review(),
            'days_until_due': self.days_until_due()
        }
