from flask_login import login_user, logout_user
from app.models import User
from app.services.base_service import BaseService


class AuthService(BaseService):
    model = User

    @classmethod
    def register_user(cls, username, email, password):
        """Register a new user"""
        # Check if user already exists
        if cls.exists(username=username):
            return None, "Username already exists"

        if cls.exists(email=email):
            return None, "Email already registered"

        # Create new user
        user = User(username=username, email=email)
        user.set_password(password)
        user.save()

        return user, "Registration successful"

    @classmethod
    def authenticate_user(cls, username_or_email, password):
        """Authenticate user with username/email and password"""
        # Try to find user by username or email
        user = User.query.filter(
            (User.username == username_or_email) |
            (User.email == username_or_email)
        ).first()

        if user and user.check_password(password):
            return user, "Login successful"

        return None, "Invalid credentials"

    @classmethod
    def login_user_session(cls, user, remember=False):
        """Log user into session"""
        return login_user(user, remember=remember)

    @classmethod
    def logout_user_session(cls):
        """Log user out of session"""
        logout_user()

    @classmethod
    def get_user_by_username(cls, username):
        """Get user by username"""
        return User.query.filter_by(username=username).first()

    @classmethod
    def get_user_by_email(cls, email):
        """Get user by email"""
        return User.query.filter_by(email=email).first()

    @classmethod
    def update_password(cls, user, new_password):
        """Update user password"""
        user.set_password(new_password)
        return user.save()

    @classmethod
    def deactivate_user(cls, user):
        """Deactivate user account"""
        user.is_active = False
        return user.save()

    @classmethod
    def activate_user(cls, user):
        """Activate user account"""
        user.is_active = True
        return user.save()
