"""
MC Generator Service
Handles generation of multiple choice questions using AI
"""

from app.models import MCCard
from app.services.ai_providers.gemini import GeminiProvider
from app.services.ai_providers.mc_prompts import get_mc_generation_prompt  # FIXED: Changed from build_mc_generation_prompt
from app.extensions import db
import json
import re

# Try to import AIUsage if available
try:
    from app.models import AIUsage
    HAS_AI_USAGE = True
except ImportError:
    HAS_AI_USAGE = False


class MCGeneratorService:
    """Service for generating MC questions"""

    @staticmethod
    def generate_questions(topic, count, difficulty, subject_area, deck_id, user_id, additional_context=None):
        """
        Generate multiple choice questions using AI

        Args:
            topic: Main topic for questions
            count: Number of questions to generate
            difficulty: Difficulty level (1-5)
            subject_area: Subject category
            deck_id: ID of deck to associate with
            user_id: ID of requesting user
            additional_context: Optional additional instructions

        Returns:
            dict with success, questions list, and metadata
        """
        try:
            # Get AI provider
            ai_provider = GeminiProvider()

            if not ai_provider.is_available():
                return {
                    'success': False,
                    'error': 'AI provider not available',
                    'questions': [],
                    'generated_count': 0
                }

            # Build prompt - FIXED: Changed function name
            prompt = get_mc_generation_prompt(
                topic=topic,
                count=count,
                difficulty=difficulty,
                subject_area=subject_area,
                additional_context=additional_context
            )

            # Generate with retry logic
            response_text = ai_provider.generate_text(prompt, max_retries=2)

            if not response_text:
                return {
                    'success': False,
                    'error': 'AI returned empty response',
                    'questions': [],
                    'generated_count': 0
                }

            # Parse response into MCCard objects
            questions, parse_errors = MCGeneratorService._parse_mc_response(
                response_text,
                deck_id,
                topic,
                difficulty
            )

            if not questions:
                error_msg = f'Failed to parse AI response. {parse_errors}' if parse_errors else 'No valid questions generated'
                return {
                    'success': False,
                    'error': error_msg,
                    'questions': [],
                    'generated_count': 0,
                    'raw_response': response_text[:500]  # First 500 chars for debugging
                }

            # Log AI usage
            if HAS_AI_USAGE:
                try:
                    tokens_used = ai_provider.estimate_tokens(prompt + response_text)
                    AIUsage.log_usage(
                        user_id=user_id,
                        operation_type='mc_generation',  # FIXED: Changed from 'feature' to 'operation_type'
                        tokens_used=tokens_used,
                        success=True
                        # Removed 'provider' parameter - not supported by AIUsage model
                    )
                except Exception as log_error:
                    print(f"Failed to log AI usage: {log_error}")

            return {
                'success': True,
                'questions': questions,
                'generated_count': len(questions),
                'requested_count': count,
                'parse_warnings': parse_errors if parse_errors else None
            }

        except Exception as e:
            print(f"MC generation error: {str(e)}")
            import traceback
            traceback.print_exc()

            return {
                'success': False,
                'error': f'Generation failed: {str(e)}',
                'questions': [],
                'generated_count': 0
            }

    @staticmethod
    def _parse_mc_response(response_text, deck_id, topic, difficulty):
        """
        Parse AI response into MCCard objects with robust error handling

        Returns:
            tuple: (list of MCCard objects, error messages string or None)
        """
        errors = []

        try:
            # Extract JSON from markdown if present
            json_text = MCGeneratorService._extract_json(response_text)

            if not json_text:
                return [], "No JSON content found in response"

            # Attempt to parse JSON with multiple strategies
            data = None
            parse_error = None

            try:
                data = json.loads(json_text)
            except json.JSONDecodeError as e:
                parse_error = e
                errors.append(f"Initial JSON parse failed at position {e.pos}: {e.msg}")

                # Attempt recovery with multiple strategies
                print("Attempting JSON recovery...")
                data = MCGeneratorService._attempt_json_recovery(json_text)

                if not data:
                    # Last resort: try fixing common issues
                    try:
                        # Remove trailing commas
                        fixed_text = re.sub(r',\s*([}\]])', r'\1', json_text)
                        # Remove comments if any
                        fixed_text = re.sub(r'//.*?\n', '\n', fixed_text)
                        fixed_text = re.sub(r'/\*.*?\*/', '', fixed_text, flags=re.DOTALL)
                        data = json.loads(fixed_text)
                        errors.append("Recovered by fixing common JSON issues")
                    except:
                        return [], f"Could not parse or recover JSON. Error: {parse_error}. Preview: {response_text[:300]}"

            if not data:
                return [], "Failed to extract valid JSON structure"

            # Extract questions array
            questions_data = None
            if isinstance(data, dict):
                questions_data = data.get('questions') or data.get('cards')
            elif isinstance(data, list):
                questions_data = data

            if not questions_data:
                return [], f"No 'questions' array found. Structure: {list(data.keys()) if isinstance(data, dict) else 'list'}"

            if not isinstance(questions_data, list):
                return [], f"'questions' field is not an array. Type: {type(questions_data)}"

            # Parse individual questions
            cards = []
            for idx, q_data in enumerate(questions_data):
                try:
                    card = MCGeneratorService._parse_single_question(
                        q_data, deck_id, topic, difficulty
                    )
                    if card:
                        cards.append(card)
                    else:
                        errors.append(f"Q{idx + 1}: Invalid structure or missing required fields")
                except Exception as e:
                    errors.append(f"Q{idx + 1}: {str(e)}")
                    continue

            if not cards:
                return [], f"No valid questions generated. Errors: {'; '.join(errors)}"

            # Success with possible warnings
            success_msg = f"Generated {len(cards)} cards"
            if len(cards) < len(questions_data):
                success_msg += f" ({len(questions_data) - len(cards)} skipped due to errors)"

            error_msg = '; '.join(errors) if errors else None
            return cards, error_msg

        except Exception as e:
            import traceback
            traceback.print_exc()
            return [], f"Unexpected parse error: {str(e)}"

    @staticmethod
    def _extract_json(text):
        """Extract JSON from text, handling markdown code blocks and malformed responses"""
        # Try markdown JSON block first
        json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if json_match:
            return json_match.group(1).strip()

        # Try generic code block
        code_match = re.search(r'```\s*(.*?)\s*```', text, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()

        # Find first { or [ and last } or ]
        start_brace = text.find('{')
        start_bracket = text.find('[')

        start_pos = -1
        end_pos = -1

        if start_brace != -1 and start_bracket != -1:
            start_pos = min(start_brace, start_bracket)
        elif start_brace != -1:
            start_pos = start_brace
        elif start_bracket != -1:
            start_pos = start_bracket

        if start_pos != -1:
            # Find matching closing bracket
            if text[start_pos] == '{':
                end_pos = text.rfind('}')
            else:
                end_pos = text.rfind(']')

            if end_pos > start_pos:
                return text[start_pos:end_pos + 1].strip()
            return text[start_pos:].strip()

        return text.strip()

    @staticmethod
    def _attempt_json_recovery(json_text):
        """
        Attempt to recover partial/malformed JSON with multiple strategies
        Returns dict or None if recovery fails
        """
        # Strategy 1: Try to fix common JSON issues
        try:
            # Remove trailing commas before closing braces/brackets
            fixed = re.sub(r',\s*([}\]])', r'\1', json_text)
            # Try parsing
            return json.loads(fixed)
        except:
            pass

        # Strategy 2: Find complete question objects
        try:
            # Pattern for complete question with all required fields
            # More flexible pattern that handles multi-line content
            question_pattern = r'\{[^{}]*?"question"\s*:[^{}]*?"choices"\s*:\s*\{[^{}]*?"A"[^{}]*?"B"[^{}]*?"C"[^{}]*?"D"[^{}]*?\}[^{}]*?"correct_answer"\s*:[^{}]*?\}'
            matches = re.findall(question_pattern, json_text, re.DOTALL)

            if matches:
                # Clean up each match
                clean_matches = []
                for match in matches:
                    # Remove trailing commas
                    cleaned = re.sub(r',\s*([}\]])', r'\1', match)
                    try:
                        # Validate individual question
                        json.loads(cleaned)
                        clean_matches.append(cleaned)
                    except:
                        continue

                if clean_matches:
                    # Wrap in questions array
                    recovered = '{"questions": [' + ','.join(clean_matches) + ']}'
                    return json.loads(recovered)
        except Exception as e:
            print(f"Recovery strategy 2 failed: {e}")

        # Strategy 3: Try to extract up to first malformed question
        try:
            # Find questions array start
            array_start = json_text.find('"questions"')
            if array_start == -1:
                array_start = json_text.find('"cards"')

            if array_start != -1:
                # Find the opening bracket after questions key
                bracket_start = json_text.find('[', array_start)
                if bracket_start != -1:
                    # Find complete question objects before error
                    valid_questions = []
                    current_pos = bracket_start + 1
                    brace_count = 0
                    question_start = -1

                    for i, char in enumerate(json_text[current_pos:], current_pos):
                        if char == '{':
                            if brace_count == 0:
                                question_start = i
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0 and question_start != -1:
                                # Found complete question
                                q_text = json_text[question_start:i+1]
                                try:
                                    q_obj = json.loads(q_text)
                                    if 'question' in q_obj and 'choices' in q_obj and 'correct_answer' in q_obj:
                                        valid_questions.append(q_text)
                                except:
                                    pass
                                question_start = -1

                    if valid_questions:
                        recovered = '{"questions": [' + ','.join(valid_questions) + ']}'
                        return json.loads(recovered)
        except Exception as e:
            print(f"Recovery strategy 3 failed: {e}")

        return None

    @staticmethod
    def _parse_single_question(q_data, deck_id, topic, difficulty):
        """
        Parse a single question dict into MCCard object

        Returns:
            MCCard object or None if invalid
        """
        if not isinstance(q_data, dict):
            return None

        # Required fields
        question_text = q_data.get('question')
        choices = q_data.get('choices', {})
        correct_answer = q_data.get('correct_answer')

        if not question_text or not choices or not correct_answer:
            return None

        # Validate choices structure
        required_choices = ['A', 'B', 'C', 'D']
        if not all(choice in choices for choice in required_choices):
            return None

        # Get misconceptions (optional)
        misconceptions = q_data.get('misconceptions', {})

        # Get metadata
        q_difficulty = q_data.get('difficulty', difficulty)
        concept_tags = q_data.get('concept_tags', [])

        # Create MCCard object (not saved to DB yet)
        card = MCCard(
            deck_id=deck_id,
            question_text=question_text,
            choice_a=str(choices['A'])[:500],  # Limit length
            choice_b=str(choices['B'])[:500],
            choice_c=str(choices['C'])[:500],
            choice_d=str(choices['D'])[:500],
            correct_answer=correct_answer.upper(),
            misconception_a=str(misconceptions.get('A', ''))[:500] if misconceptions.get('A') else None,
            misconception_b=str(misconceptions.get('B', ''))[:500] if misconceptions.get('B') else None,
            misconception_c=str(misconceptions.get('C', ''))[:500] if misconceptions.get('C') else None,
            misconception_d=str(misconceptions.get('D', ''))[:500] if misconceptions.get('D') else None,
            difficulty=q_difficulty,
            concept_tags=','.join(concept_tags) if isinstance(concept_tags, list) else str(concept_tags),
            ai_generated=True,
            generation_topic=topic,
            ai_provider='gemini'
        )

        return card

    @staticmethod
    def save_questions(cards):
        """
        Save MCCard objects to database

        Args:
            cards: List of MCCard objects

        Returns:
            dict with success status and count
        """
        try:
            saved_count = 0
            for card in cards:
                db.session.add(card)
                saved_count += 1

            db.session.commit()

            return {
                'success': True,
                'saved_count': saved_count
            }

        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': str(e),
                'saved_count': 0
            }

    @staticmethod
    def regenerate_single_question(card, reason=""):
        """
        Regenerate a single question (not implemented in Phase 1)

        Args:
            card: MCCard to regenerate
            reason: Reason for regeneration

        Returns:
            New MCCard or None
        """
        # Placeholder for Phase 2
        return None

    @staticmethod
    def update_card_manual(card, question_text, choices, correct_answer, misconceptions):
        """
        Manually update an existing MC card

        Args:
            card: MCCard object to update
            question_text: New question text
            choices: Dict with A, B, C, D choices
            correct_answer: Letter of correct answer
            misconceptions: Dict with misconception explanations

        Returns:
            dict with success status
        """
        try:
            card.question_text = question_text
            card.choice_a = choices['A']
            card.choice_b = choices['B']
            card.choice_c = choices['C']
            card.choice_d = choices['D']
            card.correct_answer = correct_answer.upper()
            card.misconception_a = misconceptions.get('A')
            card.misconception_b = misconceptions.get('B')
            card.misconception_c = misconceptions.get('C')
            card.misconception_d = misconceptions.get('D')

            db.session.commit()

            return {'success': True}

        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': str(e)
            }
