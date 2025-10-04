from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, abort
from flask_login import login_required, current_user
from app.models import Deck
from app.services.ai_service import AIService
from app.services import StudyService
from app.forms.ai_forms import AIGenerateCardsForm
from app.config import Config

ai_bp = Blueprint('ai', __name__, url_prefix='/ai')


@ai_bp.before_request
@login_required
def check_ai_access():
    """Ensure user has AI access before any AI route"""
    if not Config.AI_ENABLED:
        flash('AI features are currently unavailable.', 'warning')
        abort(403)

    if not current_user.has_ai_access():
        flash('You need to enable AI features in your profile to use this.', 'warning')
        abort(403)


@ai_bp.route('/deck/<int:deck_id>/generate', methods=['GET', 'POST'])
def generate_cards(deck_id):
    """Generate flashcards using AI"""
    # Verify deck ownership
    deck = Deck.query.filter_by(id=deck_id, user_id=current_user.id).first_or_404()

    form = AIGenerateCardsForm()

    if form.validate_on_submit():
        import traceback
        try:
            # Call AI service to generate cards
            print(f"\n=== AI Card Generation Started ===")
            print(f"Topic: {form.topic.data}")
            print(f"Count: {form.card_count.data}")
            print(f"Difficulty: {form.difficulty.data}")
            print(f"User ID: {current_user.id}")

            cards_data = AIService.generate_flashcards(
                topic=form.topic.data,
                count=form.card_count.data,
                difficulty=form.difficulty.data,
                additional_context=form.context.data,
                user_id=current_user.id
            )

            print(f"AI returned {len(cards_data) if cards_data else 0} cards")

            if cards_data:
                # Transform card data to match expected format
                print(f"Creating flashcards in deck {deck.id}...")
                print(f"Sample card data: {cards_data[0] if cards_data else 'None'}")

                # Convert 'front'/'back' to 'front_text'/'back_text' if needed
                transformed_cards = []
                for card in cards_data:
                    transformed_card = {
                        'front_text': card.get('front') or card.get('front_text', ''),
                        'back_text': card.get('back') or card.get('back_text', '')
                    }
                    transformed_cards.append(transformed_card)

                created_cards = StudyService.bulk_create_flashcards(
                    deck_id=deck.id,
                    cards_data=transformed_cards
                )

                # Mark cards as AI-generated manually
                from app.extensions import db
                for card in created_cards:
                    card.ai_generated = True
                    card.ai_provider = 'gemini'
                db.session.commit()

                print(f"Successfully created {len(created_cards)} cards")
                flash(f'✨ AI generated {len(created_cards)} flashcards!', 'success')
                return redirect(url_for('decks.view', id=deck.id))
            else:
                print("AI returned no cards")
                flash('AI generation failed. Please try again with a different topic.', 'error')

        except Exception as e:
            error_trace = traceback.format_exc()
            print(f"\n=== ERROR in AI Card Generation ===")
            print(f"Error Type: {type(e).__name__}")
            print(f"Error Message: {str(e)}")
            print(f"Full Traceback:\n{error_trace}")
            flash(f'Error generating cards: {str(e)}', 'error')

    return render_template(
        'ai/generate_cards.html',
        title='Generate Cards with AI',
        deck=deck,
        form=form
    )


@ai_bp.route('/card/<int:card_id>/enhance', methods=['POST'])
def enhance_card(card_id):
    """Enhance existing card with AI"""
    from app.models import Flashcard

    # Get card and verify ownership through deck
    card = Flashcard.query.get_or_404(card_id)
    deck = Deck.query.filter_by(id=card.deck_id, user_id=current_user.id).first_or_404()

    enhancement_type = request.json.get('type', 'clarity')

    try:
        enhanced = AIService.enhance_card(
            card.front_text,
            card.back_text,
            enhancement_type=enhancement_type,
            user_id=current_user.id
        )

        if enhanced:
            return jsonify({
                'success': True,
                'enhanced_front': enhanced['front'],
                'enhanced_back': enhanced['back'],
                'suggestions': enhanced.get('suggestions', [])
            })
        else:
            return jsonify({'error': 'Enhancement failed'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@ai_bp.route('/card/<int:card_id>/hint', methods=['POST'])
def get_hint(card_id):
    """Get AI-powered hint for a card during study"""
    from app.models import Flashcard

    card = Flashcard.query.get_or_404(card_id)

    # Verify access through deck ownership or public deck
    deck = Deck.query.get_or_404(card.deck_id)
    if deck.user_id != current_user.id and not deck.is_public:
        abort(403)

    try:
        hint = AIService.generate_hint(
            card.front_text,
            card.back_text,
            previous_attempts=request.json.get('attempts', 0),
            user_id=current_user.id
        )

        if hint:
            return jsonify({'hint': hint})
        else:
            return jsonify({'error': 'Unable to generate hint'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@ai_bp.route('/card/suggest-tags', methods=['POST'])
def suggest_tags():
    """Suggest tags for card content using AI"""
    front_text = request.json.get('front', '')
    back_text = request.json.get('back', '')

    if not front_text or not back_text:
        return jsonify({'error': 'Front and back text required'}), 400

    try:
        tags = AIService.suggest_tags(
            front_text,
            back_text,
            max_tags=5,
            user_id=current_user.id
        )

        if tags:
            return jsonify({'tags': tags})
        else:
            return jsonify({'error': 'Unable to suggest tags'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@ai_bp.route('/stats')
def usage_stats():
    """Show AI usage statistics for current user"""
    from app.models import AIUsage

    stats = AIUsage.get_user_usage_stats(current_user.id, days=30)

    return render_template(
        'ai/usage_stats.html',
        title='AI Usage Statistics',
        stats=stats
    )
