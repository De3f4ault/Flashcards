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

from app.forms.mc_generation_forms import (
    MCGenerationRequestForm,
    MCQuestionEditForm,
    MCManualCreateForm
)

from app.forms.mc_study_forms import (
    MCSessionStartForm,
    MCAnswerSubmitForm,
    MCFeedbackContinueForm,
    MCSessionFilterForm
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
    'PaginationForm',

    # MC Generation forms
    'MCGenerationRequestForm',
    'MCQuestionEditForm',
    'MCManualCreateForm',

    # MC Study forms
    'MCSessionStartForm',
    'MCAnswerSubmitForm',
    'MCFeedbackContinueForm',
    'MCSessionFilterForm'
]
