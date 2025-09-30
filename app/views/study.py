from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, session
from flask_login import login_required, current_user
from app.forms import StudyOptionsForm
from app.services import DeckService, StudyService
from app.models import Deck

study_bp = Blueprint('study', __name__)


@study_bp.route('/<int:deck_id>', methods=['GET', 'POST'])
@login_required
def start(deck_id):
    """Study session start page with options"""
    # Secure lookup: verify deck ownership or public access
    deck = Deck.query.get_or_404(deck_id)

    # Check access permissions
    if not DeckService.user_can_access_deck(deck, current_user.id):
        flash('You do not have permission to study this deck.', 'error')
        return redirect(url_for('decks.index'))

    # Check if deck has cards
    if not deck.can_be_studied():
        flash('This deck has no cards to study.', 'warning')
        return redirect(url_for('decks.view', id=deck_id))

    form = StudyOptionsForm()
    stats = StudyService.get_study_statistics(deck_id)

    if form.validate_on_submit():
        # Store study session settings
        session['study_settings'] = {
            'deck_id': deck_id,
            'study_mode': form.study_mode.data,
            'card_limit': form.card_limit.data if form.card_limit.data > 0 else None,
            'interaction_mode': form.interaction_mode.data if hasattr(form, 'interaction_mode') else 'flip'
        }
        return redirect(url_for('study.study_session', deck_id=deck_id))

    return render_template(
        'study/start.html',
        title=f'Study {deck.name}',
        deck=deck,
        form=form,
        stats=stats
    )


@study_bp.route('/<int:deck_id>/session')
@login_required
def study_session(deck_id):
    """Active study session"""
    # Secure lookup: verify deck ownership or public access
    deck = Deck.query.get_or_404(deck_id)

    # Check access permissions
    if not DeckService.user_can_access_deck(deck, current_user.id):
        flash('You do not have permission to study this deck.', 'error')
        return redirect(url_for('decks.index'))

    # Get study settings from session or use defaults
    study_settings = session.get('study_settings', {})
    if study_settings.get('deck_id') != deck_id:
        # Reset session if studying different deck
        study_settings = {
            'deck_id': deck_id,
            'study_mode': 'random',
            'card_limit': None,
            'interaction_mode': 'flip'
        }
        session['study_settings'] = study_settings

    # Get cards for study
    cards = StudyService.get_study_cards(
        deck_id=deck_id,
        study_mode=study_settings['study_mode'],
        limit=study_settings['card_limit']
    )

    if not cards:
        flash('No cards available for study.', 'warning')
        return redirect(url_for('decks.view', id=deck_id))

    # Initialize or get current session progress
    if 'current_session' not in session:
        session['current_session'] = {
            'deck_id': deck_id,
            'card_ids': [card.id for card in cards],
            'current_index': 0,
            'correct_count': 0,
            'total_studied': 0
        }

    current_session = session['current_session']

    # Check if session is complete
    if current_session['current_index'] >= len(current_session['card_ids']):
        return redirect(url_for('study.complete', deck_id=deck_id))

    # Get current card
    current_card_id = current_session['card_ids'][current_session['current_index']]
    current_card = StudyService.get_by_id(current_card_id)

    if not current_card:
        flash('Error loading flashcard.', 'error')
        return redirect(url_for('decks.view', id=deck_id))

    # Progress info
    progress = {
        'current': current_session['current_index'] + 1,
        'total': len(current_session['card_ids']),
        'percentage': round(((current_session['current_index'] + 1) / len(current_session['card_ids'])) * 100)
    }

    return render_template(
        'study/sessions.html',
        title=f'Studying {deck.name}',
        deck=deck,
        card=current_card,
        progress=progress,
        session_stats=current_session,
        preferred_mode=study_settings.get('interaction_mode', 'flip')
    )


