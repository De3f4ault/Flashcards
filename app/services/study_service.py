import random
from datetime import datetime, timedelta
from sqlalchemy import and_
from app.models import Flashcard
from app.services.base_service import BaseService


class StudyService(BaseService):
    model = Flashcard

    # ========== CARD CREATION & MANAGEMENT ==========

    @classmethod
    def create_flashcard(cls, deck_id, front_text, back_text):
        """Create a new flashcard with SM-2 initialization"""
        return cls.create(
            deck_id=deck_id,
            front_text=front_text.strip(),
            back_text=back_text.strip(),
            difficulty=1,
            ease_factor=2.5,
            interval=0,
            repetitions=0,
            next_review_date=datetime.utcnow(),
            learning_state='new'
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

    # ========== SM-2 SPACED REPETITION CORE METHODS ==========

    @classmethod
    def get_due_cards(cls, deck_id, limit=None):
        """
        Get cards that are due for review today (SM-2 PRIORITY METHOD)

        This is the PRIMARY method for spaced repetition study sessions.
        Cards are returned in optimal learning order:
        1. Failed cards (need immediate review)
        2. New cards (never studied)
        3. Overdue cards (past their due date)
        4. Due today cards

        Args:
            deck_id (int): Deck ID
            limit (int, optional): Maximum number of cards to return

        Returns:
            list: Cards due for review, in priority order
        """
        now = datetime.utcnow()

        # Get all cards that are due for review
        due_cards = Flashcard.query.filter(
            and_(
                Flashcard.deck_id == deck_id,
                Flashcard.next_review_date <= now
            )
        ).all()

        # Sort by priority
        def get_priority(card):
            # Priority 0: Failed cards (studied but repetitions = 0)
            if card.times_studied > 0 and card.repetitions == 0:
                return (0, card.next_review_date)

            # Priority 1: New cards (never studied)
            elif card.learning_state == 'new':
                return (1, card.created_at)

            # Priority 2: Review cards (by due date, then by difficulty)
            else:
                return (2, card.next_review_date, card.ease_factor)

        due_cards.sort(key=get_priority)

        if limit:
            due_cards = due_cards[:limit]

        return due_cards

    @classmethod
    def get_new_cards(cls, deck_id, limit=None):
        """Get cards that have never been studied"""
        query = Flashcard.query.filter(
            and_(
                Flashcard.deck_id == deck_id,
                Flashcard.learning_state == 'new'
            )
        ).order_by(Flashcard.created_at)

        if limit:
            query = query.limit(limit)

        return query.all()

    @classmethod
    def get_learning_cards(cls, deck_id):
        """Get cards currently in learning phase (repetitions < 2)"""
        return Flashcard.query.filter(
            and_(
                Flashcard.deck_id == deck_id,
                Flashcard.learning_state == 'learning'
            )
        ).order_by(Flashcard.next_review_date).all()

    @classmethod
    def get_review_cards(cls, deck_id):
        """Get cards in review phase (repetitions >= 2)"""
        return Flashcard.query.filter(
            and_(
                Flashcard.deck_id == deck_id,
                Flashcard.learning_state == 'review'
            )
        ).order_by(Flashcard.next_review_date).all()

    @classmethod
    def get_mastered_cards(cls, deck_id):
        """Get mastered cards (interval > 21 days)"""
        return Flashcard.query.filter(
            and_(
                Flashcard.deck_id == deck_id,
                Flashcard.learning_state == 'mastered'
            )
        ).all()

    # ========== STUDY RECORDING METHODS ==========

    @classmethod
    def record_sm2_review(cls, flashcard_id, quality):
        """
        Record a review using SM-2 algorithm with quality rating

        Args:
            flashcard_id (int): ID of the flashcard
            quality (int): Quality rating (0-5)
                5 = Perfect recall
                4 = Correct after hesitation
                3 = Correct with difficulty
                2 = Incorrect, seemed familiar
                1 = Incorrect, recognized
                0 = Complete blackout

        Returns:
            dict: Updated card information including next review date
        """
        flashcard = cls.get_by_id(flashcard_id)
        if not flashcard:
            return None

        result = flashcard.process_sm2_review(quality)
        flashcard.save()

        return {
            'flashcard_id': flashcard_id,
            'quality': quality,
            **result
        }

    @classmethod
    def record_study_result(cls, flashcard_id, correct, confidence='medium'):
        """
        Record study result (BACKWARD COMPATIBLE METHOD)

        Converts boolean correct/incorrect to SM-2 quality rating.
        Use this method to maintain compatibility with existing code.

        Args:
            flashcard_id (int): ID of the flashcard
            correct (bool): Whether answer was correct
            confidence (str): Confidence level ('low', 'medium', 'high')

        Returns:
            Flashcard: Updated flashcard object
        """
        flashcard = cls.get_by_id(flashcard_id)
        if not flashcard:
            return None

        # Convert boolean to quality rating
        quality = flashcard.get_quality_from_boolean(correct, confidence)

        # Use SM-2 algorithm
        flashcard.process_sm2_review(quality)
        flashcard.save()

        return flashcard

    # ========== LEGACY STUDY METHODS (Backward Compatible) ==========

    @classmethod
    def get_study_cards(cls, deck_id, study_mode='sm2', limit=None):
        """
        Get cards for study session based on study mode

        Args:
            deck_id (int): Deck ID
            study_mode (str): Study mode selection
                'sm2' or 'spaced' or 'due' = Spaced repetition (RECOMMENDED)
                'random' = Random shuffle
                'difficulty_asc' = Easiest first
                'difficulty_desc' = Hardest first
                'accuracy_asc' = Worst accuracy first
                'accuracy_desc' = Best accuracy first
                'least_studied' = Least studied first
                'newest' = Newest cards first
                'oldest' = Oldest cards first
            limit (int, optional): Maximum cards to return

        Returns:
            list: Cards for study session
        """
        # SM-2 SPACED REPETITION MODE (Recommended!)
        if study_mode in ['sm2', 'spaced', 'due']:
            return cls.get_due_cards(deck_id, limit)

        # LEGACY MODES (for backward compatibility)
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
    def get_cards_needing_review(cls, deck_id):
        """
        Get cards that need practice (LEGACY METHOD)
        Now returns due cards using SM-2 algorithm
        """
        return cls.get_due_cards(deck_id)

    @classmethod
    def get_next_card_for_study(cls, deck_id, current_card_id=None):
        """Get the next card for study using SM-2 priority"""
        due_cards = cls.get_due_cards(deck_id)

        if not due_cards:
            return None

        if current_card_id:
            # Try to find the next card after current
            try:
                current_index = next(i for i, card in enumerate(due_cards) if card.id == current_card_id)
                if current_index < len(due_cards) - 1:
                    return due_cards[current_index + 1]
            except StopIteration:
                pass

        # Return first due card
        return due_cards[0] if due_cards else None

    # ========== STATISTICS & ANALYTICS ==========

    @classmethod
    def get_study_statistics(cls, deck_id):
        """
        Get comprehensive study statistics for a deck

        Returns:
            dict: Complete statistics including SM-2 metrics
        """
        cards = cls.get_deck_cards(deck_id)

        if not cards:
            return {
                'total_cards': 0,
                'new_cards': 0,
                'learning_cards': 0,
                'review_cards': 0,
                'mastered_cards': 0,
                'due_today': 0,
                'studied_cards': 0,
                'unstudied_cards': 0,
                'avg_accuracy': 0,
                'avg_ease_factor': 0,
                'total_study_sessions': 0,
                'retention_rate': 0,
                'cards_needing_review': 0
            }

        total_cards = len(cards)
        studied_cards = len([c for c in cards if c.times_studied > 0])
        unstudied_cards = total_cards - studied_cards

        # SM-2 specific statistics
        new_cards = len([c for c in cards if c.learning_state == 'new'])
        learning_cards = len([c for c in cards if c.learning_state == 'learning'])
        review_cards = len([c for c in cards if c.learning_state == 'review'])
        mastered_cards = len([c for c in cards if c.learning_state == 'mastered'])
        due_today = len([c for c in cards if c.is_due_for_review()])

        # Accuracy statistics
        total_correct = sum(c.times_correct for c in cards)
        total_studies = sum(c.times_studied for c in cards)
        avg_accuracy = (total_correct / total_studies * 100) if total_studies > 0 else 0

        # Ease factor average (for studied cards only)
        studied_card_list = [c for c in cards if c.times_studied > 0]
        avg_ease_factor = (sum(c.ease_factor for c in studied_card_list) / len(studied_card_list)) if studied_card_list else 2.5

        # Retention rate (percentage of cards with ease factor >= 2.5)
        retention_rate = len([c for c in studied_card_list if c.ease_factor >= 2.5]) / len(studied_card_list) * 100 if studied_card_list else 0

        return {
            'total_cards': total_cards,
            'new_cards': new_cards,
            'learning_cards': learning_cards,
            'review_cards': review_cards,
            'mastered_cards': mastered_cards,
            'due_today': due_today,
            'studied_cards': studied_cards,
            'unstudied_cards': unstudied_cards,
            'avg_accuracy': round(avg_accuracy, 1),
            'avg_ease_factor': round(avg_ease_factor, 2),
            'total_study_sessions': total_studies,
            'retention_rate': round(retention_rate, 1),
            'cards_needing_review': due_today  # Legacy compatibility
        }

    @classmethod
    def get_upcoming_reviews(cls, deck_id, days=7):
        """
        Get forecast of upcoming reviews for next N days

        Args:
            deck_id (int): Deck ID
            days (int): Number of days to forecast (default: 7)

        Returns:
            list: Daily review counts
                [{'date': date, 'count': int}, ...]
        """
        cards = cls.get_deck_cards(deck_id)
        forecast = []

        for day_offset in range(days):
            target_date = datetime.utcnow() + timedelta(days=day_offset)
            start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = start_of_day + timedelta(days=1)

            due_count = len([
                c for c in cards
                if start_of_day <= c.next_review_date < end_of_day
            ])

            forecast.append({
                'date': start_of_day.date(),
                'count': due_count
            })

        return forecast

    @classmethod
    def get_card_health_score(cls, flashcard):
        """
        Calculate a "health score" for a card (0-100)

        Based on ease factor, accuracy, and learning state.
        Higher score = better retention.

        Args:
            flashcard (Flashcard): The flashcard to evaluate

        Returns:
            float: Health score (0-100)
        """
        if flashcard.times_studied == 0:
            return 50  # Neutral for new cards

        # Base score from ease factor (1.3-3.0 mapped to 0-50)
        ease_score = ((flashcard.ease_factor - 1.3) / (3.0 - 1.3)) * 50

        # Accuracy score (0-100 mapped to 0-50)
        accuracy_score = flashcard.get_accuracy() * 0.5

        # Bonus for mastered cards
        state_bonus = 10 if flashcard.learning_state == 'mastered' else 0

        return min(100, max(0, ease_score + accuracy_score + state_bonus))

    # ========== UTILITY METHODS ==========

    @classmethod
    def reset_card_progress(cls, flashcard_id):
        """
        Reset a card's SM-2 progress (start over)

        Useful for cards that need to be re-learned from scratch.

        Args:
            flashcard_id (int): ID of the flashcard

        Returns:
            Flashcard: Updated flashcard object
        """
        flashcard = cls.get_by_id(flashcard_id)
        if not flashcard:
            return None

        flashcard.ease_factor = 2.5
        flashcard.interval = 0
        flashcard.repetitions = 0
        flashcard.next_review_date = datetime.utcnow()
        flashcard.learning_state = 'new'
        flashcard.save()

        return flashcard
