"""
Main AI Service - Orchestrates all AI operations
Provides a clean interface between the app and AI providers
"""

from typing import List, Dict, Optional
from app.config import Config
from app.models.ai_usage import AIUsage
from app.services.ai_providers import GeminiProvider
from app.extensions import db


class AIService:
    """
    Main AI service class
    Handles all AI operations with provider abstraction
    """

    @staticmethod
    def _get_provider():
        """Get the configured AI provider"""
        provider_name = Config.AI_PROVIDER.lower()

        if provider_name == 'gemini':
            return GeminiProvider()
        # Future: Add OpenAI, Claude, etc.
        else:
            raise ValueError(f"Unknown AI provider: {provider_name}")

    @staticmethod
    def is_available(user_id: int = None) -> bool:
        """
        Check if AI services are available

        Args:
            user_id: Optional user ID to check user-specific availability

        Returns:
            Boolean indicating if AI is available
        """
        # Check global AI enabled flag
        if not Config.AI_ENABLED:
            return False

        # Check provider configuration
        try:
            provider = AIService._get_provider()
            if not provider.is_available():
                return False
        except:
            return False

        # Check user-specific availability if user_id provided
        if user_id:
            from app.models.user import User
            user = User.query.get(user_id)

            if not user or not user.ai_enabled:
                return False

            # Check rate limiting
            if AIService._is_rate_limited(user_id):
                return False

        return True

    @staticmethod
    def _is_rate_limited(user_id: int) -> bool:
        """Check if user has exceeded rate limit"""
        request_count = AIUsage.get_hourly_request_count(user_id)
        return request_count >= Config.AI_RATE_LIMIT_PER_HOUR

    @staticmethod
    def generate_flashcards(
        topic: str,
        count: int = 10,
        difficulty: str = 'medium',
        user_id: int = None,
        additional_context: str = None
    ) -> List[Dict[str, str]]:
        """
        Generate flashcards from a topic using AI

        Args:
            topic: Subject or topic to generate cards about
            count: Number of cards to generate (max: AI_MAX_CARDS_PER_GENERATION)
            difficulty: 'easy', 'medium', or 'hard'
            user_id: User ID for tracking and rate limiting
            additional_context: Optional additional instructions

        Returns:
            List of card dicts: [{'front': '...', 'back': '...'}, ...]
        """
        # Validation
        if not Config.AI_CARD_GENERATION_ENABLED:
            return []

        if not AIService.is_available(user_id):
            return []

        # Limit count
        count = min(count, Config.AI_MAX_CARDS_PER_GENERATION)

        # Validate difficulty
        if difficulty not in ['easy', 'medium', 'hard']:
            difficulty = 'medium'

        try:
            provider = AIService._get_provider()
            cards = provider.generate_flashcards(topic, count, difficulty, additional_context)

            # Log success
            if user_id:
                AIUsage.log_usage(
                    user_id=user_id,
                    operation_type='generate_cards',
                    tokens_used=provider.estimate_tokens(topic) * count,
                    success=True
                )

            return cards

        except Exception as e:
            # Log failure
            if user_id:
                AIUsage.log_usage(
                    user_id=user_id,
                    operation_type='generate_cards',
                    success=False,
                    error_message=str(e)
                )

            print(f"AI generate_flashcards error: {e}")
            return []

    @staticmethod
    def enhance_card(
        front_text: str,
        back_text: str,
        enhancement_type: str = 'clarity',
        user_id: int = None
    ) -> Optional[Dict[str, any]]:
        """
        Enhance existing flashcard content using AI

        Args:
            front_text: Current front text
            back_text: Current back text
            enhancement_type: 'clarity', 'examples', 'simplify', 'detail'
            user_id: User ID for tracking

        Returns:
            Dict with enhanced content or None if failed
        """
        if not Config.AI_CARD_ENHANCEMENT_ENABLED:
            return None

        if not AIService.is_available(user_id):
            return None

        try:
            provider = AIService._get_provider()
            result = provider.enhance_card(front_text, back_text, enhancement_type)

            # Log usage
            if user_id:
                AIUsage.log_usage(
                    user_id=user_id,
                    operation_type='enhance_card',
                    tokens_used=provider.estimate_tokens(front_text + back_text),
                    success=result is not None
                )

            return result

        except Exception as e:
            if user_id:
                AIUsage.log_usage(
                    user_id=user_id,
                    operation_type='enhance_card',
                    success=False,
                    error_message=str(e)
                )

            print(f"AI enhance_card error: {e}")
            return None

    @staticmethod
    def generate_hint(
        card_front: str,
        card_back: str,
        previous_attempts: int = 0,
        user_id: int = None
    ) -> str:
        """
        Generate a helpful hint for a flashcard

        Args:
            card_front: Question text
            card_back: Answer text
            previous_attempts: How many times user has tried
            user_id: User ID for tracking

        Returns:
            Hint text string
        """
        if not Config.AI_HINT_GENERATION_ENABLED:
            return "Hints are not available at this time."

        if not AIService.is_available(user_id):
            return "AI hints are not available."

        try:
            provider = AIService._get_provider()
            hint = provider.generate_hint(card_front, card_back, previous_attempts)

            # Log usage
            if user_id:
                AIUsage.log_usage(
                    user_id=user_id,
                    operation_type='hint_generation',
                    tokens_used=provider.estimate_tokens(card_front + card_back),
                    success=bool(hint)
                )

            return hint

        except Exception as e:
            if user_id:
                AIUsage.log_usage(
                    user_id=user_id,
                    operation_type='hint_generation',
                    success=False,
                    error_message=str(e)
                )

            print(f"AI generate_hint error: {e}")
            return "Unable to generate hint at this time."

    @staticmethod
    def suggest_tags(
        card_front: str,
        card_back: str,
        max_tags: int = 3,
        user_id: int = None
    ) -> List[str]:
        """
        Suggest relevant tags for a flashcard

        Args:
            card_front: Front of card
            card_back: Back of card
            max_tags: Maximum number of tags to return
            user_id: User ID for tracking

        Returns:
            List of tag strings
        """
        if not Config.AI_TAG_SUGGESTIONS_ENABLED:
            return []

        if not AIService.is_available(user_id):
            return []

        try:
            provider = AIService._get_provider()
            tags = provider.suggest_tags(card_front, card_back, max_tags)

            # Log usage
            if user_id:
                AIUsage.log_usage(
                    user_id=user_id,
                    operation_type='tag_suggestion',
                    tokens_used=provider.estimate_tokens(card_front + card_back),
                    success=bool(tags)
                )

            return tags

        except Exception as e:
            if user_id:
                AIUsage.log_usage(
                    user_id=user_id,
                    operation_type='tag_suggestion',
                    success=False,
                    error_message=str(e)
                )

            print(f"AI suggest_tags error: {e}")
            return []

    @staticmethod
    def get_user_stats(user_id: int, days: int = 30) -> Dict:
        """
        Get AI usage statistics for a user

        Args:
            user_id: User ID
            days: Number of days to look back

        Returns:
            Dict with usage statistics
        """
        from app.models.user import User

        user = User.query.get(user_id)
        if not user:
            return {}

        usage_stats = AIUsage.get_user_usage_stats(user_id, days)

        return {
            'ai_enabled': user.ai_enabled,
            'usage_by_operation': usage_stats,
            'total_requests': sum(op['count'] for op in usage_stats.values()),
            'rate_limit_status': {
                'current_hour_requests': AIUsage.get_hourly_request_count(user_id),
                'limit': Config.AI_RATE_LIMIT_PER_HOUR,
                'is_limited': AIService._is_rate_limited(user_id)
            }
        }
