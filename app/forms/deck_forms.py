from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, BooleanField, SubmitField, SelectField, FieldList, FormField
from wtforms.validators import DataRequired, Length, Optional
from app.forms.base_forms import BaseForm


class DeckForm(BaseForm):
    """Create/Edit deck form"""
    name = StringField(
        'Deck Name',
        validators=[
            DataRequired(message='Deck name is required'),
            Length(min=1, max=100, message='Deck name must be between 1 and 100 characters')
        ],
        render_kw={'placeholder': 'Enter deck name', 'class': 'form-control'}
    )
    description = TextAreaField(
        'Description',
        validators=[
            Optional(),
            Length(max=500, message='Description must be less than 500 characters')
        ],
        render_kw={
            'placeholder': 'Describe what this deck is about (optional)',
            'class': 'form-control',
            'rows': 3
        }
    )
    is_public = BooleanField(
        'Make this deck public',
        render_kw={'class': 'form-check-input'},
        description='Public decks can be viewed and copied by other users'
    )
    submit = SubmitField(
        'Save Deck',
        render_kw={'class': 'btn btn-primary'}
    )


class FlashcardForm(BaseForm):
    """Create/Edit flashcard form"""
    front_text = TextAreaField(
        'Front (Question)',
        validators=[
            DataRequired(message='Front text is required'),
            Length(min=1, max=1000, message='Front text must be between 1 and 1000 characters')
        ],
        render_kw={
            'placeholder': 'Enter the question or prompt',
            'class': 'form-control',
            'rows': 3
        }
    )
    back_text = TextAreaField(
        'Back (Answer)',
        validators=[
            DataRequired(message='Back text is required'),
            Length(min=1, max=1000, message='Back text must be between 1 and 1000 characters')
        ],
        render_kw={
            'placeholder': 'Enter the answer or explanation',
            'class': 'form-control',
            'rows': 3
        }
    )
    submit = SubmitField(
        'Save Flashcard',
        render_kw={'class': 'btn btn-primary'}
    )


class QuickFlashcardForm(BaseForm):
    """Quick add flashcard form (simplified)"""
    front_text = StringField(
        'Question',
        validators=[DataRequired(), Length(min=1, max=200)],
        render_kw={'placeholder': 'Quick question', 'class': 'form-control'}
    )
    back_text = StringField(
        'Answer',
        validators=[DataRequired(), Length(min=1, max=200)],
        render_kw={'placeholder': 'Quick answer', 'class': 'form-control'}
    )
    submit = SubmitField(
        'Add Card',
        render_kw={'class': 'btn btn-success btn-sm'}
    )


class BulkFlashcardForm(BaseForm):
    """Bulk add flashcards form"""
    cards_text = TextAreaField(
        'Cards (one per line, separate front and back with |)',
        validators=[
            DataRequired(message='Please enter at least one card')
        ],
        render_kw={
            'placeholder': 'Question 1 | Answer 1\nQuestion 2 | Answer 2\nQuestion 3 | Answer 3',
            'class': 'form-control',
            'rows': 10
        },
        description='Enter one card per line. Separate question and answer with a pipe (|) symbol.'
    )
    submit = SubmitField(
        'Add All Cards',
        render_kw={'class': 'btn btn-success'}
    )

    def parse_cards(self):
        """Parse the bulk text into individual cards"""
        cards = []
        if self.cards_text.data:
            lines = self.cards_text.data.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line and '|' in line:
                    parts = line.split('|', 1)  # Split on first pipe only
                    if len(parts) == 2:
                        front = parts[0].strip()
                        back = parts[1].strip()
                        if front and back:
                            cards.append({
                                'front_text': front,
                                'back_text': back
                            })
        return cards


class StudyOptionsForm(BaseForm):
    """Study session options form"""
    study_mode = SelectField(
        'Study Mode',
        choices=[
            ('random', 'Random Order'),
            ('newest', 'Newest First'),
            ('oldest', 'Oldest First'),
            ('difficulty_asc', 'Easy to Hard'),
            ('difficulty_desc', 'Hard to Easy'),
            ('accuracy_asc', 'Worst Performance First'),
            ('accuracy_desc', 'Best Performance First'),
            ('least_studied', 'Least Studied First')
        ],
        default='random',
        render_kw={'class': 'form-control'}
    )
    card_limit = SelectField(
        'Number of Cards',
        choices=[
            (0, 'All Cards'),
            (5, '5 Cards'),
            (10, '10 Cards'),
            (15, '15 Cards'),
            (20, '20 Cards'),
            (25, '25 Cards'),
            (50, '50 Cards')
        ],
        coerce=int,
        default=0,
        render_kw={'class': 'form-control'}
    )
    submit = SubmitField(
        'Start Study Session',
        render_kw={'class': 'btn btn-success btn-lg'}
    )


class DeckSearchForm(BaseForm):
    """Search decks form"""
    query = StringField(
        'Search Decks',
        validators=[Length(max=100)],
        render_kw={
            'placeholder': 'Search by name or description...',
            'class': 'form-control'
        }
    )
    include_public = BooleanField(
        'Include public decks',
        default=True,
        render_kw={'class': 'form-check-input'}
    )
    submit = SubmitField(
        'Search',
        render_kw={'class': 'btn btn-outline-primary'}
    )


class DuplicateDeckForm(BaseForm):
    """Form to duplicate/copy a deck"""
    name = StringField(
        'New Deck Name',
        validators=[
            DataRequired(message='Deck name is required'),
            Length(min=1, max=100)
        ],
        render_kw={'class': 'form-control'}
    )
    submit = SubmitField(
        'Copy Deck',
        render_kw={'class': 'btn btn-success'}
    )
