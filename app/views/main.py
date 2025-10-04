from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from app.services import DeckService, StudyService

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Homepage"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    # Get some public decks to showcase
    public_decks_pagination = DeckService.get_public_decks(page=1, per_page=6)
    featured_decks = public_decks_pagination.items

    return render_template(
        'main/index.html',
        title='Welcome to Flashcards',
        featured_decks=featured_decks
    )


@main_bp.route('/dashboard')
@login_required
def dashboard():
    """User dashboard"""
    # Get user's recent decks
    recent_decks_pagination = DeckService.get_user_decks(
        user_id=current_user.id,
        page=1,
        per_page=6
    )
    recent_decks = recent_decks_pagination.items

    # Calculate user statistics
    user_stats = {
        'total_decks': current_user.get_deck_count(),
        'total_cards': current_user.get_total_cards(),
    }

    # Get study statistics for recent decks
    deck_stats = []
    for deck in recent_decks:
        stats = StudyService.get_study_statistics(deck.id)
        deck_stats.append({
            'deck': deck,
            'stats': stats
        })

    # Get decks that need attention (cards needing review)
    decks_needing_attention = []
    for deck in recent_decks:
        review_cards = StudyService.get_cards_needing_review(deck.id)
        if review_cards:
            decks_needing_attention.append({
                'deck': deck,
                'review_count': len(review_cards)
            })

    return render_template(
        'main/dashboard.html',
        title='Dashboard',
        user_stats=user_stats,
        deck_stats=deck_stats,
        decks_needing_attention=decks_needing_attention
    )


@main_bp.route('/about')
def about():
    """About page"""
    return render_template('main/about.html', title='About')


@main_bp.route('/help')
def help():
    """Help page"""
    return render_template('main/help.html', title='Help')


@main_bp.app_errorhandler(404)
def not_found_error(error):
    """404 error handler"""
    return render_template('errors/404.html', title='Page Not Found'), 404


@main_bp.app_errorhandler(403)
def forbidden_error(error):
    """403 error handler"""
    return render_template('errors/403.html', title='Access Forbidden'), 403


@main_bp.app_errorhandler(500)
def internal_error(error):
    """500 error handler"""
    return render_template('errors/500.html', title='Server Error'), 500
