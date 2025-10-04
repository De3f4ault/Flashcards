from app.extensions import db
from app.models.base import BaseModel


class AIUsage(BaseModel):
    """Track AI API usage for billing and rate limiting"""
    __tablename__ = 'ai_usage_logs'

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    operation_type = db.Column(db.String(50), nullable=False)  # 'generate_cards', 'enhance_card', 'hint', 'tag_suggest'
    tokens_used = db.Column(db.Integer, default=0)
    cost = db.Column(db.Numeric(10, 6), default=0.0)  # Cost in USD
    success = db.Column(db.Boolean, default=True)
    error_message = db.Column(db.Text, nullable=True)

    # Store request details for debugging
    request_data = db.Column(db.Text, nullable=True)  # JSON string of request
    response_data = db.Column(db.Text, nullable=True)  # JSON string of response

    # Relationships
    user = db.relationship('User', backref=db.backref('ai_usage_logs', lazy='dynamic'))

    def __repr__(self):
        return f'<AIUsage {self.operation_type} by User {self.user_id}>'

    @staticmethod
    def log_usage(user_id, operation_type, tokens_used=0, cost=0.0, success=True, error_message=None, request_data=None, response_data=None):
        """Create a new usage log entry"""
        log = AIUsage(
            user_id=user_id,
            operation_type=operation_type,
            tokens_used=tokens_used,
            cost=cost,
            success=success,
            error_message=error_message,
            request_data=request_data,
            response_data=response_data
        )
        db.session.add(log)
        db.session.commit()
        return log

    @staticmethod
    def get_user_usage_stats(user_id, days=30):
        """Get usage statistics for a user over the last N days"""
        from datetime import datetime, timedelta
        from sqlalchemy import func

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        stats = db.session.query(
            AIUsage.operation_type,
            func.count(AIUsage.id).label('count'),
            func.sum(AIUsage.tokens_used).label('total_tokens'),
            func.sum(AIUsage.cost).label('total_cost')
        ).filter(
            AIUsage.user_id == user_id,
            AIUsage.created_at >= cutoff_date
        ).group_by(AIUsage.operation_type).all()

        return {
            stat.operation_type: {
                'count': stat.count,
                'total_tokens': stat.total_tokens or 0,
                'total_cost': float(stat.total_cost or 0)
            }
            for stat in stats
        }

    @staticmethod
    def get_hourly_request_count(user_id):
        """Get number of requests in the last hour for rate limiting"""
        from datetime import datetime, timedelta

        one_hour_ago = datetime.utcnow() - timedelta(hours=1)

        count = AIUsage.query.filter(
            AIUsage.user_id == user_id,
            AIUsage.created_at >= one_hour_ago
        ).count()

        return count
