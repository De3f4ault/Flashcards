from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from app.forms.base_forms import BaseForm
from app.services import AuthService


class LoginForm(BaseForm):
    """User login form"""
    username_or_email = StringField(
        'Username or Email',
        validators=[DataRequired(), Length(min=3, max=120)],
        render_kw={'placeholder': 'Enter username or email', 'class': 'form-control'}
    )
    password = PasswordField(
        'Password',
        validators=[DataRequired()],
        render_kw={'placeholder': 'Enter password', 'class': 'form-control'}
    )
    remember_me = BooleanField(
        'Remember me',
        render_kw={'class': 'form-check-input'}
    )
    submit = SubmitField(
        'Sign In',
        render_kw={'class': 'btn btn-primary btn-block'}
    )


class RegistrationForm(BaseForm):
    """User registration form"""
    username = StringField(
        'Username',
        validators=[
            DataRequired(),
            Length(min=3, max=80, message='Username must be between 3 and 80 characters')
        ],
        render_kw={'placeholder': 'Choose a username', 'class': 'form-control'}
    )
    email = StringField(
        'Email',
        validators=[
            DataRequired(),
            Email(message='Please enter a valid email address'),
            Length(max=120)
        ],
        render_kw={'placeholder': 'Enter your email', 'class': 'form-control'}
    )
    password = PasswordField(
        'Password',
        validators=[
            DataRequired(),
            Length(min=6, message='Password must be at least 6 characters long')
        ],
        render_kw={'placeholder': 'Create a password', 'class': 'form-control'}
    )
    password2 = PasswordField(
        'Confirm Password',
        validators=[
            DataRequired(),
            EqualTo('password', message='Passwords must match')
        ],
        render_kw={'placeholder': 'Confirm your password', 'class': 'form-control'}
    )
    submit = SubmitField(
        'Create Account',
        render_kw={'class': 'btn btn-success btn-block'}
    )

    def validate_username(self, username):
        """Check if username is already taken"""
        if AuthService.exists(username=username.data):
            raise ValidationError('Username already taken. Please choose a different one.')

    def validate_email(self, email):
        """Check if email is already registered"""
        if AuthService.exists(email=email.data):
            raise ValidationError('Email already registered. Please use a different email.')


class ChangePasswordForm(BaseForm):
    """Change password form"""
    current_password = PasswordField(
        'Current Password',
        validators=[DataRequired()],
        render_kw={'placeholder': 'Enter current password', 'class': 'form-control'}
    )
    new_password = PasswordField(
        'New Password',
        validators=[
            DataRequired(),
            Length(min=6, message='Password must be at least 6 characters long')
        ],
        render_kw={'placeholder': 'Enter new password', 'class': 'form-control'}
    )
    new_password2 = PasswordField(
        'Confirm New Password',
        validators=[
            DataRequired(),
            EqualTo('new_password', message='Passwords must match')
        ],
        render_kw={'placeholder': 'Confirm new password', 'class': 'form-control'}
    )
    submit = SubmitField(
        'Change Password',
        render_kw={'class': 'btn btn-primary'}
    )


class ProfileForm(BaseForm):
    """User profile edit form"""
    username = StringField(
        'Username',
        validators=[
            DataRequired(),
            Length(min=3, max=80, message='Username must be between 3 and 80 characters')
        ],
        render_kw={'class': 'form-control'}
    )
    email = StringField(
        'Email',
        validators=[
            DataRequired(),
            Email(message='Please enter a valid email address'),
            Length(max=120)
        ],
        render_kw={'class': 'form-control'}
    )
    submit = SubmitField(
        'Update Profile',
        render_kw={'class': 'btn btn-primary'}
    )

    def __init__(self, original_username=None, original_email=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_username = original_username
        self.original_email = original_email

    def validate_username(self, username):
        """Check if username is already taken (excluding current user)"""
        if username.data != self.original_username:
            if AuthService.exists(username=username.data):
                raise ValidationError('Username already taken. Please choose a different one.')

    def validate_email(self, email):
        """Check if email is already registered (excluding current user)"""
        if email.data != self.original_email:
            if AuthService.exists(email=email.data):
                raise ValidationError('Email already registered. Please use a different email.')
