"""
MC Metrics Dashboard Views
Admin interface for viewing Phase 1 metrics
"""

from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from app.services.mc_metrics_service import MCMetricsService
from functools import wraps

mc_metrics_bp = Blueprint('mc_metrics', __name__, url_prefix='/mc/metrics')


def admin_required(f):
    """Decorator to require admin access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Simple check - you can add is_admin field to User model
        # For now, just check if user is authenticated
        if not current_user.is_authenticated:
            return "Unauthorized", 403
        return f(*args, **kwargs)
    return decorated_function


@mc_metrics_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """Phase 1 metrics dashboard"""
    days = 7  # Last 7 days
    metrics = MCMetricsService.get_dashboard_metrics(days=days)

    return render_template(
        'mc_metrics/dashboard.html',
        title='Phase 1 Metrics Dashboard',
        metrics=metrics,
        days=days
    )


@mc_metrics_bp.route('/validation-report')
@login_required
@admin_required
def validation_report():
    """Phase 2 Go/No-Go validation report"""
    report = MCMetricsService.get_validation_report()

    return render_template(
        'mc_metrics/validation_report.html',
        title='Phase 1 Validation Report',
        report=report
    )


@mc_metrics_bp.route('/api/metrics')
@login_required
@admin_required
def api_metrics():
    """JSON API for metrics"""
    days = 7
    metrics = MCMetricsService.get_dashboard_metrics(days=days)
    return jsonify(metrics)


@mc_metrics_bp.route('/api/validation')
@login_required
@admin_required
def api_validation():
    """JSON API for validation report"""
    report = MCMetricsService.get_validation_report()
    return jsonify(report)
