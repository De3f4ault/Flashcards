from abc import ABC, abstractmethod
from typing import List, Dict, Optional


class BaseAIProvider(ABC):
    """
    Abstract base class for AI providers
    All AI providers must implement these methods
    """

    @abstractmethod
    def generate_flashcards(self, topic: str, count: int, difficulty: str, additional_context: str = None) -> List[Dict[str, str]]:
        """
        Generate flashcards from a topic

        Args:
            topic: Subject or topic description
            count: Number of cards to generate
            difficulty: 'easy', 'medium', 'hard'
            additional_context: Optional additional instructions

        Returns:
            List of dicts: [{'front': '...', 'back': '...'}, ...]
        """
        pass

    @abstractmethod
    def enhance_card(self, front_text: str, back_text: str, enhancement_type: str = 'clarity') -> Dict[str, any]:
        """
        Improve existing flashcard content

        Args:
            front_text: Current front of card
            back_text: Current back of card
            enhancement_type: 'clarity', 'examples', 'simplify', 'detail'

        Returns:
            Dict: {
                'front': 'improved front text',
                'back': 'improved back text',
                'suggestions': ['suggestion 1', 'suggestion 2']
            }
        """
        pass

    @abstractmethod
    def generate_hint(self, card_front: str, card_back: str, previous_attempts: int = 0) -> str:
        """
        Generate a contextual hint without revealing the answer

        Args:
            card_front: Question/prompt on front of card
            card_back: Answer on back of card
            previous_attempts: Number of times user has tried

        Returns:
            String: Hint text
        """
        pass

    @abstractmethod
    def suggest_tags(self, card_front: str, card_back: str, max_tags: int = 3) -> List[str]:
        """
        Suggest relevant tags for a flashcard

        Args:
            card_front: Front of card
            card_back: Back of card
            max_tags: Maximum number of tags to suggest

        Returns:
            List of tag strings
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the provider is properly configured and available

        Returns:
            Boolean: True if provider can be used
        """
        pass

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text (rough approximation)

        Args:
            text: Input text

        Returns:
            Estimated token count
        """
        # Rough estimation: ~4 characters per token
        return len(text) // 4

    def validate_card_response(self, cards: List[Dict]) -> List[Dict]:
        """
        Validate and clean card responses from AI

        Args:
            cards: Raw card list from AI

        Returns:
            Validated and cleaned card list
        """
        validated = []

        for card in cards:
            if not isinstance(card, dict):
                continue

            front = card.get('front', '').strip()
            back = card.get('back', '').strip()

            # Must have both front and back
            if not front or not back:
                continue

            # Reasonable length limits
            if len(front) > 500 or len(back) > 2000:
                continue

            validated.append({
                'front': front,
                'back': back
            })

        return validated
