"""
Forms for MC Question Generation
Handles user input for generating and editing MC questions
"""

from flask_wtf import FlaskForm
from wtforms import (
    StringField, TextAreaField, SelectField,
    IntegerField, HiddenField, SubmitField
)
from wtforms.validators import (
    DataRequired, Length, NumberRange,
    Optional, ValidationError
)


class MCGenerationRequestForm(FlaskForm):
    """Form for requesting AI generation of MC questions"""

    topic = StringField(
        'Topic',
        validators=[
            DataRequired(message='Topic is required'),
            Length(min=3, max=200, message='Topic must be 3-200 characters')
        ],
        render_kw={
            'placeholder': 'e.g., Photosynthesis, World War II, Python Functions',
            'class': 'form-control',
            'autofocus': True
        }
    )

    count = IntegerField(
        'Number of Questions',
        validators=[
            DataRequired(message='Number of questions is required'),
            NumberRange(min=1, max=20, message='Must be between 1 and 20 questions')
        ],
        default=10,
        render_kw={
            'class': 'form-control',
            'type': 'number',
            'min': '1',
            'max': '20'
        }
    )

    difficulty = SelectField(
        'Difficulty Level',
        choices=[
            (1, 'Beginner - Basic recall and definitions'),
            (2, 'Easy - Simple application'),
            (3, 'Medium - Understanding and analysis'),
            (4, 'Advanced - Complex application'),
            (5, 'Expert - Synthesis and evaluation')
        ],
        coerce=int,
        default=3,
        render_kw={'class': 'form-select'}
    )

    subject_area = SelectField(
        'Subject Area',
        choices=[
            ('science', 'Science (Biology, Chemistry, Physics)'),
            ('math', 'Mathematics'),
            ('history', 'History'),
            ('language', 'Language Arts'),
            ('social_studies', 'Social Studies'),
            ('computer_science', 'Computer Science'),
            ('general', 'General Knowledge')
        ],
        default='general',
        render_kw={'class': 'form-select'}
    )

    additional_context = TextAreaField(
        'Additional Instructions (Optional)',
        validators=[
            Optional(),
            Length(max=500, message='Additional context must be less than 500 characters')
        ],
        render_kw={
            'placeholder': 'e.g., Focus on the Calvin cycle, Include common student mistakes, Use real-world examples',
            'class': 'form-control',
            'rows': 3
        }
    )

    deck_id = HiddenField('Deck ID', validators=[DataRequired()])

    submit = SubmitField('Generate Questions', render_kw={'class': 'btn btn-primary'})


class MCQuestionEditForm(FlaskForm):
    """Form for editing a single MC question in preview"""

    question_text = TextAreaField(
        'Question',
        validators=[
            DataRequired(message='Question is required'),
            Length(min=10, max=1000, message='Question must be 10-1000 characters')
        ],
        render_kw={
            'class': 'form-control',
            'rows': 3
        }
    )

    choice_a = StringField(
        'Choice A',
        validators=[
            DataRequired(message='Choice A is required'),
            Length(min=1, max=500, message='Choice must be 1-500 characters')
        ],
        render_kw={'class': 'form-control'}
    )

    choice_b = StringField(
        'Choice B',
        validators=[
            DataRequired(message='Choice B is required'),
            Length(min=1, max=500, message='Choice must be 1-500 characters')
        ],
        render_kw={'class': 'form-control'}
    )

    choice_c = StringField(
        'Choice C',
        validators=[
            DataRequired(message='Choice C is required'),
            Length(min=1, max=500, message='Choice must be 1-500 characters')
        ],
        render_kw={'class': 'form-control'}
    )

    choice_d = StringField(
        'Choice D',
        validators=[
            DataRequired(message='Choice D is required'),
            Length(min=1, max=500, message='Choice must be 1-500 characters')
        ],
        render_kw={'class': 'form-control'}
    )

    correct_answer = SelectField(
        'Correct Answer',
        choices=[
            ('A', 'A'),
            ('B', 'B'),
            ('C', 'C'),
            ('D', 'D')
        ],
        validators=[DataRequired(message='Must select correct answer')],
        render_kw={'class': 'form-select'}
    )

    misconception_a = TextAreaField(
        'Why A is wrong (if not correct)',
        validators=[Optional(), Length(max=500)],
        render_kw={'class': 'form-control', 'rows': 2}
    )

    misconception_b = TextAreaField(
        'Why B is wrong (if not correct)',
        validators=[Optional(), Length(max=500)],
        render_kw={'class': 'form-control', 'rows': 2}
    )

    misconception_c = TextAreaField(
        'Why C is wrong (if not correct)',
        validators=[Optional(), Length(max=500)],
        render_kw={'class': 'form-control', 'rows': 2}
    )

    misconception_d = TextAreaField(
        'Why D is wrong (if not correct)',
        validators=[Optional(), Length(max=500)],
        render_kw={'class': 'form-control', 'rows': 2}
    )

    card_id = HiddenField('Card ID')

    submit = SubmitField('Save Changes', render_kw={'class': 'btn btn-success'})

    def validate_choices(self, field):
        """Custom validator to ensure no duplicate choices"""
        choices = [
            self.choice_a.data,
            self.choice_b.data,
            self.choice_c.data,
            self.choice_d.data
        ]

        # Remove None/empty values for comparison
        choices = [c.strip().lower() for c in choices if c and c.strip()]

        if len(choices) != len(set(choices)):
            raise ValidationError('All choices must be different')


