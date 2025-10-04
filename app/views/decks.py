from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, jsonify
from flask_login import login_required, current_user
from app.forms import (
    DeckForm, FlashcardForm, QuickFlashcardForm, BulkFlashcardForm,
    DeckSearchForm, DuplicateDeckForm, ConfirmationForm
)
from app.services import DeckService, StudyService
from app.config import Config
from app.models import Deck, Flashcard
from datetime import datetime, timedelta

decks_bp = Blueprint('decks', __name__)


# ============================================================================
# ORIGINAL ROUTES (Preserved)
# ============================================================================

@decks_bp.route('/')
@login_required
def index():
    """List user's decks"""
    page = request.args.get('page', 1, type=int)
    search_form = DeckSearchForm()

    # Handle search
    query = request.args.get('query', '')
    if query:
        decks = DeckService.search_decks(
            query=query,
            user_id=current_user.id,
            include_public=True
        )
        pagination = None
    else:
        pagination = DeckService.get_user_decks(
            user_id=current_user.id,
            page=page,
            per_page=Config.DECKS_PER_PAGE
        )
        decks = pagination.items

    return render_template(
        'decks/index.html',
        title='My Decks',
        decks=decks,
        pagination=pagination,
        search_form=search_form,
        query=query
    )


@decks_bp.route('/public')
def public():
    """Browse public decks"""
    page = request.args.get('page', 1, type=int)
    search_form = DeckSearchForm()

    # Handle search
    query = request.args.get('query', '')
    if query:
        decks = DeckService.search_decks(query=query, include_public=True)
        pagination = None
    else:
        pagination = DeckService.get_public_decks(
            page=page,
            per_page=Config.DECKS_PER_PAGE
        )
        decks = pagination.items

    return render_template(
        'decks/public.html',
        title='Public Decks',
        decks=decks,
        pagination=pagination,
        search_form=search_form,
        query=query
    )


