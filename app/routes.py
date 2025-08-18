from app.views import main_bp, auth_bp, decks_bp, study_bp


def register_routes(app):
    """Register all application routes"""

    # Main routes (homepage, dashboard, etc.)
    app.register_blueprint(main_bp)

    # Authentication routes
    app.register_blueprint(auth_bp, url_prefix='/auth')

    # Deck management routes
    app.register_blueprint(decks_bp, url_prefix='/decks')

    # Study session routes
    app.register_blueprint(study_bp, url_prefix='/study')
