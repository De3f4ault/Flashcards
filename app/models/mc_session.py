from app.extensions import db
from app.models.base import BaseModel
from datetime import datetime


class MCSession(BaseModel):
    """
    Multiple Choice Study Session Model
    Tracks each study session with basic metrics
    """
    __tablename__ = 'mc_sessions'

    # Session Info
    session_title = db.Column(db.String(200), nullable=True)

    # Timestamps
    started_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    completed_at = db.Column(db.DateTime, nullable=True)

    # Session Status
    is_completed = db.Column(db.Boolean, default=False, nullable=False)

    # Basic Metrics (calculated from attempts)
    total_questions = db.Column(db.Integer, default=0)
    correct_count = db.Column(db.Integer, default=0)

    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    deck_id = db.Column(db.Integer, db.ForeignKey('decks.id'), nullable=False)

    # Relationships
    attempts = db.relationship('MCAttempt', backref='session', lazy=True,
                              cascade='all, delete-orphan',
                              order_by='MCAttempt.created_at')

    def __repr__(self):
        return f'<MCSession {self.id} - {self.session_title or "Untitled"}>'

    def get_duration_seconds(self):
        """Calculate session duration in seconds"""
        if not self.completed_at:
            # Session still in progress
            return int((datetime.utcnow() - self.started_at).total_seconds())
        return int((self.completed_at - self.started_at).total_seconds())

    def get_duration_formatted(self):
        """Get human-readable duration (e.g., '6 minutes 32 seconds')"""
        seconds = self.get_duration_seconds()

        if seconds < 60:
            return f"{seconds} seconds"

        minutes = seconds // 60
        remaining_seconds = seconds % 60

        if minutes < 60:
            return f"{minutes} minute{'s' if minutes != 1 else ''} {remaining_seconds} second{'s' if remaining_seconds != 1 else ''}"

        hours = minutes // 60
        remaining_minutes = minutes % 60
        return f"{hours} hour{'s' if hours != 1 else ''} {remaining_minutes} minute{'s' if remaining_minutes != 1 else ''}"

    def get_accuracy_percentage(self):
        """Calculate accuracy as percentage"""
        if self.total_questions == 0:
            return 0.0
        return round((self.correct_count / self.total_questions) * 100, 1)

    def get_average_time_per_question(self):
        """Calculate average time spent per question in seconds"""
        if self.total_questions == 0:
            return 0
        return round(self.get_duration_seconds() / self.total_questions)

    def get_average_confidence(self):
        """Calculate average confidence rating across all attempts"""
        if not self.attempts:
            return 0.0

        confidences = [a.confidence_rating for a in self.attempts if a.confidence_rating]
        if not confidences:
            return 0.0

        return round(sum(confidences) / len(confidences), 1)

    def mark_complete(self):
        """Mark session as completed and update metrics"""
        self.is_completed = True
        self.completed_at = datetime.utcnow()

        # Recalculate metrics from attempts
        self.total_questions = len(self.attempts)
        self.correct_count = sum(1 for a in self.attempts if a.is_correct)

        return self

    def add_attempt_result(self, is_correct):
        """
        Update session metrics when an attempt is recorded
        (Called after each question is answered)
        """
        self.total_questions += 1
        if is_correct:
            self.correct_count += 1

    def get_summary_stats(self):
        """Get comprehensive summary statistics for the session"""
        return {
            'session_id': self.id,
            'title': self.session_title or 'Untitled Session',
            'started_at': self.started_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'is_completed': self.is_completed,
            'duration': {
                'seconds': self.get_duration_seconds(),
                'formatted': self.get_duration_formatted()
            },
            'questions': {
                'total': self.total_questions,
                'correct': self.correct_count,
                'incorrect': self.total_questions - self.correct_count
            },
            'accuracy': self.get_accuracy_percentage(),
            'avg_time_per_question': self.get_average_time_per_question(),
            'avg_confidence': self.get_average_confidence()
        }

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'session_title': self.session_title,
            'deck_id': self.deck_id,
            'started_at': self.started_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'is_completed': self.is_completed,
            'total_questions': self.total_questions,
            'correct_count': self.correct_count,
            'accuracy': self.get_accuracy_percentage(),
            'duration_seconds': self.get_duration_seconds(),
            'created_at': self.created_at.isoformat()
        }
