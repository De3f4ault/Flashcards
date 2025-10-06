"""
MC Study Views
Handles routes for MC study sessions and answer processing
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, session, abort
from flask_login import login_required, current_user
from app.models import Deck, MCCard, MCSession, Document
from app.services.mc_study_service import MCStudyService
from app.services.document_qa_service import DocumentQAService
from app.services import DeckService
from app.forms import MCSessionStartForm, MCAnswerSubmitForm, MCFeedbackContinueForm
from datetime import datetime

mc_study_bp = Blueprint('mc_study', __name__, url_prefix='/mc/study')


@mc_study_bp.route('/deck/<int:deck_id>/start', methods=['GET', 'POST'])
@login_required
def start(deck_id):
    """Start an MC study session, optionally filtered by document"""
    deck = Deck.query.get_or_404(deck_id)

    # Check access permissions
    if not DeckService.user_can_access_deck(deck, current_user.id):
        flash('You do not have permission to study this deck.', 'error')
        return redirect(url_for('decks.index'))

    # Check if filtering by document (Phase 3 feature)
    document_id = request.args.get('document_id', type=int)
    document = None

    if document_id:
        # Verify document belongs to user
        document = Document.query.filter_by(id=document_id, user_id=current_user.id).first()
        if not document:
            flash('Document not found.', 'error')
            return redirect(url_for('mc_study.start', deck_id=deck_id))

        # Get cards filtered by document
        cards = MCCard.query.filter_by(deck_id=deck_id, document_id=document_id).all()

        if not cards:
            flash(f'No questions from "{document.original_filename}" found in this deck.', 'warning')
            return redirect(url_for('documents.view', id=document_id))
    else:
        # Get all available MC cards
        cards = MCStudyService.get_session_cards(deck_id, shuffle=True)

    if not cards:
        flash('This deck has no MC questions yet. Generate some first!', 'warning')
        if document_id:
            return redirect(url_for('documents.view', id=document_id))
        return redirect(url_for('decks.view', id=deck_id))

    # Shuffle cards if not already shuffled
    if document_id:
        import random
        cards = list(cards)
        random.shuffle(cards)

    # Get deck stats
    stats = MCStudyService.get_deck_mc_stats(deck_id)

    form = MCSessionStartForm()
    form.deck_id.data = deck_id

    if form.validate_on_submit():
        try:
            # Create session title with document info if filtered
            session_title = form.session_title.data
            if document_id and not session_title:
                session_title = f"Questions from {document.original_filename}"

            # Create session
            mc_session = MCStudyService.create_session(
                deck_id=deck_id,
                user_id=current_user.id,
                session_title=session_title
            )

            # Store session info in Flask session
            session['current_mc_session'] = {
                'session_id': mc_session.id,
                'deck_id': deck_id,
                'card_ids': [card.id for card in cards],
                'current_index': 0,
                'start_time': datetime.utcnow().isoformat(),
                'document_id': document_id  # Store for completion redirect
            }

            flash(f'{len(cards)} questions ready. Let\'s go!', 'success')
            return redirect(url_for('mc_study.question', deck_id=deck_id))

        except Exception as e:
            flash(f'Error starting session: {str(e)}', 'error')

    return render_template(
        'mc_study/start.html',
        title=f'Study MC - {deck.name}',
        deck=deck,
        form=form,
        card_count=len(cards),
        stats=stats,
        document=document  # Pass document to template for display
    )


@mc_study_bp.route('/deck/<int:deck_id>/question')
@login_required
def question(deck_id):
    """Display current question in session"""
    deck = Deck.query.get_or_404(deck_id)

    # Check access
    if not DeckService.user_can_access_deck(deck, current_user.id):
        abort(403)

    # Get current session
    current_session = session.get('current_mc_session')

    if not current_session or current_session['deck_id'] != deck_id:
        flash('No active study session. Please start a new session.', 'warning')
        return redirect(url_for('mc_study.start', deck_id=deck_id))

    # Check if session is complete
    if current_session['current_index'] >= len(current_session['card_ids']):
        return redirect(url_for('mc_study.complete', deck_id=deck_id))

    # Get current card
    card_id = current_session['card_ids'][current_session['current_index']]
    card = MCCard.query.get(card_id)

    if not card:
        flash('Error loading question.', 'error')
        return redirect(url_for('mc_study.start', deck_id=deck_id))

    # Progress info
    progress = {
        'current': current_session['current_index'] + 1,
        'total': len(current_session['card_ids']),
        'percentage': round(((current_session['current_index'] + 1) / len(current_session['card_ids'])) * 100)
    }

    # Get session stats
    mc_session_id = current_session['session_id']
    session_progress = MCStudyService.get_session_progress(mc_session_id)

    # Answer form
    answer_form = MCAnswerSubmitForm()
    answer_form.card_id.data = card.id
    answer_form.session_id.data = mc_session_id

    return render_template(
        'mc_study/question.html',
        title=f'Question {progress["current"]} of {progress["total"]}',
        deck=deck,
        card=card,
        choices=card.get_choices_dict(),
        progress=progress,
        session_stats=session_progress,
        form=answer_form
    )


@mc_study_bp.route('/deck/<int:deck_id>/answer', methods=['POST'])
@login_required
def submit_answer(deck_id):
    """Process submitted answer"""
    deck = Deck.query.get_or_404(deck_id)

    # Check access
    if not DeckService.user_can_access_deck(deck, current_user.id):
        if request.is_json:
            return jsonify({'success': False, 'error': 'Permission denied'}), 403
        abort(403)

    # Get current session
    current_session = session.get('current_mc_session')

    if not current_session or current_session['deck_id'] != deck_id:
        if request.is_json:
            return jsonify({'success': False, 'error': 'No active session'}), 400
        flash('Session expired. Please start a new session.', 'warning')
        return redirect(url_for('mc_study.start', deck_id=deck_id))

    # Get form data
    form = MCAnswerSubmitForm()

    if not form.validate_on_submit():
        if request.is_json:
            return jsonify({'success': False, 'errors': form.errors}), 400
        flash('Invalid form submission.', 'error')
        return redirect(url_for('mc_study.question', deck_id=deck_id))

    try:
        # Calculate time spent
        start_time = datetime.fromisoformat(current_session['start_time'])
        time_spent = int((datetime.utcnow() - start_time).total_seconds())

        # Record attempt
        result = MCStudyService.record_attempt(
            session_id=form.session_id.data,
            card_id=form.card_id.data,
            user_id=current_user.id,
            selected_choice=form.selected_choice.data,
            confidence_rating=form.confidence_rating.data,
            time_spent_seconds=min(time_spent, 300)  # Cap at 5 minutes
        )

        if not result['success']:
            if request.is_json:
                return jsonify(result), 400
            flash('Error recording answer.', 'error')
            return redirect(url_for('mc_study.question', deck_id=deck_id))

        # Move to next question
        current_session['current_index'] += 1
        current_session['start_time'] = datetime.utcnow().isoformat()  # Reset timer for next question
        session['current_mc_session'] = current_session

        # Store result for feedback page
        session['last_attempt'] = {
            'attempt_id': result['attempt_id'],
            'is_correct': result['is_correct']
        }

        if request.is_json:
            return jsonify({
                'success': True,
                'is_correct': result['is_correct'],
                'feedback_url': url_for('mc_study.feedback', deck_id=deck_id)
            })

        return redirect(url_for('mc_study.feedback', deck_id=deck_id))

    except Exception as e:
        print(f"Answer submission error: {str(e)}")
        if request.is_json:
            return jsonify({'success': False, 'error': str(e)}), 500
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('mc_study.question', deck_id=deck_id))


@mc_study_bp.route('/deck/<int:deck_id>/feedback')
@login_required
def feedback(deck_id):
    """Show feedback for last answer"""
    deck = Deck.query.get_or_404(deck_id)

    # Check access
    if not DeckService.user_can_access_deck(deck, current_user.id):
        abort(403)

    # Get last attempt
    last_attempt = session.get('last_attempt')

    if not last_attempt:
        flash('No feedback available.', 'warning')
        return redirect(url_for('mc_study.question', deck_id=deck_id))

    # Get feedback data
    feedback_data = MCStudyService.get_feedback_data(last_attempt['attempt_id'])

    if not feedback_data['success']:
        flash('Error loading feedback.', 'error')
        return redirect(url_for('mc_study.question', deck_id=deck_id))

    # Get session progress
    current_session = session.get('current_mc_session')
    is_complete = current_session['current_index'] >= len(current_session['card_ids'])

    # Continue form
    continue_form = MCFeedbackContinueForm()
    continue_form.session_id.data = current_session['session_id']

    return render_template(
        'mc_study/feedback.html',
        title='Answer Feedback',
        deck=deck,
        feedback=feedback_data,
        is_complete=is_complete,
        form=continue_form
    )


@mc_study_bp.route('/deck/<int:deck_id>/complete')
@login_required
def complete(deck_id):
    """Show session completion summary"""
    deck = Deck.query.get_or_404(deck_id)

    # Check access
    if not DeckService.user_can_access_deck(deck, current_user.id):
        abort(403)

    # Get session
    current_session = session.get('current_mc_session')

    if not current_session or current_session['deck_id'] != deck_id:
        flash('No session to complete.', 'warning')
        return redirect(url_for('decks.view', id=deck_id))

    # Get document_id if this was a document-filtered session
    document_id = current_session.get('document_id')
    document = None
    if document_id:
        document = Document.query.filter_by(id=document_id, user_id=current_user.id).first()

    # Complete the session
    session_id = current_session['session_id']
    result = MCStudyService.complete_session(session_id)

    if not result['success']:
        flash('Error completing session.', 'error')
        return redirect(url_for('decks.view', id=deck_id))

    summary = result['summary']

    # Clear session
    session.pop('current_mc_session', None)
    session.pop('last_attempt', None)

    return render_template(
        'mc_study/completion.html',
        title='Study Complete!',
        deck=deck,
        summary=summary,
        document=document  # Pass document for "Back to Document" link
    )


@mc_study_bp.route('/sessions')
@login_required
def sessions():
    """View past MC study sessions"""
    deck_id = request.args.get('deck_id', type=int)

    if deck_id:
        deck = Deck.query.get_or_404(deck_id)
        if not DeckService.user_can_access_deck(deck, current_user.id):
            abort(403)
        sessions_list = MCStudyService.get_user_sessions(current_user.id, deck_id=deck_id)
    else:
        deck = None
        sessions_list = MCStudyService.get_user_sessions(current_user.id)

    return render_template(
        'mc_study/sessions_history.html',
        title='MC Study Sessions',
        deck=deck,
        sessions=sessions_list
    )


@mc_study_bp.route('/session/<int:session_id>')
@login_required
def view_session(session_id):
    """View details of a completed session"""
    mc_session = MCSession.query.get_or_404(session_id)

    # Check ownership
    if mc_session.user_id != current_user.id:
        abort(403)

    deck = Deck.query.get_or_404(mc_session.deck_id)

    summary = mc_session.get_summary_stats()

    # Get all attempts
    attempts = mc_session.attempts

    return render_template(
        'mc_study/session_detail.html',
        title=f'Session: {mc_session.session_title or "Untitled"}',
        deck=deck,
        session=mc_session,
        summary=summary,
        attempts=attempts
    )


@mc_study_bp.route('/reset-session', methods=['POST'])
@login_required
def reset_session():
    """Reset/abandon current study session"""
    session.pop('current_mc_session', None)
    session.pop('last_attempt', None)

    deck_id = request.form.get('deck_id', type=int)
    if deck_id:
        flash('Study session reset.', 'info')
        return redirect(url_for('mc_study.start', deck_id=deck_id))

    return redirect(url_for('decks.index'))
