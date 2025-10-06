from app.extensions import db
from app.models.base import BaseModel
from datetime import datetime


class MCAttempt(BaseModel):
    """
    Multiple Choice Attempt Model
    Records each individual answer attempt during a study session
    """
    __tablename__ = 'mc_attempts'

    # Answer Data
    selected_choice = db.Column(db.String(1), nullable=False)  # 'A', 'B', 'C', or 'D'
    is_correct = db.Column(db.Boolean, nullable=False)

    # User Confidence (1-5 scale: 1=Guessing, 5=Certain)
    confidence_rating = db.Column(db.Integer, nullable=True)

    # Time Tracking
    time_spent_seconds = db.Column(db.Integer, default=0)  # Seconds spent on this question

    # Foreign Keys
    card_id = db.Column(db.Integer, db.ForeignKey('mc_cards.id'), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey('mc_sessions.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    def __repr__(self):
        return f'<MCAttempt card={self.card_id} choice={self.selected_choice} correct={self.is_correct}>'

    def get_confidence_label(self):
        """Get human-readable confidence label"""
        if not self.confidence_rating:
            return 'Unknown'

        labels = {
            1: 'Guessing',
            2: 'Uncertain',
            3: 'Moderate',
            4: 'Confident',
            5: 'Certain'
        }
        return labels.get(self.confidence_rating, 'Unknown')

    def get_time_formatted(self):
        """Get formatted time spent (e.g., '45 seconds', '1 minute 23 seconds')"""
        seconds = self.time_spent_seconds

        if seconds < 60:
            return f"{seconds} second{'s' if seconds != 1 else ''}"

        minutes = seconds // 60
        remaining_seconds = seconds % 60

        if remaining_seconds == 0:
            return f"{minutes} minute{'s' if minutes != 1 else ''}"

        return f"{minutes} minute{'s' if minutes != 1 else ''} {remaining_seconds} second{'s' if remaining_seconds != 1 else ''}"

    def was_overconfident(self):
        """
        Check if user was overconfident (high confidence but wrong)
        Returns True if confidence >= 4 but answer was incorrect
        """
        if not self.confidence_rating:
            return False
        return self.confidence_rating >= 4 and not self.is_correct

    def was_underconfident(self):
        """
        Check if user was underconfident (low confidence but correct)
        Returns True if confidence <= 2 but answer was correct
        """
        if not self.confidence_rating:
            return False
        return self.confidence_rating <= 2 and self.is_correct

    def is_well_calibrated(self):
        """
        Check if confidence matches performance
        Well-calibrated means: high confidence + correct OR low confidence + incorrect
        """
        if not self.confidence_rating:
            return None  # Can't determine without confidence rating

        if self.is_correct:
            return self.confidence_rating >= 3  # Correct answers should have moderate+ confidence
        else:
            return self.confidence_rating <= 3  # Incorrect answers should have low-moderate confidence

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'card_id': self.card_id,
            'session_id': self.session_id,
            'selected_choice': self.selected_choice,
            'is_correct': self.is_correct,
            'confidence_rating': self.confidence_rating,
            'confidence_label': self.get_confidence_label(),
            'time_spent_seconds': self.time_spent_seconds,
            'time_formatted': self.get_time_formatted(),
            'created_at': self.created_at.isoformat(),
            'calibration': {
                'overconfident': self.was_overconfident(),
                'underconfident': self.was_underconfident(),
                'well_calibrated': self.is_well_calibrated()
            }
        }

    def to_dict_with_card(self):
        """Include card details in the dictionary"""
        data = self.to_dict()
        if self.card:
            data['card'] = {
                'question_text': self.card.question_text,
                'correct_answer': self.card.correct_answer,
                'difficulty': self.card.difficulty
            }
        return data

    @staticmethod
    def calculate_calibration_stats(attempts):
        """
        Calculate calibration statistics for a collection of attempts

        Args:
            attempts: List of MCAttempt objects

        Returns:
            Dict with calibration metrics
        """
        if not attempts:
            return {
                'total_attempts': 0,
                'overconfident_count': 0,
                'underconfident_count': 0,
                'well_calibrated_count': 0,
                'avg_confidence': 0.0
            }

        attempts_with_confidence = [a for a in attempts if a.confidence_rating]

        if not attempts_with_confidence:
            return {
                'total_attempts': len(attempts),
                'overconfident_count': 0,
                'underconfident_count': 0,
                'well_calibrated_count': 0,
                'avg_confidence': 0.0
            }

        overconfident = sum(1 for a in attempts_with_confidence if a.was_overconfident())
        underconfident = sum(1 for a in attempts_with_confidence if a.was_underconfident())
        well_calibrated = sum(1 for a in attempts_with_confidence if a.is_well_calibrated())
        avg_confidence = sum(a.confidence_rating for a in attempts_with_confidence) / len(attempts_with_confidence)

        return {
            'total_attempts': len(attempts),
            'attempts_with_confidence': len(attempts_with_confidence),
            'overconfident_count': overconfident,
            'underconfident_count': underconfident,
            'well_calibrated_count': well_calibrated,
            'avg_confidence': round(avg_confidence, 1),
            'overconfident_percentage': round((overconfident / len(attempts_with_confidence)) * 100, 1),
            'underconfident_percentage': round((underconfident / len(attempts_with_confidence)) * 100, 1),
            'well_calibrated_percentage': round((well_calibrated / len(attempts_with_confidence)) * 100, 1)
        }
