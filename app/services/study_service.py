import random
from app.models import Flashcard
from app.services.base_service import BaseService


class StudyService(BaseService):
    model = Flashcard

    @classmethod
    def create_flashcard(cls, deck_id, front_text, back_text):
        """Create a new flashcard"""
        return cls.create(
            deck_id=deck_id,
            front_text=front_text.strip(),
            back_text=back_text.strip(),
            difficulty=1
        )

    @classmethod
    def get_deck_cards(cls, deck_id):
        """Get all flashcards for a deck"""
        return Flashcard.query.filter_by(deck_id=deck_id).all()

    @classmethod
    def update_flashcard(cls, flashcard, **kwargs):
        """Update flashcard details"""
        allowed_fields = ['front_text', 'back_text']
        filtered_kwargs = {
            k: v.strip() if isinstance(v, str) else v
            for k, v in kwargs.items()
            if k in allowed_fields
        }
        return cls.update(flashcard, **filtered_kwargs)

    @classmethod
    def get_study_cards(cls, deck_id, study_mode='random', limit=None):
        """Get cards for study session based on study mode"""
        cards = cls.get_deck_cards(deck_id)

        if not cards:
            return []

        if study_mode == 'random':
            random.shuffle(cards)
        elif study_mode == 'difficulty_asc':
            cards.sort(key=lambda x: x.difficulty)
        elif study_mode == 'difficulty_desc':
            cards.sort(key=lambda x: x.difficulty, reverse=True)
        elif study_mode == 'accuracy_asc':
            cards.sort(key=lambda x: x.get_accuracy())
        elif study_mode == 'accuracy_desc':
            cards.sort(key=lambda x: x.get_accuracy(), reverse=True)
        elif study_mode == 'least_studied':
            cards.sort(key=lambda x: x.times_studied)
        elif study_mode == 'newest':
            cards.sort(key=lambda x: x.created_at, reverse=True)
        elif study_mode == 'oldest':
            cards.sort(key=lambda x: x.created_at)

        if limit:
            cards = cards[:limit]

        return cards

    @classmethod
    def record_study_result(cls, flashcard_id, correct):
        """Record the result of studying a flashcard"""
        flashcard = cls.get_by_id(flashcard_id)
        if flashcard:
            flashcard.mark_studied(correct)
            flashcard.save()
            return flashcard
        return None

    @classmethod
    def get_cards_needing_review(cls, deck_id):
        """Get cards that need more practice (low accuracy or high difficulty)"""
        cards = cls.get_deck_cards(deck_id)
        review_cards = []

        for card in cards:
            if card.times_studied > 0:
                accuracy = card.get_accuracy()
                if accuracy < 70 or card.difficulty >= 4:
                    review_cards.append(card)
            else:
                # New cards need to be studied
                review_cards.append(card)

        return review_cards

    @classmethod
    def get_study_statistics(cls, deck_id):
        """Get study statistics for a deck"""
        cards = cls.get_deck_cards(deck_id)

        if not cards:
            return {
                'total_cards': 0,
                'studied_cards': 0,
                'unstudied_cards': 0,
                'avg_accuracy': 0,
                'cards_needing_review': 0,
                'total_study_sessions': 0
            }

        total_cards = len(cards)
        studied_cards = len([c for c in cards if c.times_studied > 0])
        unstudied_cards = total_cards - studied_cards
        total_correct = sum(c.times_correct for c in cards)
        total_studies = sum(c.times_studied for c in cards)
        avg_accuracy = (total_correct / total_studies * 100) if total_studies > 0 else 0
        cards_needing_review = len(cls.get_cards_needing_review(deck_id))

        return {
            'total_cards': total_cards,
            'studied_cards': studied_cards,
            'unstudied_cards': unstudied_cards,
            'avg_accuracy': round(avg_accuracy, 1),
            'cards_needing_review': cards_needing_review,
            'total_study_sessions': total_studies
        }

    @classmethod
    def get_next_card_for_study(cls, deck_id, current_card_id=None):
        """Get the next card for study (simple implementation)"""
        cards = cls.get_study_cards(deck_id, study_mode='least_studied')

        if not cards:
            return None

        if current_card_id:
            # Try to find the next card after current
            try:
                current_index = next(i for i, card in enumerate(cards) if card.id == current_card_id)
                if current_index < len(cards) - 1:
                    return cards[current_index + 1]
            except StopIteration:
                pass

        # Return first card or None if no cards
        return cards[0] if cards else None

    @classmethod
    def bulk_create_flashcards(cls, deck_id, cards_data):
        """Create multiple flashcards at once"""
        created_cards = []

        for card_data in cards_data:
            if 'front_text' in card_data and 'back_text' in card_data:
                card = cls.create_flashcard(
                    deck_id=deck_id,
                    front_text=card_data['front_text'],
                    back_text=card_data['back_text']
                )
                created_cards.append(card)

        return created_cards
