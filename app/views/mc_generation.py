"""
MC Generation Views
Handles routes for generating and managing MC questions
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, abort, session
from flask_login import login_required, current_user
from app.models import Deck, MCCard
from app.services.mc_generator_service import MCGeneratorService
from app.forms import MCGenerationRequestForm, MCQuestionEditForm, MCManualCreateForm
from app.config import Config
from app.extensions import db

mc_generation_bp = Blueprint('mc_generation', __name__, url_prefix='/mc')


@mc_generation_bp.before_request
@login_required
def check_mc_access():
    """Ensure user has MC generation access"""
    if not Config.AI_ENABLED or not Config.AI_CARD_GENERATION_ENABLED:
        flash('MC question generation is currently unavailable.', 'warning')
        abort(403)

    if not current_user.ai_enabled:
        flash('AI features are disabled. Please enable them in your profile.', 'warning')
        abort(403)


@mc_generation_bp.route('/deck/<int:deck_id>/generate', methods=['GET', 'POST'])
def generate_request(deck_id):
    """Request form for generating MC questions"""
    deck = Deck.query.filter_by(id=deck_id, user_id=current_user.id).first_or_404()
    form = MCGenerationRequestForm()
    form.deck_id.data = deck_id

    if form.validate_on_submit():
        try:
            result = MCGeneratorService.generate_questions(
                topic=form.topic.data,
                count=form.count.data,
                difficulty=form.difficulty.data,
                subject_area=form.subject_area.data,
                deck_id=deck_id,
                user_id=current_user.id,
                additional_context=form.additional_context.data
            )

            if result['success'] and result['questions']:
                # For large question sets, save immediately to avoid session overflow
                question_count = len(result['questions'])

                if question_count > 5:
                    # Save questions to database immediately
                    save_result = MCGeneratorService.save_questions(result['questions'])

                    if save_result['success']:
                        card_ids = [q.id for q in result['questions']]

                        session['pending_mc_questions'] = {
                            'deck_id': deck_id,
                            'topic': form.topic.data,
                            'card_ids': card_ids,
                            'count': question_count
                        }
                    else:
                        flash(f'Error saving questions: {save_result.get("error")}', 'error')
                        return render_template('mc_generation/request.html', title='Generate MC Questions', deck=deck, form=form)
                else:
                    # For small sets, keep in session
                    questions_data = [q.to_dict_with_answer() for q in result['questions']]
                    session['pending_mc_questions'] = {
                        'deck_id': deck_id,
                        'topic': form.topic.data,
                        'questions': questions_data
                    }

                if result.get('parse_warnings'):
                    flash(f'Generated {question_count} questions with warnings. Review and confirm below.', 'warning')
                else:
                    flash(f'Generated {question_count} questions! Review and confirm to save.', 'success')

                return redirect(url_for('mc_generation.preview', deck_id=deck_id))
            else:
                error_msg = result.get('error', 'Generation failed')
                if 'raw_response' in result:
                    print(f"Raw response preview: {result['raw_response'][:200]}")

                if 'AI returned empty response' in error_msg:
                    flash('The AI service did not return a response. This may be due to API issues or the request being too complex. Try reducing the number of questions or simplifying the topic.', 'error')
                elif 'Could not parse' in error_msg:
                    flash(f'Generated response could not be parsed: {error_msg[:200]}', 'error')
                else:
                    flash(f'Failed to generate questions: {error_msg[:200]}', 'error')

        except Exception as e:
            print(f"Generation exception: {str(e)}")
            import traceback
            traceback.print_exc()
            flash(f'Error generating questions: {str(e)[:200]}', 'error')

    return render_template('mc_generation/request.html', title='Generate MC Questions', deck=deck, form=form)


@mc_generation_bp.route('/deck/<int:deck_id>/preview')
def preview(deck_id):
    """Preview generated questions before saving"""
    deck = Deck.query.filter_by(id=deck_id, user_id=current_user.id).first_or_404()
    pending = session.get('pending_mc_questions')

    if not pending or pending['deck_id'] != deck_id:
        flash('No pending questions to preview.', 'warning')
        return redirect(url_for('mc_generation.generate_request', deck_id=deck_id))

    # Check if we stored IDs (for large sets) or full questions (for small sets)
    if 'card_ids' in pending:
        # Load from database
        card_ids = pending['card_ids']
        cards = MCCard.query.filter(MCCard.id.in_(card_ids)).all()
        questions = [card.to_dict_with_answer() for card in cards]
    else:
        # Load from session
        questions = pending['questions']

    return render_template('mc_generation/preview.html', title='Preview Generated Questions', deck=deck, questions=questions, topic=pending['topic'])


@mc_generation_bp.route('/deck/<int:deck_id>/save', methods=['POST'])
def save_questions(deck_id):
    """Confirm saved questions (they're already in DB if >5 questions)"""
    deck = Deck.query.filter_by(id=deck_id, user_id=current_user.id).first_or_404()
    pending = session.get('pending_mc_questions')

    if not pending or pending['deck_id'] != deck_id:
        flash('No pending questions to save.', 'error')
        return redirect(url_for('decks.view', id=deck_id))

    try:
        # Check if questions are already in DB (large set) or need to be saved (small set)
        if 'card_ids' in pending:
            # Already saved, just clear session and confirm
            session.pop('pending_mc_questions', None)
            card_count = pending.get('count', len(pending['card_ids']))
            flash(f'Confirmed {card_count} MC questions!', 'success')
            return redirect(url_for('decks.view', id=deck_id))
        else:
            # Small set - save from session
            selected_indices = request.form.getlist('selected_questions')
            if not selected_indices:
                flash('Please select at least one question to save.', 'warning')
                return redirect(url_for('mc_generation.preview', deck_id=deck_id))

            cards_to_save = []
            for idx in selected_indices:
                q_data = pending['questions'][int(idx)]
                card = MCCard(
                    deck_id=deck_id,
                    question_text=q_data['question_text'],
                    choice_a=q_data['choices']['A'],
                    choice_b=q_data['choices']['B'],
                    choice_c=q_data['choices']['C'],
                    choice_d=q_data['choices']['D'],
                    correct_answer=q_data['correct_answer'],
                    misconception_a=q_data['misconceptions'].get('A'),
                    misconception_b=q_data['misconceptions'].get('B'),
                    misconception_c=q_data['misconceptions'].get('C'),
                    misconception_d=q_data['misconceptions'].get('D'),
                    difficulty=q_data['difficulty'],
                    concept_tags=','.join(q_data['concept_tags']) if isinstance(q_data['concept_tags'], list) else q_data['concept_tags'],
                    ai_generated=q_data['ai_generated'],
                    generation_topic=q_data['generation_topic'],
                    ai_provider='gemini'
                )
                cards_to_save.append(card)

            result = MCGeneratorService.save_questions(cards_to_save)

            if result['success']:
                session.pop('pending_mc_questions', None)
                flash(f'Successfully saved {result["saved_count"]} MC questions!', 'success')
                return redirect(url_for('decks.view', id=deck_id))
            else:
                flash(f'Error saving questions: {result.get("error")}', 'error')
                return redirect(url_for('mc_generation.preview', deck_id=deck_id))

    except Exception as e:
        flash(f'Error saving questions: {str(e)}', 'error')
        return redirect(url_for('mc_generation.preview', deck_id=deck_id))


@mc_generation_bp.route('/question/<int:question_index>/regenerate', methods=['POST'])
def regenerate_question(question_index):
    """Regenerate a single question in preview"""
    pending = session.get('pending_mc_questions')
    if not pending or question_index >= len(pending['questions']):
        return jsonify({'success': False, 'error': 'Question not found'}), 404

    try:
        original_q = pending['questions'][question_index]
        deck_id = pending['deck_id']
        temp_card = MCCard(
            deck_id=deck_id,
            question_text=original_q['question_text'],
            difficulty=original_q['difficulty'],
            generation_topic=pending['topic']
        )

        new_card = MCGeneratorService.regenerate_single_question(temp_card, reason="User requested regeneration")
        if new_card:
            pending['questions'][question_index] = new_card.to_dict_with_answer()
            session['pending_mc_questions'] = pending
            return jsonify({'success': True, 'question': new_card.to_dict_with_answer()})
        else:
            return jsonify({'success': False, 'error': 'Regeneration failed'}), 500

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@mc_generation_bp.route('/question/<int:question_index>/delete', methods=['POST'])
def delete_preview_question(question_index):
    """Delete a question from preview"""
    pending = session.get('pending_mc_questions')
    if not pending or question_index >= len(pending['questions']):
        return jsonify({'success': False, 'error': 'Question not found'}), 404

    try:
        pending['questions'].pop(question_index)
        session['pending_mc_questions'] = pending
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@mc_generation_bp.route('/deck/<int:deck_id>/manual', methods=['GET', 'POST'])
def manual_create(deck_id):
    """Manually create MC question (fallback if AI fails)"""
    deck = Deck.query.filter_by(id=deck_id, user_id=current_user.id).first_or_404()
    form = MCManualCreateForm()
    form.deck_id.data = deck_id

    if form.validate_on_submit():
        try:
            card = MCCard(
                deck_id=deck_id,
                question_text=form.question_text.data,
                choice_a=form.choice_a.data,
                choice_b=form.choice_b.data,
                choice_c=form.choice_c.data,
                choice_d=form.choice_d.data,
                correct_answer=form.correct_answer.data,
                misconception_a=form.misconception_a.data,
                misconception_b=form.misconception_b.data,
                misconception_c=form.misconception_c.data,
                misconception_d=form.misconception_d.data,
                difficulty=form.difficulty.data,
                concept_tags=form.concept_tags.data,
                ai_generated=False
            )
            db.session.add(card)
            db.session.commit()
            flash('MC question created successfully!', 'success')
            return redirect(url_for('decks.view', id=deck_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating question: {str(e)}', 'error')

    return render_template('mc_generation/manual_create.html', title='Create MC Question', deck=deck, form=form)


@mc_generation_bp.route('/card/<int:card_id>/edit', methods=['GET', 'POST'])
def edit_card(card_id):
    """Edit an existing MC card"""
    card = MCCard.query.get_or_404(card_id)
    deck = Deck.query.filter_by(id=card.deck_id, user_id=current_user.id).first_or_404()
    form = MCQuestionEditForm()

    if form.validate_on_submit():
        try:
            result = MCGeneratorService.update_card_manual(
                card=card,
                question_text=form.question_text.data,
                choices={'A': form.choice_a.data, 'B': form.choice_b.data, 'C': form.choice_c.data, 'D': form.choice_d.data},
                correct_answer=form.correct_answer.data,
                misconceptions={'A': form.misconception_a.data, 'B': form.misconception_b.data, 'C': form.misconception_c.data, 'D': form.misconception_d.data}
            )
            if result['success']:
                flash('MC question updated successfully!', 'success')
                return redirect(url_for('decks.view', id=deck.id))
            else:
                flash(f'Error updating question: {result.get("error")}', 'error')
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')
    elif request.method == 'GET':
        form.question_text.data = card.question_text
        form.choice_a.data = card.choice_a
        form.choice_b.data = card.choice_b
        form.choice_c.data = card.choice_c
        form.choice_d.data = card.choice_d
        form.correct_answer.data = card.correct_answer
        form.misconception_a.data = card.misconception_a
        form.misconception_b.data = card.misconception_b
        form.misconception_c.data = card.misconception_c
        form.misconception_d.data = card.misconception_d

    return render_template('mc_generation/edit_card.html', title='Edit MC Question', deck=deck, card=card, form=form)


@mc_generation_bp.route('/card/<int:card_id>/delete', methods=['POST'])
def delete_card(card_id):
    """Delete an MC card"""
    card = MCCard.query.get_or_404(card_id)
    deck = Deck.query.filter_by(id=card.deck_id, user_id=current_user.id).first_or_404()

    try:
        from app.services.mc_study_service import MCStudyService
        result = MCStudyService.delete_card(card_id)
        if result['success']:
            flash('MC question deleted successfully.', 'success')
        else:
            flash(f'Error deleting question: {result.get("error")}', 'error')
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')

    return redirect(url_for('decks.view', id=deck.id))


@mc_generation_bp.route('/cancel-preview')
def cancel_preview():
    """Cancel preview and discard pending questions"""
    pending = session.pop('pending_mc_questions', None)
    if pending:
        deck_id = pending['deck_id']
        flash('Question generation cancelled.', 'info')
        return redirect(url_for('decks.view', id=deck_id))
    return redirect(url_for('decks.index'))
