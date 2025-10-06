"""
MC Metrics Service
Convenience methods for logging metrics throughout the application
"""

from app.models.mc_metrics import MCMetrics
from app.extensions import db
import time


class MCMetricsService:
    """Service for tracking MC generation and study metrics"""

    @staticmethod
    def track_generation_request(user_id, deck_id, count):
        """Track when user requests generation"""
        try:
            MCMetrics.log_generation_request(user_id, deck_id, count)
        except Exception as e:
            print(f"Failed to log generation request: {e}")

    @staticmethod
    def track_generation_result(user_id, deck_id, requested, generated, duration, success=True, error=None):
        """Track generation result (success or failure)"""
        try:
            if success:
                MCMetrics.log_generation_success(user_id, deck_id, requested, generated, duration)
            else:
                MCMetrics.log_generation_failure(user_id, deck_id, requested, error or "Unknown error")
        except Exception as e:
            print(f"Failed to log generation result: {e}")

    @staticmethod
    def track_preview_save(user_id, deck_id, total_generated, accepted_count, edited_count):
        """
        Track user actions in preview screen

        Args:
            user_id: User ID
            deck_id: Deck ID
            total_generated: Total questions generated
            accepted_count: Number accepted (saved)
            edited_count: Number edited before accepting
        """
        try:
            deleted_count = total_generated - accepted_count
            MCMetrics.log_preview_action(user_id, deck_id, accepted_count, edited_count, deleted_count)
        except Exception as e:
            print(f"Failed to log preview action: {e}")

    @staticmethod
    def track_session_start(user_id, deck_id, session_id):
        """Track study session start"""
        try:
            MCMetrics.log_session_start(user_id, deck_id, session_id)
        except Exception as e:
            print(f"Failed to log session start: {e}")

    @staticmethod
    def track_session_complete(user_id, deck_id, session_id):
        """Track study session completion"""
        try:
            MCMetrics.log_session_complete(user_id, deck_id, session_id)
        except Exception as e:
            print(f"Failed to log session complete: {e}")

    @staticmethod
    def get_dashboard_metrics(days=7):
        """Get Phase 1 metrics for dashboard display"""
        return MCMetrics.get_phase1_metrics(days=days)

    @staticmethod
    def get_validation_report():
        """Get Go/No-Go report for Phase 2 decision"""
        return MCMetrics.get_phase1_validation_report()

    @staticmethod
    def format_report_for_display(report):
        """Format validation report for terminal/web display"""
        lines = []
        lines.append("=" * 60)
        lines.append("PHASE 1 VALIDATION REPORT")
        lines.append("=" * 60)
        lines.append("")

        for key, criterion in report['criteria'].items():
            status = "✓ PASS" if criterion['passing'] else "✗ FAIL"
            lines.append(f"{status} {criterion['name']}")
            lines.append(f"     Current: {criterion['current']}% | Target: {criterion['target']}%")
            lines.append(f"     {criterion['description']}")
            lines.append("")

        lines.append("=" * 60)
        lines.append(f"RESULT: {report['recommendation']}")
        lines.append(f"Passing Criteria: {report['passing_count']}/{report['total_criteria']}")
        lines.append("=" * 60)
        lines.append("")

        if report['notes']:
            lines.append("RECOMMENDATIONS:")
            for note in report['notes']:
                lines.append(note)
            lines.append("")

        return "\n".join(lines)


class MetricsTimer:
    """Context manager for timing operations"""

    def __init__(self):
        self.start_time = None
        self.duration = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.duration = time.time() - self.start_time
        return False

    def elapsed(self):
        """Get elapsed time in seconds"""
        return self.duration if self.duration else 0
