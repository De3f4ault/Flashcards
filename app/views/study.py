from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, session
from flask_login import login_required, current_user
from app.forms import StudyOptionsForm
from app.services import DeckService, StudyService
from app.models import Deck

study_bp = Blueprint('study', __name__)


@study_bp.route('/<int:deck_id>', methods=['GET', 'POST'])
@login_required
def start(deck_id):
    """Study session start page with SM-2 options"""
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

    # Get due cards count for SM-2
    due_cards = StudyService.get_due_cards(deck_id)
    due_cards_count = len(due_cards)

    # Get upcoming review forecast
    upcoming_reviews = StudyService.get_upcoming_reviews(deck_id, days=7)

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
        stats=stats,
        due_cards_count=due_cards_count,
        upcoming_reviews=upcoming_reviews
    )


@study_bp.route('/<int:deck_id>/session')
@login_required
def study_session(deck_id):
    """Active study session with SM-2 spaced repetition"""
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
            'study_mode': 'sm2',  # Default to spaced repetition
            'card_limit': None,
            'interaction_mode': 'flip'
        }
        session['study_settings'] = study_settings

    # Get cards for study using SM-2 or selected mode
    cards = StudyService.get_study_cards(
        deck_id=deck_id,
        study_mode=study_settings.get('study_mode', 'sm2'),
        limit=study_settings['card_limit']
    )

    if not cards:
        flash('No cards due for review! Great work! 🎉', 'success')
        return redirect(url_for('decks.view', id=deck_id))

    # Initialize or get current session progress
    if 'current_session' not in session or session['current_session'].get('deck_id') != deck_id:
        session['current_session'] = {
            'deck_id': deck_id,
            'card_ids': [card.id for card in cards],
            'current_index': 0,
            'correct_count': 0,
            'total_studied': 0,
            'quality_ratings': []  # Track quality ratings for SM-2 statistics
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
    """Process study answer with SM-2 algorithm"""
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

    # Get answer result and quality/confidence
    if request.is_json:
        data = request.json
        correct = data.get('correct', False)
        confidence = data.get('confidence', 'medium')  # 'low', 'medium', 'high'
        quality = data.get('quality')  # Optional: direct quality rating (0-5)
    else:
        correct = request.form.get('correct') == 'true'
        confidence = request.form.get('confidence', 'medium')
        quality = request.form.get('quality')

    # Get current card
    current_card_id = current_session['card_ids'][current_session['current_index']]
    current_card = StudyService.get_by_id(current_card_id)

    if not current_card:
        if request.is_json:
            return jsonify({'success': False, 'error': 'Card not found'}), 404
        flash('Card not found.', 'error')
        return redirect(url_for('study.start', deck_id=deck_id))

    # Record result using SM-2 algorithm
    if quality is not None:
        # Direct quality rating provided (0-5)
        result = StudyService.record_sm2_review(current_card_id, int(quality))
        quality_value = int(quality)
    else:
        # Convert boolean + confidence to quality rating
        quality_value = current_card.get_quality_from_boolean(correct, confidence)
        result = StudyService.record_sm2_review(current_card_id, quality_value)

    # Update session stats
    current_session['total_studied'] += 1
    if correct or (quality_value and quality_value >= 3):
        current_session['correct_count'] += 1

    # Track quality ratings for session statistics
    current_session['quality_ratings'].append(quality_value)

    # Move to next card
    current_session['current_index'] += 1
    session['current_session'] = current_session

    if request.is_json:
        # Return JSON response for AJAX requests
        is_complete = current_session['current_index'] >= len(current_session['card_ids'])

        response_data = {
            'success': True,
            'is_complete': is_complete,
            'next_url': url_for('study.complete', deck_id=deck_id) if is_complete else url_for('study.study_session', deck_id=deck_id),
            'sm2_result': result  # Include SM-2 scheduling info (next review date, interval, etc.)
        }

        return jsonify(response_data)
    else:
        # Regular form submission
        return redirect(url_for('study.study_session', deck_id=deck_id))


@study_bp.route('/<int:deck_id>/complete')
@login_required
def complete(deck_id):
    """Study session completion page with SM-2 insights"""
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
    quality_ratings = current_session.get('quality_ratings', [])
    avg_quality = sum(quality_ratings) / len(quality_ratings) if quality_ratings else 0

    results = {
        'total_studied': current_session['total_studied'],
        'correct_count': current_session['correct_count'],
        'incorrect_count': current_session['total_studied'] - current_session['correct_count'],
        'accuracy': round((current_session['correct_count'] / current_session['total_studied']) * 100, 1) if current_session['total_studied'] > 0 else 0,
        'avg_quality': round(avg_quality, 1),
        'quality_ratings': quality_ratings
    }

    # Get updated deck statistics
    updated_stats = StudyService.get_study_statistics(deck_id)

    # Get next review forecast (7 days)
    upcoming_reviews = StudyService.get_upcoming_reviews(deck_id, days=7)

    # Clear session
    session.pop('current_session', None)
    session.pop('study_settings', None)

    return render_template(
        'study/complete.html',
        title='Study Complete',
        deck=deck,
        results=results,
        updated_stats=updated_stats,
        upcoming_reviews=upcoming_reviews
    )


@study_bp.route('/<int:deck_id>/review')
@login_required
def review(deck_id):
    """Review cards that are due (SM-2 based)"""
    deck = Deck.query.get_or_404(deck_id)

    # Check access permissions
    if not DeckService.user_can_access_deck(deck, current_user.id):
        flash('You do not have permission to review this deck.', 'error')
        return redirect(url_for('decks.index'))

    # Get cards due for review
    due_cards = StudyService.get_due_cards(deck_id)

    # Organize by learning state
    cards_by_state = {
        'new': [c for c in due_cards if c.learning_state == 'new'],
        'learning': [c for c in due_cards if c.learning_state == 'learning'],
        'review': [c for c in due_cards if c.learning_state == 'review'],
        'mastered': [c for c in due_cards if c.learning_state == 'mastered']
    }

    return render_template(
        'study/review.html',
        title=f'Review {deck.name}',
        deck=deck,
        due_cards=due_cards,
        cards_by_state=cards_by_state
    )


@study_bp.route('/<int:deck_id>/statistics')
@login_required
def statistics(deck_id):
    """Detailed study statistics with SM-2 insights"""
    deck = Deck.query.get_or_404(deck_id)

    # Check access permissions
    if not DeckService.user_can_access_deck(deck, current_user.id):
        flash('You do not have permission to view these statistics.', 'error')
        return redirect(url_for('decks.index'))

    stats = StudyService.get_study_statistics(deck_id)
    deck_stats = DeckService.get_deck_statistics(deck)

    # Get cards with detailed SM-2 stats
    cards = StudyService.get_deck_cards(deck_id)
    cards_with_stats = []

    for card in cards:
        health_score = StudyService.get_card_health_score(card)
        cards_with_stats.append({
            'card': card,
            'accuracy': card.get_accuracy(),
            'ease_factor': card.ease_factor,
            'interval': card.interval,
            'repetitions': card.repetitions,
            'learning_state': card.learning_state,
            'days_until_due': card.days_until_due(),
            'health_score': round(health_score),
            'needs_review': card.is_due_for_review()
        })

    # Sort by health score (worst first - cards that need attention)
    cards_with_stats.sort(key=lambda x: x['health_score'])

    # Get upcoming review forecast (30 days)
    upcoming_reviews = StudyService.get_upcoming_reviews(deck_id, days=30)

    return render_template(
        'study/statistics.html',
        title=f'{deck.name} - Statistics',
        deck=deck,
        stats=stats,
        deck_stats=deck_stats,
        cards_with_stats=cards_with_stats,
        upcoming_reviews=upcoming_reviews
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


@study_bp.route('/card/<int:card_id>/reset-progress', methods=['POST'])
@login_required
def reset_card_progress(card_id):
    """Reset SM-2 progress for a specific card"""
    card = StudyService.get_by_id(card_id)

    if not card:
        if request.is_json:
            return jsonify({'success': False, 'error': 'Card not found'}), 404
        flash('Card not found.', 'error')
        return redirect(url_for('decks.index'))

    # Check permissions
    deck = Deck.query.get(card.deck_id)
    if not DeckService.user_can_access_deck(deck, current_user.id):
        if request.is_json:
            return jsonify({'success': False, 'error': 'Permission denied'}), 403
        flash('Permission denied.', 'error')
        return redirect(url_for('decks.index'))

    # Reset the card
    StudyService.reset_card_progress(card_id)

    if request.is_json:
        return jsonify({
            'success': True,
            'message': 'Card progress reset successfully'
        })

    flash('Card progress has been reset. It will appear as a new card.', 'success')
    return redirect(url_for('study.statistics', deck_id=card.deck_id))


@study_bp.route('/<int:deck_id>/dashboard')
@login_required
def dashboard(deck_id):
    """SM-2 learning dashboard with detailed insights"""
    deck = Deck.query.get_or_404(deck_id)

    # Check access permissions
    if not DeckService.user_can_access_deck(deck, current_user.id):
        flash('You do not have permission to view this dashboard.', 'error')
        return redirect(url_for('decks.index'))

    # Get comprehensive statistics
    stats = StudyService.get_study_statistics(deck_id)

    # Get cards by learning state (preview first 5 of each)
    new_cards = StudyService.get_new_cards(deck_id, limit=5)
    learning_cards = StudyService.get_learning_cards(deck_id)[:5]
    review_cards = StudyService.get_review_cards(deck_id)[:5]
    mastered_cards = StudyService.get_mastered_cards(deck_id)[:5]
    due_cards = StudyService.get_due_cards(deck_id, limit=20)

    # Get 30-day forecast
    forecast = StudyService.get_upcoming_reviews(deck_id, days=30)

    return render_template(
        'study/dashboard.html',
        title=f'{deck.name} - Learning Dashboard',
        deck=deck,
        stats=stats,
        new_cards=new_cards,
        learning_cards=learning_cards,
        review_cards=review_cards,
        mastered_cards=mastered_cards,
        due_cards=due_cards,
        forecast=forecast
    )