@decks_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create new deck"""
    form = DeckForm()

    if form.validate_on_submit():
        deck = DeckService.create_deck(
            user_id=current_user.id,
            name=form.name.data,
            description=form.description.data,
            is_public=form.is_public.data
        )
        flash(f'Deck "{deck.name}" created successfully!', 'success')
        return redirect(url_for('decks.view', id=deck.id))

    return render_template('decks/create.html', title='Create Deck', form=form)


@decks_bp.route('/<int:id>', methods=['GET', 'POST'])
def view(id):
    """View deck details"""
    deck = DeckService.get_or_404(id)

    # Check access permissions
    if not DeckService.user_can_access_deck(deck, current_user.id if current_user.is_authenticated else None):
        abort(403)

    # Get comprehensive statistics
    stats = DeckService.get_deck_card_statistics(id)
    difficulty_dist = DeckService.get_deck_difficulty_distribution(id)
    study_stats = StudyService.get_study_statistics(deck.id)

    # Quick add form for owners
    quick_form = None
    if current_user.is_authenticated and DeckService.user_owns_deck(deck, current_user.id):
        quick_form = QuickFlashcardForm()

        if quick_form.validate_on_submit():
            StudyService.create_flashcard(
                deck_id=deck.id,
                front_text=quick_form.front_text.data,
                back_text=quick_form.back_text.data
            )
            flash('Card added successfully!', 'success')
            return redirect(url_for('decks.view', id=id))

    return render_template(
        'decks/view.html',
        title=deck.name,
        deck=deck,
        stats=stats,
        difficulty_dist=difficulty_dist,
        study_stats=study_stats,
        quick_form=quick_form
    )


@decks_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    """Edit deck"""
    # Secure lookup: only get deck if it belongs to current user
    deck = Deck.query.filter_by(id=id, user_id=current_user.id).first_or_404()

    form = DeckForm()

    if form.validate_on_submit():
        DeckService.update_deck(
            deck,
            name=form.name.data,
            description=form.description.data,
            is_public=form.is_public.data
        )
        flash(f'Deck "{deck.name}" updated successfully!', 'success')
        return redirect(url_for('decks.view', id=deck.id))

    elif request.method == 'GET':
        # Pre-populate form
        form.name.data = deck.name
        form.description.data = deck.description
        form.is_public.data = deck.is_public

    return render_template('decks/edit.html', title='Edit Deck', deck=deck, form=form)


@decks_bp.route('/<int:id>/delete', methods=['GET', 'POST'])
@login_required
def delete(id):
    """Delete deck"""
    # Secure lookup: only get deck if it belongs to current user
    deck = Deck.query.filter_by(id=id, user_id=current_user.id).first_or_404()

    form = ConfirmationForm()

    if form.validate_on_submit():
        deck_name = deck.name
        DeckService.delete(deck)
        flash(f'Deck "{deck_name}" has been deleted.', 'success')
        return redirect(url_for('decks.index'))

    return render_template('decks/delete.html', title='Delete Deck', deck=deck, form=form)


@decks_bp.route('/<int:id>/duplicate', methods=['GET', 'POST'])
@login_required
def duplicate(id):
    """Duplicate/copy a deck"""
    original_deck = DeckService.get_or_404(id)

    # Check access permissions
    if not DeckService.user_can_access_deck(original_deck, current_user.id):
        abort(403)

    form = DuplicateDeckForm()

    if form.validate_on_submit():
        new_deck = DeckService.duplicate_deck(
            original_deck=original_deck,
            new_user_id=current_user.id,
            new_name=form.name.data
        )
        flash(f'Deck copied as "{new_deck.name}"!', 'success')
        return redirect(url_for('decks.view', id=new_deck.id))

    elif request.method == 'GET':
        form.name.data = f"Copy of {original_deck.name}"

    return render_template(
        'decks/duplicate.html',
        title='Copy Deck',
        original_deck=original_deck,
        form=form
    )


# ============================================================================
# ENHANCED: CARDS ROUTE WITH SEARCH & FILTER
# ============================================================================

@decks_bp.route('/<int:deck_id>/cards')
@login_required
def cards(deck_id):
    """List all cards in a deck with search and filter"""
    # Secure lookup: only get deck if it belongs to current user
    deck = Deck.query.filter_by(id=deck_id, user_id=current_user.id).first_or_404()

    # Get filter parameters
    page = request.args.get('page', 1, type=int)
    query = request.args.get('query', '').strip()
    learning_state = request.args.get('learning_state', '').strip()
    difficulty = request.args.get('difficulty', '').strip()
    sort_by = request.args.get('sort_by', 'created_desc')

    # Date filters
    date_from_str = request.args.get('date_from', '')
    date_to_str = request.args.get('date_to', '')

    date_from = None
    date_to = None

    if date_from_str:
        try:
            date_from = datetime.strptime(date_from_str, '%Y-%m-%d')
        except ValueError:
            pass

    if date_to_str:
        try:
            date_to = datetime.strptime(date_to_str, '%Y-%m-%d')
            # Set to end of day
            date_to = date_to.replace(hour=23, minute=59, second=59)
        except ValueError:
            pass

    # Get filtered and paginated cards
    pagination = DeckService.search_deck_cards(
        deck_id=deck_id,
        query=query if query else None,
        learning_state=learning_state if learning_state else None,
        difficulty=difficulty if difficulty else None,
        sort_by=sort_by,
        date_from=date_from,
        date_to=date_to,
        page=page,
        per_page=Config.CARDS_PER_PAGE
    )

    cards_page = pagination.items if pagination else []

    # Get deck statistics for sidebar
    deck_stats = DeckService.get_deck_card_statistics(deck_id)
    difficulty_dist = DeckService.get_deck_difficulty_distribution(deck_id)

    # Build filter summary for display
    active_filters = []
    if query:
        active_filters.append(f"Search: '{query}'")
    if learning_state:
        active_filters.append(f"State: {learning_state.title()}")
    if difficulty:
        active_filters.append(f"Difficulty: {difficulty.title()}")
    if date_from:
        active_filters.append(f"From: {date_from.strftime('%Y-%m-%d')}")
    if date_to:
        active_filters.append(f"To: {date_to.strftime('%Y-%m-%d')}")

    return render_template(
        'decks/cards.html',
        title=f'{deck.name} - Cards',
        deck=deck,
        cards=cards_page,
        pagination=pagination,
        deck_stats=deck_stats,
        difficulty_dist=difficulty_dist,
        # Filter values for form
        query=query,
        learning_state=learning_state,
        difficulty=difficulty,
        sort_by=sort_by,
        date_from=date_from_str,
        date_to=date_to_str,
        active_filters=active_filters
    )


# ============================================================================
# NEW: SEARCH & FILTER API ENDPOINTS
# ============================================================================

@decks_bp.route('/<int:deck_id>/cards/search/api')
@login_required
def search_cards_api(deck_id):
    """API endpoint for card search (AJAX/JSON response)"""
    # Secure lookup
    deck = Deck.query.filter_by(id=deck_id, user_id=current_user.id).first_or_404()

    query = request.args.get('q', '').strip()

    if not query or len(query) < 2:
        return jsonify({'results': []})

    # Quick search
    results = DeckService.quick_search_cards(deck_id, query)

    return jsonify({
        'results': [
            {
                'id': card_id,
                'front': front_text
            }
            for card_id, front_text in results
        ]
    })


@decks_bp.route('/<int:deck_id>/statistics/api')
@login_required
def deck_statistics_api(deck_id):
    """API endpoint for deck statistics"""
    # Secure lookup
    deck = Deck.query.filter_by(id=deck_id, user_id=current_user.id).first_or_404()

    stats = DeckService.get_advanced_deck_stats(deck_id)

    if not stats:
        return jsonify({'error': 'Statistics not available'}), 404

    return jsonify(stats)


@decks_bp.route('/<int:deck_id>/cards/filter/api')
@login_required
def filter_cards_api(deck_id):
    """API endpoint for filtered cards list"""
    # Secure lookup
    deck = Deck.query.filter_by(id=deck_id, user_id=current_user.id).first_or_404()

    filters = {
        'query': request.args.get('query'),
        'learning_state': request.args.get('learning_state'),
        'difficulty': request.args.get('difficulty'),
        'sort_by': request.args.get('sort_by', 'created_desc')
    }

    cards = DeckService.get_filtered_cards(deck_id, filters)

    return jsonify({
        'count': len(cards),
        'cards': [
            {
                'id': card.id,
                'front': card.front,
                'back': card.back,
                'learning_state': card.learning_state,
                'ease_factor': card.ease_factor,
                'times_studied': card.times_studied,
                'is_due': card.is_due_for_review()
            }
            for card in cards[:50]  # Limit to 50 for performance
        ]
    })


@decks_bp.route('/<int:deck_id>/cards/by-state/<state>')
@login_required
def cards_by_state(deck_id, state):
    """View cards filtered by learning state"""
    # Secure lookup
    deck = Deck.query.filter_by(id=deck_id, user_id=current_user.id).first_or_404()

    valid_states = ['new', 'learning', 'review', 'mastered']
    if state not in valid_states:
        abort(400)

    # Redirect to cards view with filter
    return redirect(url_for('decks.cards', deck_id=deck_id, learning_state=state))


@decks_bp.route('/<int:deck_id>/export')
@login_required
def export_deck(deck_id):
    """Export deck data as JSON"""
    # Secure lookup
    deck = Deck.query.filter_by(id=deck_id, user_id=current_user.id).first_or_404()

    include_stats = request.args.get('stats', 'false').lower() == 'true'

    export_data = DeckService.export_deck_data(deck_id, include_stats=include_stats)

    if not export_data:
        abort(404)

    return jsonify(export_data)


# ============================================================================
# ORIGINAL CARD CRUD ROUTES (Preserved)
# ============================================================================

@decks_bp.route('/<int:deck_id>/cards/create', methods=['GET', 'POST'])
@login_required
def create_card(deck_id):
    """Create new flashcard"""
    # Secure lookup: only get deck if it belongs to current user
    deck = Deck.query.filter_by(id=deck_id, user_id=current_user.id).first_or_404()

    form = FlashcardForm()

    if form.validate_on_submit():
        card = StudyService.create_flashcard(
            deck_id=deck.id,
            front_text=form.front_text.data,
            back_text=form.back_text.data
        )
        flash('Flashcard created successfully!', 'success')
        return redirect(url_for('decks.view', id=deck.id))

    return render_template(
        'decks/create_card.html',
        title='Create Flashcard',
        deck=deck,
        form=form
    )


@decks_bp.route('/<int:deck_id>/cards/bulk', methods=['GET', 'POST'])
@login_required
def bulk_create_cards(deck_id):
    """Bulk create flashcards"""
    # Secure lookup: only get deck if it belongs to current user
    deck = Deck.query.filter_by(id=deck_id, user_id=current_user.id).first_or_404()

    form = BulkFlashcardForm()

    if form.validate_on_submit():
        cards_data = form.parse_cards()
        if cards_data:
            created_cards = StudyService.bulk_create_flashcards(deck.id, cards_data)
            flash(f'{len(created_cards)} flashcards created successfully!', 'success')
            return redirect(url_for('decks.view', id=deck.id))
        else:
            flash('No valid cards found. Please check the format.', 'warning')

    return render_template(
        'decks/bulk_create_cards.html',
        title='Bulk Add Cards',
        deck=deck,
        form=form
    )


@decks_bp.route('/<int:deck_id>/cards/<int:card_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_card(deck_id, card_id):
    """Edit flashcard"""
    # Secure lookup: first verify deck ownership
    deck = Deck.query.filter_by(id=deck_id, user_id=current_user.id).first_or_404()

    # Then verify card belongs to this deck
    card = Flashcard.query.filter_by(id=card_id, deck_id=deck.id).first_or_404()

    form = FlashcardForm()

    if form.validate_on_submit():
        StudyService.update_flashcard(
            card,
            front_text=form.front_text.data,
            back_text=form.back_text.data
        )
        flash('Flashcard updated successfully!', 'success')
        return redirect(url_for('decks.view', id=deck.id))

    elif request.method == 'GET':
        form.front_text.data = card.front
        form.back_text.data = card.back

    return render_template(
        'decks/edit_card.html',
        title='Edit Flashcard',
        deck=deck,
        card=card,
        form=form
    )


@decks_bp.route('/<int:deck_id>/cards/<int:card_id>/delete', methods=['POST', 'GET'])
@login_required
def delete_card(deck_id, card_id):
    """Delete flashcard"""
    # Secure lookup: first verify deck ownership
    deck = Deck.query.filter_by(id=deck_id, user_id=current_user.id).first_or_404()

    # Then verify card belongs to this deck
    card = Flashcard.query.filter_by(id=card_id, deck_id=deck.id).first_or_404()

    if request.method == 'POST':
        StudyService.delete(card)
        flash('Flashcard deleted successfully!', 'success')
        return redirect(url_for('decks.view', id=deck.id))

    # Optional: confirmation page for GET
    return render_template('decks/delete_card.html', title='Delete Card', deck=deck, card=card)