@study_bp.route('/<int:deck_id>/answer', methods=['POST'])
@login_required
def answer(deck_id):
    """Process study answer"""
    # Secure lookup: verify deck ownership or public access
    deck = Deck.query.get_or_404(deck_id)

    # Check access permissions
    if not DeckService.user_can_access_deck(deck, current_user.id):
        if request.is_json:
            return jsonify({'success': False, 'error': 'Permission denied'}), 403
        flash('You do not have permission to study this deck.', 'error')
        return redirect(url_for('decks.index'))

    if 'current_session' not in session:
        flash('Study session expired. Please start a new session.', 'warning')
        return redirect(url_for('study.start', deck_id=deck_id))

    current_session = session['current_session']

    # Validate session
    if current_session['deck_id'] != deck_id:
        flash('Invalid study session.', 'error')
        return redirect(url_for('study.start', deck_id=deck_id))

    # Get answer result
    correct = request.json.get('correct', False) if request.is_json else request.form.get('correct') == 'true'

    # Get current card and record result
    current_card_id = current_session['card_ids'][current_session['current_index']]
    StudyService.record_study_result(current_card_id, correct)

    # Update session stats
    current_session['total_studied'] += 1
    if correct:
        current_session['correct_count'] += 1

    # Move to next card
    current_session['current_index'] += 1
    session['current_session'] = current_session

    if request.is_json:
        # Return JSON response for AJAX requests
        is_complete = current_session['current_index'] >= len(current_session['card_ids'])
        return jsonify({
            'success': True,
            'is_complete': is_complete,
            'next_url': url_for('study.complete', deck_id=deck_id) if is_complete else url_for('study.study_session', deck_id=deck_id)
        })
    else:
        # Regular form submission
        return redirect(url_for('study.study_session', deck_id=deck_id))


@study_bp.route('/<int:deck_id>/complete')
@login_required
def complete(deck_id):
    """Study session completion page"""
    # Secure lookup: verify deck ownership or public access
    deck = Deck.query.get_or_404(deck_id)

    # Check access permissions
    if not DeckService.user_can_access_deck(deck, current_user.id):
        flash('You do not have permission to view this page.', 'error')
        return redirect(url_for('decks.index'))

    # Get session results
    current_session = session.get('current_session', {})

    if not current_session or current_session.get('deck_id') != deck_id:
        flash('No study session found.', 'warning')
        return redirect(url_for('decks.view', id=deck_id))

    # Calculate results
    results = {
        'total_studied': current_session['total_studied'],
        'correct_count': current_session['correct_count'],
        'incorrect_count': current_session['total_studied'] - current_session['correct_count'],
        'accuracy': round((current_session['correct_count'] / current_session['total_studied']) * 100, 1) if current_session['total_studied'] > 0 else 0
    }

    # Clear session
    session.pop('current_session', None)
    session.pop('study_settings', None)

    return render_template(
        'study/complete.html',
        title='Study Complete',
        deck=deck,
        results=results
    )


@study_bp.route('/<int:deck_id>/review')
@login_required
def review(deck_id):
    """Review cards that need practice"""
    # Secure lookup: verify deck ownership or public access
    deck = Deck.query.get_or_404(deck_id)

    # Check access permissions
    if not DeckService.user_can_access_deck(deck, current_user.id):
        flash('You do not have permission to review this deck.', 'error')
        return redirect(url_for('decks.index'))

    review_cards = StudyService.get_cards_needing_review(deck_id)

    return render_template(
        'study/review.html',
        title=f'Review {deck.name}',
        deck=deck,
        cards=review_cards
    )


@study_bp.route('/<int:deck_id>/statistics')
@login_required
def statistics(deck_id):
    """Detailed study statistics"""
    # Secure lookup: verify deck ownership or public access
    deck = Deck.query.get_or_404(deck_id)

    # Check access permissions
    if not DeckService.user_can_access_deck(deck, current_user.id):
        flash('You do not have permission to view these statistics.', 'error')
        return redirect(url_for('decks.index'))

    stats = StudyService.get_study_statistics(deck_id)
    deck_stats = DeckService.get_deck_statistics(deck)

    # Get cards with detailed stats
    cards = StudyService.get_deck_cards(deck_id)
    cards_with_stats = []
    for card in cards:
        cards_with_stats.append({
            'card': card,
            'accuracy': card.get_accuracy(),
            'needs_review': card.get_accuracy() < 70 or card.difficulty >= 4
        })

    # Sort by accuracy (worst first)
    cards_with_stats.sort(key=lambda x: x['accuracy'])

    return render_template(
        'study/statistics.html',
        title=f'{deck.name} - Statistics',
        deck=deck,
        stats=stats,
        deck_stats=deck_stats,
        cards_with_stats=cards_with_stats
    )


@study_bp.route('/reset-session', methods=['POST'])
@login_required
def reset_session():
    """Reset current study session"""
    session.pop('current_session', None)
    session.pop('study_settings', None)

    deck_id = request.form.get('deck_id')
    if deck_id:
        flash('Study session reset.', 'info')
        return redirect(url_for('study.start', deck_id=deck_id))

    return redirect(url_for('decks.index'))
