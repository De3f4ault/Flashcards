import json
import google.generativeai as genai
from typing import List, Dict, Optional
from app.services.ai_providers.base import BaseAIProvider
from app.services.ai_prompts import PROMPTS
from app.config import Config


class GeminiProvider(BaseAIProvider):
    """Google Gemini AI Provider Implementation"""

    def __init__(self):
        """Initialize Gemini with API key"""
        if not Config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not configured")

        genai.configure(api_key=Config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-2.5-flash')

        # Generation config for consistent responses
        self.generation_config = {
            'temperature': 0.7,
            'top_p': 0.95,
            'top_k': 40,
            'max_output_tokens': 2048,
        }

    def is_available(self) -> bool:
        """Check if Gemini is properly configured"""
        try:
            return bool(Config.GEMINI_API_KEY)
        except:
            return False

    def generate_flashcards(self, topic: str, count: int, difficulty: str, additional_context: str = None) -> List[Dict[str, str]]:
        """Generate flashcards using Gemini"""
        try:
            # Build the prompt
            prompt = PROMPTS['generate_cards'].format(
                topic=topic,
                count=count,
                difficulty=difficulty,
                additional_context=additional_context or "No additional context provided."
            )

            # Call Gemini API
            response = self.model.generate_content(
                prompt,
                generation_config=self.generation_config
            )

            # Parse the response
            cards = self._parse_json_response(response.text)

            # Validate cards
            validated_cards = self.validate_card_response(cards)

            return validated_cards[:count]  # Limit to requested count

        except Exception as e:
            print(f"Gemini generate_flashcards error: {e}")
            return []

    def enhance_card(self, front_text: str, back_text: str, enhancement_type: str = 'clarity') -> Dict[str, any]:
        """Enhance existing flashcard using Gemini"""
        try:
            prompt = PROMPTS['enhance_card'].format(
                front_text=front_text,
                back_text=back_text,
                enhancement_type=enhancement_type
            )

            response = self.model.generate_content(
                prompt,
                generation_config=self.generation_config
            )

            result = self._parse_json_response(response.text)

            # Validate response structure
            if not isinstance(result, dict):
                return None

            if 'front' not in result or 'back' not in result:
                return None

            return {
                'front': result.get('front', front_text),
                'back': result.get('back', back_text),
                'suggestions': result.get('suggestions', [])
            }

        except Exception as e:
            print(f"Gemini enhance_card error: {e}")
            return None

    def generate_hint(self, card_front: str, card_back: str, previous_attempts: int = 0) -> str:
        """Generate hint using Gemini"""
        try:
            prompt = PROMPTS['generate_hint'].format(
                card_front=card_front,
                card_back=card_back,
                previous_attempts=previous_attempts
            )

            response = self.model.generate_content(
                prompt,
                generation_config={
                    **self.generation_config,
                    'temperature': 0.5,  # Lower temperature for more consistent hints
                }
            )

            hint = response.text.strip()

            # Remove quotes if present
            if hint.startswith('"') and hint.endswith('"'):
                hint = hint[1:-1]

            return hint if hint else "Try thinking about the key concepts involved."

        except Exception as e:
            print(f"Gemini generate_hint error: {e}")
            return "Unable to generate hint at this time."

    def suggest_tags(self, card_front: str, card_back: str, max_tags: int = 3) -> List[str]:
        """Suggest tags using Gemini"""
        try:
            prompt = PROMPTS['suggest_tags'].format(
                card_front=card_front,
                card_back=card_back,
                max_tags=max_tags
            )

            response = self.model.generate_content(
                prompt,
                generation_config={
                    **self.generation_config,
                    'temperature': 0.4,  # Lower temperature for consistent tagging
                }
            )

            # Try to parse as JSON array first
            tags = self._parse_json_response(response.text)

            if isinstance(tags, list):
                # Clean and validate tags
                clean_tags = []
                for tag in tags[:max_tags]:
                    if isinstance(tag, str):
                        tag = tag.strip().lower()
                        if tag and len(tag) <= 30:
                            clean_tags.append(tag)
                return clean_tags

            # Fallback: parse comma-separated or line-separated
            text = response.text.strip()
            if ',' in text:
                tags = [t.strip().lower() for t in text.split(',')]
            else:
                tags = [t.strip().lower() for t in text.split('\n')]

            return [t for t in tags if t and len(t) <= 30][:max_tags]

        except Exception as e:
            print(f"Gemini suggest_tags error: {e}")
            return []

    def _parse_json_response(self, text: str):
        """
        Parse JSON from Gemini response
        Handles cases where JSON is wrapped in markdown code blocks
        """
        try:
            # Remove markdown code blocks if present
            if '```json' in text:
                text = text.split('```json')[1].split('```')[0]
            elif '```' in text:
                text = text.split('```')[1].split('```')[0]

            # Clean up the text
            text = text.strip()

            # Parse JSON
            return json.loads(text)

        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            print(f"Response text: {text[:200]}...")
            return None
        except Exception as e:
            print(f"Parse error: {e}")
            return None
