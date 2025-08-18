from app.extensions import db


class BaseService:
    """Base service class with common CRUD operations"""

    model = None  # To be overridden in child classes

    @classmethod
    def get_by_id(cls, id):
        """Get record by ID"""
        return cls.model.query.get(id)

    @classmethod
    def get_all(cls):
        """Get all records"""
        return cls.model.query.all()

    @classmethod
    def create(cls, **kwargs):
        """Create new record"""
        instance = cls.model(**kwargs)
        return instance.save()

    @classmethod
    def update(cls, instance, **kwargs):
        """Update existing record"""
        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        return instance.save()

    @classmethod
    def delete(cls, instance):
        """Delete record"""
        instance.delete()
        return True

    @classmethod
    def get_paginated(cls, page=1, per_page=20, **filters):
        """Get paginated records with optional filters"""
        query = cls.model.query

        # Apply filters
        for key, value in filters.items():
            if hasattr(cls.model, key) and value is not None:
                query = query.filter(getattr(cls.model, key) == value)

        return query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

    @classmethod
    def get_or_404(cls, id):
        """Get record by ID or raise 404"""
        return cls.model.query.get_or_404(id)

    @classmethod
    def exists(cls, **filters):
        """Check if record exists with given filters"""
        query = cls.model.query
        for key, value in filters.items():
            if hasattr(cls.model, key):
                query = query.filter(getattr(cls.model, key) == value)
        return query.first() is not None
