from app.extensions import db
from app.models.base import BaseModel
from sqlalchemy import Text


class MCCard(BaseModel):
    """
    Multiple Choice Card Model
    Stores AI-generated or manually created MC questions
    """
    __tablename__ = 'mc_cards'

    # Core Question Data
    question_text = db.Column(Text, nullable=False)

    # Choices (stored as JSON for flexibility)
    choice_a = db.Column(Text, nullable=False)
    choice_b = db.Column(Text, nullable=False)
    choice_c = db.Column(Text, nullable=False)
    choice_d = db.Column(Text, nullable=False)

    # Correct Answer (stores letter: 'A', 'B', 'C', or 'D')
    correct_answer = db.Column(db.String(1), nullable=False)

    # Misconception Explanations (what's wrong with each incorrect choice)
    misconception_a = db.Column(Text, nullable=True)
    misconception_b = db.Column(Text, nullable=True)
    misconception_c = db.Column(Text, nullable=True)
    misconception_d = db.Column(Text, nullable=True)

    # Metadata
    difficulty = db.Column(db.Integer, default=3)  # 1-5 scale
    concept_tags = db.Column(Text, nullable=True)  # Comma-separated tags

    # AI Generation Metadata
    ai_generated = db.Column(db.Boolean, default=False, nullable=False)
    generation_topic = db.Column(db.String(200), nullable=True)
    generation_context = db.Column(Text, nullable=True)
    ai_provider = db.Column(db.String(20), nullable=True)

    # Document Source Fields (Phase 3)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=True)
    document_section = db.Column(db.String(200), nullable=True)  # Future: track specific section

    # Foreign Keys
    deck_id = db.Column(db.Integer, db.ForeignKey('decks.id'), nullable=False)

    # Relationships
    attempts = db.relationship('MCAttempt', backref='card', lazy=True, cascade='all, delete-orphan')
    document = db.relationship('Document', backref=db.backref('mc_cards', lazy='dynamic'))

    def __repr__(self):
        return f'<MCCard {self.question_text[:30]}...>'

    def get_choices_dict(self):
        """Return all choices as a dictionary"""
        return {
            'A': self.choice_a,
            'B': self.choice_b,
            'C': self.choice_c,
            'D': self.choice_d
        }

    def get_misconception(self, choice_letter):
        """Get misconception explanation for a specific choice"""
        misconception_map = {
            'A': self.misconception_a,
            'B': self.misconception_b,
            'C': self.misconception_c,
            'D': self.misconception_d
        }
        return misconception_map.get(choice_letter.upper())

    def is_correct(self, choice_letter):
        """Check if given choice is correct"""
        return choice_letter.upper() == self.correct_answer.upper()

    def get_concept_tags_list(self):
        """Parse comma-separated tags into list"""
        if not self.concept_tags:
            return []
        return [tag.strip() for tag in self.concept_tags.split(',') if tag.strip()]

    def is_document_based(self):
        """Check if this question was generated from a document"""
        return self.document_id is not None

    def get_document_info(self):
        """Get source document information if available"""
        if not self.is_document_based():
            return None

        return {
            'id': self.document.id,
            'filename': self.document.original_filename,
            'file_type': self.document.file_type,
            'section': self.document_section
        } if self.document else None

    def get_accuracy_stats(self):
        """Calculate accuracy statistics from attempts"""
        if not self.attempts:
            return {
                'times_attempted': 0,
                'times_correct': 0,
                'accuracy': 0.0
            }

        times_attempted = len(self.attempts)
        times_correct = sum(1 for attempt in self.attempts if attempt.is_correct)
        accuracy = (times_correct / times_attempted * 100) if times_attempted > 0 else 0.0

        return {
            'times_attempted': times_attempted,
            'times_correct': times_correct,
            'accuracy': round(accuracy, 1)
        }

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        stats = self.get_accuracy_stats()

        data = {
            'id': self.id,
            'question_text': self.question_text,
            'choices': self.get_choices_dict(),
            'correct_answer': self.correct_answer,
            'difficulty': self.difficulty,
            'concept_tags': self.get_concept_tags_list(),
            'ai_generated': self.ai_generated,
            'generation_topic': self.generation_topic,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'stats': stats,
            'is_document_based': self.is_document_based()
        }

        # Include document info if available
        if self.is_document_based():
            data['document_info'] = self.get_document_info()

        return data

    def to_dict_with_answer(self):
        """Include misconception explanations (for review/feedback)"""
        data = self.to_dict()
        data['misconceptions'] = {
            'A': self.misconception_a,
            'B': self.misconception_b,
            'C': self.misconception_c,
            'D': self.misconception_d
        }
        return data
