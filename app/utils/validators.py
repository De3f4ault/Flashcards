import re
from wtforms.validators import ValidationError


class UniqueUsername:
    """Validator to check if username is unique"""
    def __init__(self, message=None):
        if not message:
            message = 'Username already exists. Please choose a different one.'
        self.message = message

    def __call__(self, form, field):
        from app.services import AuthService
        if AuthService.exists(username=field.data):
            raise ValidationError(self.message)


class UniqueEmail:
    """Validator to check if email is unique"""
    def __init__(self, message=None):
        if not message:
            message = 'Email already registered. Please use a different email.'
        self.message = message

    def __call__(self, form, field):
        from app.services import AuthService
        if AuthService.exists(email=field.data):
            raise ValidationError(self.message)


class StrongPassword:
    """Validator for strong password requirements"""
    def __init__(self, min_length=8, require_uppercase=True, require_lowercase=True,
                 require_numbers=True, require_symbols=False, message=None):
        self.min_length = min_length
        self.require_uppercase = require_uppercase
        self.require_lowercase = require_lowercase
        self.require_numbers = require_numbers
        self.require_symbols = require_symbols
        self.message = message or self._build_message()

    def _build_message(self):
        requirements = [f"at least {self.min_length} characters"]
        if self.require_uppercase:
            requirements.append("one uppercase letter")
        if self.require_lowercase:
            requirements.append("one lowercase letter")
        if self.require_numbers:
            requirements.append("one number")
        if self.require_symbols:
            requirements.append("one special character")

        return f"Password must contain {', '.join(requirements)}."

    def __call__(self, form, field):
        password = field.data

        if len(password) < self.min_length:
            raise ValidationError(self.message)

        if self.require_uppercase and not re.search(r'[A-Z]', password):
            raise ValidationError(self.message)

        if self.require_lowercase and not re.search(r'[a-z]', password):
            raise ValidationError(self.message)

        if self.require_numbers and not re.search(r'[0-9]', password):
            raise ValidationError(self.message)

        if self.require_symbols and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValidationError(self.message)


class NoHtml:
    """Validator to prevent HTML tags in input"""
    def __init__(self, message=None):
        if not message:
            message = 'HTML tags are not allowed.'
        self.message = message

    def __call__(self, form, field):
        if field.data and re.search(r'<[^>]*>', field.data):
            raise ValidationError(self.message)


class CleanText:
    """Validator to ensure text doesn't contain excessive whitespace or special chars"""
    def __init__(self, max_consecutive_spaces=2, message=None):
        self.max_consecutive_spaces = max_consecutive_spaces
        if not message:
            message = f'Text cannot contain more than {max_consecutive_spaces} consecutive spaces.'
        self.message = message

    def __call__(self, form, field):
        if field.data:
            # Check for excessive consecutive spaces
            if re.search(f' {{{self.max_consecutive_spaces + 1},}}', field.data):
                raise ValidationError(self.message)


class ValidFlashcardText:
    """Validator specifically for flashcard text content"""
    def __init__(self, message=None):
        if not message:
            message = 'Flashcard text contains invalid content.'
        self.message = message

    def __call__(self, form, field):
        if field.data:
            text = field.data.strip()

            # Check if empty after stripping
            if not text:
                raise ValidationError('Flashcard text cannot be empty or contain only spaces.')

            # Check for common issues
            if text.count('|') > 3:  # Probably trying to use bulk format
                raise ValidationError('Use the bulk import feature for multiple cards.')

            # Check for extremely repetitive content
            if len(set(text.replace(' ', '').lower())) < 3 and len(text) > 10:
                raise ValidationError('Text appears to be repetitive or invalid.')


class BulkCardsFormat:
    """Validator for bulk flashcards format"""
    def __init__(self, min_cards=1, max_cards=100, message=None):
        self.min_cards = min_cards
        self.max_cards = max_cards
        self.message = message or f'Must contain between {min_cards} and {max_cards} valid cards.'

    def __call__(self, form, field):
        if not field.data:
            raise ValidationError(self.message)

        lines = field.data.strip().split('\n')
        valid_cards = 0

        for line in lines:
            line = line.strip()
            if line and '|' in line:
                parts = line.split('|', 1)
                if len(parts) == 2 and parts[0].strip() and parts[1].strip():
                    valid_cards += 1

        if valid_cards < self.min_cards or valid_cards > self.max_cards:
            raise ValidationError(self.message)
