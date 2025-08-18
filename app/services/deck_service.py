from app.models import Deck, Flashcard
from app.services.base_service import BaseService


class DeckService(BaseService):
    model = Deck

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

        # Copy all flashcards
        for card in original_deck.flashcards:
            Flashcard(
                deck_id=new_deck.id,
                front_text=card.front_text,
                back_text=card.back_text,
                difficulty=1  # Reset difficulty for new user
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
        avg_difficulty = sum(card.difficulty for card in deck.flashcards) / total_cards
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
