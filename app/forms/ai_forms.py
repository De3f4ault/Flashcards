from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, IntegerField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Optional


class AIGenerateCardsForm(FlaskForm):
    """Form for AI-powered flashcard generation"""

    topic = StringField(
        'Topic or Subject',
        validators=[
            DataRequired(message='Please enter a topic'),
            Length(min=3, max=200, message='Topic must be between 3 and 200 characters')
        ],
        render_kw={
            'placeholder': 'e.g., Spanish irregular verbs, Python data structures, World War 2 battles',
            'class': 'form-control'
        }
    )

    card_count = IntegerField(
        'Number of Cards',
        validators=[
            DataRequired(message='Please specify number of cards'),
            NumberRange(min=1, max=50, message='Must generate between 1 and 50 cards')
        ],
        default=10,
        render_kw={'class': 'form-control'}
    )

    difficulty = SelectField(
        'Difficulty Level',
        choices=[
            ('easy', 'Easy - Basic recall and definitions'),
            ('medium', 'Medium - Understanding and application'),
            ('hard', 'Hard - Analysis and complex concepts')
        ],
        default='medium',
        validators=[DataRequired()],
        render_kw={'class': 'form-control'}
    )

    context = TextAreaField(
        'Additional Instructions (Optional)',
        validators=[
            Optional(),
            Length(max=500, message='Additional context must be less than 500 characters')
        ],
        render_kw={
            'placeholder': 'e.g., Focus on practical examples, Include only present tense, Suitable for beginners',
            'class': 'form-control',
            'rows': 3
        }
    )

    submit = SubmitField('Generate Cards with AI', render_kw={'class': 'btn btn-primary'})


class AIEnhanceCardForm(FlaskForm):
    """Form for AI-powered card enhancement"""

    enhancement_type = SelectField(
        'Enhancement Type',
        choices=[
            ('clarity', 'Make Clearer - Improve question and answer clarity'),
            ('examples', 'Add Examples - Include concrete examples'),
            ('simplify', 'Simplify - Use simpler language'),
            ('detail', 'Add Detail - Provide more comprehensive answer')
        ],
        default='clarity',
        validators=[DataRequired()],
        render_kw={'class': 'form-control'}
    )

    submit = SubmitField('Enhance Card', render_kw={'class': 'btn btn-success'})


class AIBulkEnhanceForm(FlaskForm):
    """Form for enhancing multiple cards at once"""

    enhancement_type = SelectField(
        'Enhancement Type',
        choices=[
            ('clarity', 'Make Clearer'),
            ('examples', 'Add Examples'),
            ('simplify', 'Simplify Language'),
            ('detail', 'Add More Detail')
        ],
        default='clarity',
        validators=[DataRequired()],
        render_kw={'class': 'form-control'}
    )

    card_limit = IntegerField(
        'Maximum Cards to Enhance',
        validators=[
            DataRequired(),
            NumberRange(min=1, max=50, message='Can enhance 1-50 cards at a time')
        ],
        default=10,
        render_kw={'class': 'form-control'}
    )

    submit = SubmitField('Enhance Selected Cards', render_kw={'class': 'btn btn-success'})
