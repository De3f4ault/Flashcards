"""
Forms for MC Study Sessions
Handles user input during study sessions
"""

from flask_wtf import FlaskForm
from wtforms import (
    StringField, SelectField, HiddenField,
    SubmitField, RadioField, IntegerField
)
from wtforms.validators import (
    DataRequired, Optional, Length, NumberRange
)


class MCSessionStartForm(FlaskForm):
    """Form for starting an MC study session"""

    session_title = StringField(
        'Session Title (Optional)',
        validators=[
            Optional(),
            Length(max=200, message='Title must be less than 200 characters')
        ],
        render_kw={
            'placeholder': 'e.g., Midterm prep, Chapter 5 review',
            'class': 'form-control'
        }
    )

    deck_id = HiddenField('Deck ID', validators=[DataRequired()])

    submit = SubmitField('Start Studying', render_kw={'class': 'btn btn-primary btn-lg'})


class MCAnswerSubmitForm(FlaskForm):
    """Form for submitting an answer to a single MC question"""

    selected_choice = RadioField(
        'Your Answer',
        choices=[
            ('A', 'A'),
            ('B', 'B'),
            ('C', 'C'),
            ('D', 'D')
        ],
        validators=[DataRequired(message='Please select an answer')],
        render_kw={'class': 'form-check-input'}
    )

    confidence_rating = SelectField(
        'Confidence Level',
        choices=[
            (1, '1 - Guessing'),
            (2, '2 - Uncertain'),
            (3, '3 - Moderate'),
            (4, '4 - Confident'),
            (5, '5 - Certain')
        ],
        coerce=int,
        validators=[DataRequired(message='Please rate your confidence')],
        render_kw={'class': 'form-select'}
    )

    time_spent = HiddenField('Time Spent', default=0)
    card_id = HiddenField('Card ID', validators=[DataRequired()])
    session_id = HiddenField('Session ID', validators=[DataRequired()])

    submit = SubmitField('Submit Answer', render_kw={'class': 'btn btn-primary'})


class MCFeedbackContinueForm(FlaskForm):
    """Simple form to continue to next question after feedback"""

    session_id = HiddenField('Session ID', validators=[DataRequired()])

    submit = SubmitField('Next Question', render_kw={'class': 'btn btn-success btn-lg'})


class MCSessionFilterForm(FlaskForm):
    """Form for filtering which cards to study in a session"""

    filter_by = SelectField(
        'Study Mode',
        choices=[
            ('all', 'All Questions'),
            ('new', 'New Questions Only'),
            ('incorrect', 'Previously Incorrect'),
            ('random', 'Random Selection')
        ],
        default='all',
        render_kw={'class': 'form-select'}
    )

    max_questions = IntegerField(
        'Maximum Questions',
        validators=[
            Optional(),
            NumberRange(min=1, max=50, message='Must be between 1 and 50')
        ],
        render_kw={
            'class': 'form-control',
            'placeholder': 'Leave blank for all'
        }
    )

    shuffle = SelectField(
        'Question Order',
        choices=[
            ('yes', 'Shuffle (Random Order)'),
            ('no', 'Original Order')
        ],
        default='yes',
        render_kw={'class': 'form-select'}
    )

    submit = SubmitField('Apply Filters', render_kw={'class': 'btn btn-secondary'})
