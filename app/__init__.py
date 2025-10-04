import os
from flask import Flask
from app.config import config
from app.extensions import db, migrate, login_manager, csrf  # Add csrf here
from app.routes import register_routes
from app.utils.helpers import (
    format_datetime, time_ago, truncate_text,
    get_difficulty_badge_class, get_accuracy_badge_class,
    pluralize, get_study_recommendation
)

def create_app(config_name=None):
    """Application factory pattern"""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)  # Add this line

    # Register routes
    register_routes(app)

    # Register template filters and globals
    register_template_helpers(app)

    # User loader for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))

    # Create database tables
    with app.app_context():
        db.create_all()

    return app

def register_template_helpers(app):
    """Register template filters and global functions"""
    # Template filters
    @app.template_filter('datetime')
    def datetime_filter(dt, format='%B %d, %Y at %I:%M %p'):
        return format_datetime(dt, format)

    @app.template_filter('timeago')
    def timeago_filter(dt):
        return time_ago(dt)

    @app.template_filter('truncate')
    def truncate_filter(text, length=50, suffix='...'):
        return truncate_text(text, length, suffix)

    @app.template_filter('pluralize')
    def pluralize_filter(count, singular, plural=None):
        return pluralize(count, singular, plural)

    # Template globals
    @app.template_global()
    def difficulty_badge_class(difficulty):
        return get_difficulty_badge_class(difficulty)

    @app.template_global()
    def accuracy_badge_class(accuracy):
        return get_accuracy_badge_class(accuracy)

    @app.template_global()
    def study_recommendation(stats):
        return get_study_recommendation(stats)

    @app.template_global()
    def difficulty_label(difficulty):
        labels = {
            1: 'Very Easy',
            2: 'Easy',
            3: 'Medium',
            4: 'Hard',
            5: 'Very Hard'
        }
        return labels.get(difficulty, 'Unknown')
