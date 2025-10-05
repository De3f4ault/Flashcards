from app.views.main import main_bp
from app.views.auth import auth_bp
from app.views.decks import decks_bp
from app.views.study import study_bp
from app.views.ai import ai_bp
from app.views.mc_generation import mc_generation_bp
from app.views.mc_study import mc_study_bp
from app.views.mc_metrics_view import mc_metrics_bp
from app.views.documents import documents_bp
from app.views.chat import chat_bp

__all__ = ['main_bp', 'auth_bp', 'decks_bp', 'study_bp', 'ai_bp', 'mc_generation_bp', 'mc_study_bp', 'mc_metrics_bp', 'documents_bp', 'chat_bp']