class MCManualCreateForm(FlaskForm):
    """Form for manually creating MC questions (fallback if AI fails)"""

    question_text = TextAreaField(
        'Question',
        validators=[
            DataRequired(message='Question is required'),
            Length(min=10, max=1000, message='Question must be 10-1000 characters')
        ],
        render_kw={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Enter your multiple choice question'
        }
    )

    choice_a = StringField(
        'Choice A',
        validators=[
            DataRequired(message='Choice A is required'),
            Length(min=1, max=500)
        ],
        render_kw={'class': 'form-control', 'placeholder': 'First option'}
    )

    choice_b = StringField(
        'Choice B',
        validators=[
            DataRequired(message='Choice B is required'),
            Length(min=1, max=500)
        ],
        render_kw={'class': 'form-control', 'placeholder': 'Second option'}
    )

    choice_c = StringField(
        'Choice C',
        validators=[
            DataRequired(message='Choice C is required'),
            Length(min=1, max=500)
        ],
        render_kw={'class': 'form-control', 'placeholder': 'Third option'}
    )

    choice_d = StringField(
        'Choice D',
        validators=[
            DataRequired(message='Choice D is required'),
            Length(min=1, max=500)
        ],
        render_kw={'class': 'form-control', 'placeholder': 'Fourth option'}
    )

    correct_answer = SelectField(
        'Correct Answer',
        choices=[
            ('A', 'A'),
            ('B', 'B'),
            ('C', 'C'),
            ('D', 'D')
        ],
        validators=[DataRequired()],
        render_kw={'class': 'form-select'}
    )

    difficulty = SelectField(
        'Difficulty',
        choices=[
            (1, 'Beginner'),
            (2, 'Easy'),
            (3, 'Medium'),
            (4, 'Advanced'),
            (5, 'Expert')
        ],
        coerce=int,
        default=3,
        render_kw={'class': 'form-select'}
    )

    misconception_a = TextAreaField(
        'Explanation for A (if wrong)',
        validators=[Optional(), Length(max=500)],
        render_kw={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Why someone might incorrectly choose A'
        }
    )

    misconception_b = TextAreaField(
        'Explanation for B (if wrong)',
        validators=[Optional(), Length(max=500)],
        render_kw={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Why someone might incorrectly choose B'
        }
    )

    misconception_c = TextAreaField(
        'Explanation for C (if wrong)',
        validators=[Optional(), Length(max=500)],
        render_kw={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Why someone might incorrectly choose C'
        }
    )

    misconception_d = TextAreaField(
        'Explanation for D (if wrong)',
        validators=[Optional(), Length(max=500)],
        render_kw={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Why someone might incorrectly choose D'
        }
    )

    concept_tags = StringField(
        'Concept Tags (comma-separated)',
        validators=[Optional(), Length(max=200)],
        render_kw={
            'class': 'form-control',
            'placeholder': 'e.g., photosynthesis, chloroplast, light reactions'
        }
    )

    deck_id = HiddenField('Deck ID', validators=[DataRequired()])

    submit = SubmitField('Create Question', render_kw={'class': 'btn btn-primary'})
