"""
Phase 1 Metrics Tracking
Tracks key metrics to validate Phase 1 success before moving to Phase 2
"""

from app.extensions import db
from app.models.base import BaseModel
from datetime import datetime, timedelta
from sqlalchemy import func, case


class MCMetrics(BaseModel):
    """Track MC generation and study metrics"""
    __tablename__ = 'mc_metrics'

    # Event tracking
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    deck_id = db.Column(db.Integer, db.ForeignKey('decks.id'), nullable=True)
    event_type = db.Column(db.String(50), nullable=False)  # 'generation_requested', 'generation_succeeded', etc.

    # Generation metrics
    questions_requested = db.Column(db.Integer, nullable=True)
    questions_generated = db.Column(db.Integer, nullable=True)
    questions_accepted = db.Column(db.Integer, nullable=True)
    questions_edited = db.Column(db.Integer, nullable=True)
    questions_deleted = db.Column(db.Integer, nullable=True)

    # Session metrics
    session_id = db.Column(db.Integer, db.ForeignKey('mc_sessions.id'), nullable=True)
    session_completed = db.Column(db.Boolean, default=False)

    # Generation details
    generation_time_seconds = db.Column(db.Float, nullable=True)
    generation_error = db.Column(db.Text, nullable=True)

    # Additional context
    extra_data = db.Column(db.Text, nullable=True)  # JSON string for extra data (changed from 'metadata')

    def __repr__(self):
        return f'<MCMetrics {self.event_type} user={self.user_id}>'

    @staticmethod
    def log_generation_request(user_id, deck_id, questions_requested):
        """Log when user requests question generation"""
        metric = MCMetrics(
            user_id=user_id,
            deck_id=deck_id,
            event_type='generation_requested',
            questions_requested=questions_requested
        )
        db.session.add(metric)
        db.session.commit()
        return metric

    @staticmethod
    def log_generation_success(user_id, deck_id, questions_requested, questions_generated, generation_time):
        """Log successful generation"""
        metric = MCMetrics(
            user_id=user_id,
            deck_id=deck_id,
            event_type='generation_succeeded',
            questions_requested=questions_requested,
            questions_generated=questions_generated,
            generation_time_seconds=generation_time
        )
        db.session.add(metric)
        db.session.commit()
        return metric

    @staticmethod
    def log_generation_failure(user_id, deck_id, questions_requested, error_message):
        """Log failed generation"""
        metric = MCMetrics(
            user_id=user_id,
            deck_id=deck_id,
            event_type='generation_failed',
            questions_requested=questions_requested,
            generation_error=error_message
        )
        db.session.add(metric)
        db.session.commit()
        return metric

    @staticmethod
    def log_preview_action(user_id, deck_id, accepted, edited, deleted):
        """Log user actions in preview"""
        metric = MCMetrics(
            user_id=user_id,
            deck_id=deck_id,
            event_type='preview_saved',
            questions_accepted=accepted,
            questions_edited=edited,
            questions_deleted=deleted
        )
        db.session.add(metric)
        db.session.commit()
        return metric

    @staticmethod
    def log_session_start(user_id, deck_id, session_id):
        """Log study session start"""
        metric = MCMetrics(
            user_id=user_id,
            deck_id=deck_id,
            session_id=session_id,
            event_type='session_started'
        )
        db.session.add(metric)
        db.session.commit()
        return metric

    @staticmethod
    def log_session_complete(user_id, deck_id, session_id):
        """Log study session completion"""
        metric = MCMetrics(
            user_id=user_id,
            deck_id=deck_id,
            session_id=session_id,
            event_type='session_completed',
            session_completed=True
        )
        db.session.add(metric)
        db.session.commit()
        return metric

    @staticmethod
    def get_phase1_metrics(days=7):
        """
        Get comprehensive Phase 1 metrics for validation

        Returns dict with all key metrics from the plan
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Technical Success Metrics
        total_requests = MCMetrics.query.filter(
            MCMetrics.event_type == 'generation_requested',
            MCMetrics.created_at >= cutoff_date
        ).count()

        successful_generations = MCMetrics.query.filter(
            MCMetrics.event_type == 'generation_succeeded',
            MCMetrics.created_at >= cutoff_date
        ).count()

        failed_generations = MCMetrics.query.filter(
            MCMetrics.event_type == 'generation_failed',
            MCMetrics.created_at >= cutoff_date
        ).count()

        technical_success_rate = (successful_generations / total_requests * 100) if total_requests > 0 else 0

        # Quality Success Metrics
        preview_actions = MCMetrics.query.filter(
            MCMetrics.event_type == 'preview_saved',
            MCMetrics.created_at >= cutoff_date
        ).all()

        total_generated = sum(m.questions_accepted + m.questions_edited + m.questions_deleted for m in preview_actions)
        total_accepted = sum(m.questions_accepted for m in preview_actions)
        total_edited = sum(m.questions_edited for m in preview_actions)

        acceptance_rate = (total_accepted / total_generated * 100) if total_generated > 0 else 0
        edit_rate = (total_edited / total_generated * 100) if total_generated > 0 else 0

        # Engagement Success Metrics
        sessions_started = MCMetrics.query.filter(
            MCMetrics.event_type == 'session_started',
            MCMetrics.created_at >= cutoff_date
        ).count()

        sessions_completed = MCMetrics.query.filter(
            MCMetrics.event_type == 'session_completed',
            MCMetrics.created_at >= cutoff_date
        ).count()

        completion_rate = (sessions_completed / sessions_started * 100) if sessions_started > 0 else 0

        # User Engagement
        unique_users = db.session.query(func.count(func.distinct(MCMetrics.user_id))).filter(
            MCMetrics.created_at >= cutoff_date
        ).scalar()

        users_who_generated = db.session.query(func.count(func.distinct(MCMetrics.user_id))).filter(
            MCMetrics.event_type == 'generation_requested',
            MCMetrics.created_at >= cutoff_date
        ).scalar()

        # Return rate calculation
        return_rate = MCMetrics._calculate_return_rate(cutoff_date)

        # Average generation time
        avg_gen_time = db.session.query(func.avg(MCMetrics.generation_time_seconds)).filter(
            MCMetrics.event_type == 'generation_succeeded',
            MCMetrics.created_at >= cutoff_date
        ).scalar() or 0

        return {
            'period_days': days,
            'technical_success': {
                'total_requests': total_requests,
                'successful': successful_generations,
                'failed': failed_generations,
                'success_rate': round(technical_success_rate, 1),
                'target': 90.0,
                'passing': technical_success_rate >= 90.0
            },
            'quality': {
                'total_questions_generated': total_generated,
                'accepted': total_accepted,
                'edited': total_edited,
                'acceptance_rate': round(acceptance_rate, 1),
                'edit_rate': round(edit_rate, 1),
                'target_acceptance': 60.0,
                'target_edit': 30.0,
                'passing': acceptance_rate >= 60.0 and edit_rate <= 30.0
            },
            'engagement': {
                'sessions_started': sessions_started,
                'sessions_completed': sessions_completed,
                'completion_rate': round(completion_rate, 1),
                'target': 70.0,
                'passing': completion_rate >= 70.0
            },
            'users': {
                'unique_users': unique_users,
                'users_who_generated': users_who_generated,
                'adoption_rate': round((users_who_generated / unique_users * 100), 1) if unique_users > 0 else 0,
                'return_rate': round(return_rate, 1),
                'target_return': 40.0,
                'passing': return_rate >= 40.0
            },
            'performance': {
                'avg_generation_time': round(avg_gen_time, 2),
                'target': 30.0,  # 30 seconds or less
                'passing': avg_gen_time <= 30.0
            }
        }

    @staticmethod
    def _calculate_return_rate(cutoff_date):
        """Calculate what % of users who generated once came back for a second generation"""
        # Get users with multiple generation requests
        user_generation_counts = db.session.query(
            MCMetrics.user_id,
            func.count(MCMetrics.id).label('generation_count')
        ).filter(
            MCMetrics.event_type == 'generation_requested',
            MCMetrics.created_at >= cutoff_date
        ).group_by(MCMetrics.user_id).all()

        total_users = len(user_generation_counts)
        returning_users = sum(1 for _, count in user_generation_counts if count > 1)

        return (returning_users / total_users * 100) if total_users > 0 else 0

    @staticmethod
    def get_phase1_validation_report():
        """
        Generate Go/No-Go decision report for Phase 2

        Returns formatted report with all criteria
        """
        metrics = MCMetrics.get_phase1_metrics(days=7)

        criteria = {
            'technical_success': {
                'name': 'Technical Success Rate',
                'current': metrics['technical_success']['success_rate'],
                'target': metrics['technical_success']['target'],
                'passing': metrics['technical_success']['passing'],
                'description': 'AI generation completes without errors'
            },
            'question_quality': {
                'name': 'Question Quality',
                'current': metrics['quality']['acceptance_rate'],
                'target': metrics['quality']['target_acceptance'],
                'passing': metrics['quality']['passing'],
                'description': 'Users approve questions without editing'
            },
            'session_completion': {
                'name': 'Session Completion Rate',
                'current': metrics['engagement']['completion_rate'],
                'target': metrics['engagement']['target'],
                'passing': metrics['engagement']['passing'],
                'description': 'Users finish study sessions they start'
            },
            'user_return': {
                'name': 'User Return Rate',
                'current': metrics['users']['return_rate'],
                'target': metrics['users']['target_return'],
                'passing': metrics['users']['passing'],
                'description': 'Users come back for second generation'
            }
        }

        passing_count = sum(1 for c in criteria.values() if c['passing'])
        total_criteria = len(criteria)

        recommendation = 'GO' if passing_count >= 3 else 'NO-GO'

        return {
            'criteria': criteria,
            'passing_count': passing_count,
            'total_criteria': total_criteria,
            'recommendation': recommendation,
            'raw_metrics': metrics,
            'notes': MCMetrics._generate_recommendations(criteria, metrics)
        }

    @staticmethod
    def _generate_recommendations(criteria, metrics):
        """Generate specific recommendations based on failing criteria"""
        notes = []

        if not criteria['technical_success']['passing']:
            notes.append("⚠️ Technical issues: Fix bugs and improve error handling before Phase 2")
            if metrics['technical_success']['failed'] > 0:
                notes.append(f"   - {metrics['technical_success']['failed']} failed generations need investigation")

        if not criteria['question_quality']['passing']:
            notes.append("⚠️ Quality issues: Improve AI prompts or focus on manual creation")
            if metrics['quality']['edit_rate'] > 30:
                notes.append(f"   - {metrics['quality']['edit_rate']}% edit rate is too high")

        if not criteria['session_completion']['passing']:
            notes.append("⚠️ Engagement issues: Simplify UX and reduce friction in study flow")

        if not criteria['user_return']['passing']:
            notes.append("⚠️ Return rate low: Improve basic study experience before adding complexity")

        if len(notes) == 0:
            notes.append("✅ All criteria met! Ready to proceed to Phase 2")

        return notes
