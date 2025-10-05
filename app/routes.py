from app.views import main_bp, auth_bp, decks_bp, study_bp, ai_bp, mc_generation_bp, mc_study_bp, mc_metrics_bp, documents_bp, chat_bp


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

    # AI features routes
    app.register_blueprint(ai_bp, url_prefix='/ai')

    # MC Generation routes
    app.register_blueprint(mc_generation_bp)  # Prefix defined in blueprint: /mc

    # MC Study routes
    app.register_blueprint(mc_study_bp)  # Prefix defined in blueprint: /mc/study

    # MC Metrics routes (Phase 1 validation)
    app.register_blueprint(mc_metrics_bp)  # Prefix defined in blueprint: /mc/metrics

    # Documents routes (Phase 1 - Document Upload)
    app.register_blueprint(documents_bp)  # Prefix defined in blueprint: /documents

    # Chat routes (Phase 2 - AI Chat Interface)
    app.register_blueprint(chat_bp)  # Prefix defined in blueprint: /chat
