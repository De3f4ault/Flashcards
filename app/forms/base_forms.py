from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, IntegerField
from wtforms.validators import DataRequired, Length, NumberRange


class BaseForm(FlaskForm):
    """Base form class with common functionality"""

    def get_errors(self):
        """Get all form errors as a flat list"""
        errors = []
        for field_name, field_errors in self.errors.items():
            for error in field_errors:
                errors.append(f"{field_name.replace('_', ' ').title()}: {error}")
        return errors

    def populate_from_obj(self, obj, exclude=None):
        """Populate form from object, excluding specified fields"""
        exclude = exclude or []
        for field_name, field in self._fields.items():
            if field_name not in exclude and hasattr(obj, field_name):
                field.data = getattr(obj, field_name)


class SearchForm(BaseForm):
    """Generic search form"""
    query = StringField(
        'Search',
        validators=[Length(min=1, max=100)],
        render_kw={'placeholder': 'Search...', 'class': 'form-control'}
    )


class ConfirmationForm(BaseForm):
    """Generic confirmation form for dangerous operations"""
    confirmation = StringField(
        'Type "CONFIRM" to proceed',
        validators=[DataRequired()],
        render_kw={'placeholder': 'CONFIRM', 'class': 'form-control'}
    )

    def validate_confirmation(self, field):
        if field.data != 'CONFIRM':
            raise ValidationError('Please type "CONFIRM" to proceed.')


class PaginationForm(BaseForm):
    """Form for pagination controls"""
    per_page = SelectField(
        'Items per page',
        choices=[(10, '10'), (20, '20'), (50, '50')],
        coerce=int,
        default=20
    )
