from datetime import datetime
from app.extensions import db


class BaseModel(db.Model):
    """Base model class with common fields"""
    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def save(self):
        """Save the instance to database"""
        db.session.add(self)
        db.session.commit()
        return self

    def delete(self):
        """Delete the instance from database"""
        db.session.delete(self)
        db.session.commit()

    def to_dict(self):
        """Convert model instance to dictionary"""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
