from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user
from app.services import DeckService


def deck_owner_required(f):
    """Decorator to ensure current user owns the deck"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        deck_id = kwargs.get('deck_id') or kwargs.get('id')
        if not deck_id:
            abort(400)

        deck = DeckService.get_or_404(deck_id)
        if not DeckService.user_owns_deck(deck, current_user.id):
            flash('You do not have permission to modify this deck.', 'error')
            return redirect(url_for('decks.index'))

        return f(*args, **kwargs)
    return decorated_function


def deck_access_required(f):
    """Decorator to ensure current user can access the deck (owner or public)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        deck_id = kwargs.get('deck_id') or kwargs.get('id')
        if not deck_id:
            abort(400)

        deck = DeckService.get_or_404(deck_id)
        if not DeckService.user_can_access_deck(deck, current_user.id):
            flash('You do not have permission to access this deck.', 'error')
            return redirect(url_for('decks.public'))

        return f(*args, **kwargs)
    return decorated_function


def anonymous_required(f):
    """Decorator to ensure user is not logged in"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.is_authenticated:
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function
