"""
Gemini AI Provider
Handles all interactions with Google's Gemini AI
"""

import google.generativeai as genai
from app.config import Config
from app.services.ai_providers.base import BaseAIProvider
from app.services.ai_prompts import get_prompt
import json
import re


class GeminiProvider(BaseAIProvider):
    """Google Gemini AI Provider Implementation"""

    def __init__(self):
        super().__init__()
        if Config.GEMINI_API_KEY:
            genai.configure(api_key=Config.GEMINI_API_KEY)
            # Use Pro model for better handling of complex content
            self.model = genai.GenerativeModel(
                "gemini-2.0-flash-exp",
                generation_config={
                    "temperature": 0.7,
                    "top_p": 0.95,
                    "top_k": 40,
                    "max_output_tokens": 8192,  # Increased for long responses
                }
            )
        else:
            self.model = None

    def is_available(self) -> bool:
        """Check if Gemini is configured and available"""
        return Config.GEMINI_API_KEY is not None and self.model is not None

    def generate_flashcards(self, topic, count, difficulty, additional_context=None):
        """Generate flashcards using Gemini"""
        if not self.is_available():
            return []

        try:
            # Build prompt
            prompt = get_prompt("generate_cards").format(
                count=count,
                topic=topic,
                difficulty=difficulty,
                additional_context=additional_context
                or "No additional context provided",
            )

            # Generate
            response = self.model.generate_content(prompt)

            if not response or not response.text:
                return []

            # Parse JSON response
            cards = self._parse_flashcard_response(response.text)
            return cards

        except Exception as e:
            print(f"Gemini generate_flashcards error: {e}")
            return []

    def enhance_card(self, front_text, back_text, enhancement_type):
        """Enhance flashcard content"""
        if not self.is_available():
            return None

        try:
            prompt = get_prompt("enhance_card").format(
                front_text=front_text,
                back_text=back_text,
                enhancement_type=enhancement_type,
            )

            response = self.model.generate_content(prompt)

            if not response or not response.text:
                return None

            # Parse JSON response
            result = self._parse_json_response(response.text)
            return result

        except Exception as e:
            print(f"Gemini enhance_card error: {e}")
            return None

    def generate_hint(self, card_front, card_back, previous_attempts):
        """Generate hint for flashcard"""
        if not self.is_available():
            return "Hints unavailable"

        try:
            prompt = get_prompt("generate_hint").format(
                card_front=card_front,
                card_back=card_back,
                previous_attempts=previous_attempts,
            )

            response = self.model.generate_content(prompt)

            if not response or not response.text:
                return "Unable to generate hint"

            return response.text.strip()

        except Exception as e:
            print(f"Gemini generate_hint error: {e}")
            return "Hint generation failed"

    def suggest_tags(self, card_front, card_back, max_tags):
        """Suggest tags for flashcard"""
        if not self.is_available():
            return []

        try:
            prompt = get_prompt("suggest_tags").format(
                card_front=card_front, card_back=card_back, max_tags=max_tags
            )

            response = self.model.generate_content(prompt)

            if not response or not response.text:
                return []

            # Parse JSON array response
            tags = self._parse_json_response(response.text)
            return tags if isinstance(tags, list) else []

        except Exception as e:
            print(f"Gemini suggest_tags error: {e}")
            return []

    def generate_text(self, prompt: str, max_retries: int = 3) -> str:
        """
        General text generation method for custom prompts
        Used by MC generation service

        Args:
            prompt: The full prompt text
            max_retries: Number of retry attempts for failed generations

        Returns:
            Generated text response
        """
        if not self.is_available():
            return ""

        last_error = None

        for attempt in range(max_retries + 1):
            try:
                response = self.model.generate_content(prompt)

                if not response or not response.text:
                    if attempt < max_retries:
                        print(f"Empty response, retrying... (attempt {attempt + 1}/{max_retries})")
                        continue
                    return ""

                response_text = response.text.strip()

                # For large responses, be more lenient with validation
                if len(response_text) > 5000:
                    # Just check basic structure for large responses
                    if self._has_basic_json_structure(response_text):
                        return response_text
                    else:
                        print(f"Large response with invalid JSON structure, retrying... (attempt {attempt + 1}/{max_retries})")
                        if attempt < max_retries:
                            continue
                        return response_text  # Return anyway on last attempt
                else:
                    # Full validation for smaller responses
                    if self._is_valid_json_structure(response_text):
                        return response_text
                    else:
                        print(f"Invalid JSON structure, retrying... (attempt {attempt + 1}/{max_retries})")
                        if attempt < max_retries:
                            continue
                        return response_text  # Return anyway on last attempt

            except Exception as e:
                last_error = e
                print(f"Gemini generate_text error (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries:
                    continue
                # On last attempt, raise the error so it can be caught upstream
                print(f"All retry attempts exhausted. Last error: {e}")
                return ""

        return ""

    def generate_chat_response(self, user_message: str, conversation_history: list = None, system_prompt: str = None) -> dict:
        """
        Generate a chat response without document context.

        Args:
            user_message: The user's message
            conversation_history: List of previous messages in Gemini format
            system_prompt: System instructions for the AI

        Returns:
            dict: Response with 'text', 'tokens_used', 'model'
        """
        if not self.is_available():
            return {
                'text': 'AI service is not available',
                'tokens_used': 0,
                'model': 'none'
            }

        try:
            # Combine system prompt with user message
            if system_prompt:
                full_prompt = f"{system_prompt}\n\nUser: {user_message}"
            else:
                full_prompt = user_message

            # Start a chat session if there's conversation history
            if conversation_history:
                chat = self.model.start_chat(history=conversation_history)
                response = chat.send_message(full_prompt)
            else:
                response = self.model.generate_content(full_prompt)

            if not response or not response.text:
                return {
                    'text': 'Unable to generate response',
                    'tokens_used': 0,
                    'model': 'gemini-2.0-flash-exp'
                }

            # Estimate tokens (rough approximation)
            tokens_used = self.estimate_tokens(full_prompt + response.text)

            return {
                'text': response.text.strip(),
                'tokens_used': tokens_used,
                'model': 'gemini-2.0-flash-exp'
            }

        except Exception as e:
            print(f"Gemini chat error: {e}")
            return {
                'text': f'Error generating response: {str(e)}',
                'tokens_used': 0,
                'model': 'gemini-2.0-flash-exp',
                'error': str(e)
            }

    def generate_with_file(self, prompt: str, file_uri: str, conversation_history: list = None, system_prompt: str = None) -> dict:
        """
        Generate a chat response with document context using Gemini File API.

        Args:
            prompt: The user's message
            file_uri: Gemini File API URI for the uploaded document
            conversation_history: List of previous messages in Gemini format
            system_prompt: System instructions for the AI

        Returns:
            dict: Response with 'text', 'tokens_used', 'model'
        """
        if not self.is_available():
            return {
                'text': 'AI service is not available',
                'tokens_used': 0,
                'model': 'none'
            }

        try:
            # Get the file object from Gemini
            file = genai.get_file(name=file_uri.split('/')[-1])

            # Combine system prompt with user message
            if system_prompt:
                full_prompt = f"{system_prompt}\n\nUser: {prompt}"
            else:
                full_prompt = prompt

            # Build the content with file reference
            if conversation_history:
                # For chat with history, include file in the conversation
                chat = self.model.start_chat(history=conversation_history)
                response = chat.send_message([file, full_prompt])
            else:
                # For first message, include file directly
                response = self.model.generate_content([file, full_prompt])

            if not response or not response.text:
                return {
                    'text': 'Unable to generate response',
                    'tokens_used': 0,
                    'model': 'gemini-2.0-flash-exp'
                }

            # Estimate tokens (rough approximation)
            tokens_used = self.estimate_tokens(full_prompt + response.text)

            return {
                'text': response.text.strip(),
                'tokens_used': tokens_used,
                'model': 'gemini-2.0-flash-exp'
            }

        except Exception as e:
            print(f"Gemini file chat error: {e}")
            return {
                'text': f'Error accessing document or generating response: {str(e)}',
                'tokens_used': 0,
                'model': 'gemini-2.0-flash-exp',
                'error': str(e)
            }

    def estimate_tokens(self, text):
        """Rough token estimation (Gemini uses different tokenization)"""
        # Rough approximation: ~4 characters per token
        return len(text) // 4

    def _has_basic_json_structure(self, text: str) -> bool:
        """
        Quick check for basic JSON structure without full parsing
        Used for large responses to avoid timeout
        """
        if not text:
            return False

        # Extract JSON from markdown if present
        json_text = self._extract_json_from_markdown(text)

        # Basic checks
        if not json_text.strip():
            return False

        # Check for balanced braces and brackets
        if json_text.count('{') != json_text.count('}'):
            return False
        if json_text.count('[') != json_text.count(']'):
            return False

        # Check that it starts and ends appropriately
        json_text = json_text.strip()
        if json_text.startswith('{') and json_text.endswith('}'):
            return True
        if json_text.startswith('[') and json_text.endswith(']'):
            return True

        return False

    def _is_valid_json_structure(self, text: str) -> bool:
        """
        Full validation to check if text is valid JSON
        """
        if not text:
            return False

        # Extract JSON from markdown if present
        json_text = self._extract_json_from_markdown(text)

        # Basic structure checks first (fast)
        if not self._has_basic_json_structure(json_text):
            return False

        # Check for proper string termination (no unterminated quotes)
        in_string = False
        escaped = False
        for char in json_text:
            if char == '\\' and not escaped:
                escaped = True
                continue
            if char == '"' and not escaped:
                in_string = not in_string
            escaped = False

        if in_string:  # Unterminated string
            return False

        # Try to actually parse it
        try:
            json.loads(json_text)
            return True
        except:
            return False

    def _extract_json_from_markdown(self, text: str) -> str:
        """Extract JSON from markdown code blocks"""
        # Remove markdown code blocks
        if "```json" in text:
            match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
            if match:
                return match.group(1)
        elif "```" in text:
            match = re.search(r'```\s*(.*?)\s*```', text, re.DOTALL)
            if match:
                return match.group(1)

        return text.strip()

    def _parse_flashcard_response(self, response_text):
        """Parse flashcard JSON response"""
        try:
            json_text = self._extract_json_from_markdown(response_text)
            data = json.loads(json_text)

            # Extract cards array
            if isinstance(data, list):
                cards = data
            elif isinstance(data, dict) and "cards" in data:
                cards = data["cards"]
            else:
                return []

            # Validate cards
            valid_cards = []
            for card in cards:
                if isinstance(card, dict) and "front" in card and "back" in card:
                    valid_cards.append({"front": card["front"], "back": card["back"]})

            return valid_cards

        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            print(f"Response was: {response_text[:500]}")
            return []
        except Exception as e:
            print(f"Parse flashcard error: {e}")
            return []

    def _parse_json_response(self, response_text):
        """General JSON parsing helper with robust error handling"""
        try:
            json_text = self._extract_json_from_markdown(response_text)
            return json.loads(json_text)

        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            print(f"Response was: {response_text[:500]}")
            return None
        except Exception as e:
            print(f"General parse error: {e}")
            return None
