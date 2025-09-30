from app.models import Deck, Flashcard
from app.services.base_service import BaseService
from app.extensions import db
from datetime import datetime, timedelta
from sqlalchemy import func, or_


class DeckService(BaseService):
    model = Deck

    # ============================================================================
    # ORIGINAL METHODS (Preserved)
    # ============================================================================

    @classmethod
    def create_deck(cls, user_id, name, description="", is_public=False):
        """Create a new deck for a user"""
        deck = cls.create(
            user_id=user_id,
            name=name,
            description=description,
            is_public=is_public
        )
        return deck

    @classmethod
    def get_user_decks(cls, user_id, page=1, per_page=12):
        """Get all decks for a specific user with pagination"""
        return cls.get_paginated(page=page, per_page=per_page, user_id=user_id)

    @classmethod
    def get_public_decks(cls, page=1, per_page=12):
        """Get all public decks with pagination"""
        return cls.get_paginated(page=page, per_page=per_page, is_public=True)

    @classmethod
    def get_deck_with_cards(cls, deck_id):
        """Get deck with all its flashcards"""
        deck = cls.get_by_id(deck_id)
        if deck:
            # Eager load flashcards to avoid N+1 queries
            deck = Deck.query.options(
                db.joinedload(Deck.flashcards)
            ).get(deck_id)
        return deck

    @classmethod
    def user_can_access_deck(cls, deck, user_id):
        """Check if user can access a deck (owner or public)"""
        if not deck:
            return False
        return deck.user_id == user_id or deck.is_public

    @classmethod
    def user_owns_deck(cls, deck, user_id):
        """Check if user owns the deck"""
        if not deck:
            return False
        return deck.user_id == user_id

    @classmethod
    def update_deck(cls, deck, **kwargs):
        """Update deck details"""
        allowed_fields = ['name', 'description', 'is_public']
        filtered_kwargs = {
            k: v for k, v in kwargs.items()
            if k in allowed_fields
        }
        return cls.update(deck, **filtered_kwargs)

    @classmethod
    def duplicate_deck(cls, original_deck, new_user_id, new_name=None):
        """Create a copy of a deck for another user"""
        # Create new deck
        new_deck = cls.create_deck(
            user_id=new_user_id,
            name=new_name or f"Copy of {original_deck.name}",
            description=original_deck.description,
            is_public=False
        )

        # Copy all flashcards with SM-2 fields
        for card in original_deck.flashcards:
            Flashcard(
                deck_id=new_deck.id,
                front=card.front,
                back=card.back,
                # Reset SM-2 fields for new user
                ease_factor=2.5,
                interval=0,
                repetitions=0,
                learning_state='new'
            ).save()

        return new_deck

    @classmethod
    def get_deck_statistics(cls, deck):
        """Get comprehensive statistics for a deck"""
        if not deck.flashcards:
            return {
                'total_cards': 0,
                'avg_difficulty': 0,
                'total_studies': 0,
                'avg_accuracy': 0
            }

        total_cards = len(deck.flashcards)
        total_studies = sum(card.times_studied for card in deck.flashcards)
        total_correct = sum(card.times_correct for card in deck.flashcards)

        # Use ease_factor as difficulty indicator (lower = harder)
        avg_difficulty = sum(card.ease_factor for card in deck.flashcards) / total_cards
        avg_accuracy = (total_correct / total_studies * 100) if total_studies > 0 else 0

        return {
            'total_cards': total_cards,
            'avg_difficulty': round(avg_difficulty, 1),
            'total_studies': total_studies,
            'avg_accuracy': round(avg_accuracy, 1)
        }

    @classmethod
    def search_decks(cls, query, user_id=None, include_public=True):
        """Search decks by name or description"""
        search_filter = Deck.name.contains(query) | Deck.description.contains(query)

        if user_id and include_public:
            # User's decks + public decks
            deck_query = Deck.query.filter(
                search_filter &
                ((Deck.user_id == user_id) | (Deck.is_public == True))
            )
        elif user_id:
            # Only user's decks
            deck_query = Deck.query.filter(
                search_filter & (Deck.user_id == user_id)
            )
        else:
            # Only public decks
            deck_query = Deck.query.filter(
                search_filter & (Deck.is_public == True)
            )

        return deck_query.all()

    # ============================================================================
    # NEW: SEARCH & FILTER METHODS FOR CARDS
    # ============================================================================

    @classmethod
    def search_deck_cards(cls, deck_id, query=None, learning_state=None,
                         difficulty=None, sort_by='created_desc',
                         date_from=None, date_to=None, page=1, per_page=50):
        """
        Search and filter cards within a deck with pagination

        Args:
            deck_id: ID of the deck to search
            query: Search term for card content
            learning_state: Filter by learning state
            difficulty: Filter by difficulty level
            sort_by: Sort method
            date_from: Filter cards created after this date
            date_to: Filter cards created before this date
            page: Page number for pagination
            per_page: Items per page

        Returns:
            Paginated query result with cards
        """
        deck = cls.get_by_id(deck_id)
        if not deck:
            return None

        # Use the deck's search method
        cards_query = deck.search_cards(
            query=query,
            learning_state=learning_state,
            difficulty=difficulty,
            sort_by=sort_by,
            date_from=date_from,
            date_to=date_to
        )

        # Paginate results
        return cards_query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

    @classmethod
    def get_filtered_cards(cls, deck_id, filters=None):
        """
        Get filtered cards from a deck (non-paginated)

        Args:
            deck_id: ID of the deck
            filters: Dictionary with filter parameters

        Returns:
            List of filtered flashcards
        """
        deck = cls.get_by_id(deck_id)
        if not deck:
            return []

        filters = filters or {}

        cards_query = deck.search_cards(
            query=filters.get('query'),
            learning_state=filters.get('learning_state'),
            difficulty=filters.get('difficulty'),
            sort_by=filters.get('sort_by', 'created_desc'),
            date_from=filters.get('date_from'),
            date_to=filters.get('date_to')
        )

        return cards_query.all()

    @classmethod
    def get_cards_by_learning_state(cls, deck_id, state):
        """Get all cards in a specific learning state"""
        deck = cls.get_by_id(deck_id)
        if not deck:
            return []
        return deck.get_cards_by_state(state)

    @classmethod
    def get_deck_card_statistics(cls, deck_id):
        """Get comprehensive card statistics for a deck"""
        deck = cls.get_by_id(deck_id)
        if not deck:
            return None
        return deck.get_cards_statistics()

    @classmethod
    def get_deck_difficulty_distribution(cls, deck_id):
        """Get difficulty distribution for a deck"""
        deck = cls.get_by_id(deck_id)
        if not deck:
            return None
        return deck.get_difficulty_distribution()

    @classmethod
    def get_due_cards_count(cls, deck_id):
        """Get count of cards due for review today"""
        from app.models.flashcard import Flashcard

        today = datetime.utcnow()
        return Flashcard.query.filter(
            Flashcard.deck_id == deck_id,
            Flashcard.next_review_date <= today
        ).count()

    @classmethod
    def quick_search_cards(cls, deck_id, query):
        """
        Quick search for cards (for autocomplete/live search)
        Returns only front text and IDs for performance

        Args:
            deck_id: ID of the deck
            query: Search term

        Returns:
            List of tuples (card_id, front_text)
        """
        from app.models.flashcard import Flashcard

        if not query or len(query) < 2:
            return []

        search_term = f"%{query.lower()}%"

        results = db.session.query(
            Flashcard.id,
            Flashcard.front
        ).filter(
            Flashcard.deck_id == deck_id,
            or_(
                func.lower(Flashcard.front).like(search_term),
                func.lower(Flashcard.back).like(search_term)
            )
        ).limit(10).all()

        return results

    @classmethod
    def get_cards_needing_review(cls, deck_id, days_ahead=7):
        """
        Get cards that will need review in the next X days

        Args:
            deck_id: ID of the deck
            days_ahead: Number of days to look ahead

        Returns:
            Dictionary with date as key and card count as value
        """
        from app.models.flashcard import Flashcard

        today = datetime.utcnow()
        end_date = today + timedelta(days=days_ahead)

        cards = Flashcard.query.filter(
            Flashcard.deck_id == deck_id,
            Flashcard.next_review_date.between(today, end_date)
        ).all()

        # Group by date
        review_schedule = {}
        for i in range(days_ahead + 1):
            date = (today + timedelta(days=i)).date()
            review_schedule[date.isoformat()] = 0

        for card in cards:
            if card.next_review_date:
                date_key = card.next_review_date.date().isoformat()
                if date_key in review_schedule:
                    review_schedule[date_key] += 1

        return review_schedule

    @classmethod
    def get_advanced_deck_stats(cls, deck_id):
        """
        Get advanced statistics for a deck

        Returns comprehensive analytics including:
        - Card distribution
        - Study patterns
        - Difficulty metrics
        - Review forecast
        """
        deck = cls.get_by_id(deck_id)
        if not deck:
            return None

        card_stats = deck.get_cards_statistics()
        difficulty_dist = deck.get_difficulty_distribution()
        review_forecast = cls.get_cards_needing_review(deck_id, days_ahead=7)

        return {
            'basic_stats': card_stats,
            'difficulty_distribution': difficulty_dist,
            'review_forecast': review_forecast,
            'deck_info': {
                'id': deck.id,
                'name': deck.name,
                'created_at': deck.created_at.isoformat(),
                'is_public': deck.is_public
            }
        }

    @classmethod
    def export_deck_data(cls, deck_id, include_stats=False):
        """
        Export deck data in a structured format

        Args:
            deck_id: ID of the deck
            include_stats: Whether to include statistics

        Returns:
            Dictionary with complete deck data
        """
        deck = cls.get_by_id(deck_id)
        if not deck:
            return None

        export_data = {
            'deck': deck.to_dict_detailed() if include_stats else deck.to_dict_summary(),
            'cards': [card.to_dict() for card in deck.flashcards]
        }

        return export_data
