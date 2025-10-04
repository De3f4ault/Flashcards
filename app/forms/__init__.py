from app.forms.auth_forms import (
    LoginForm,
    RegistrationForm,
    ChangePasswordForm,
    ProfileForm
)

from app.forms.deck_forms import (
    DeckForm,
    FlashcardForm,
    QuickFlashcardForm,
    BulkFlashcardForm,
    StudyOptionsForm,
    DeckSearchForm,
    DuplicateDeckForm
)

from app.forms.base_forms import (
    BaseForm,
    SearchForm,
    ConfirmationForm,
    PaginationForm
)

__all__ = [
    # Auth forms
    'LoginForm',
    'RegistrationForm',
    'ChangePasswordForm',
    'ProfileForm',

    # Deck forms
    'DeckForm',
    'FlashcardForm',
    'QuickFlashcardForm',
    'BulkFlashcardForm',
    'StudyOptionsForm',
    'DeckSearchForm',
    'DuplicateDeckForm',

    # Base forms
    'BaseForm',
    'SearchForm',
    'ConfirmationForm',
    'PaginationForm'
]
