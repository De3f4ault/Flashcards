"""
Document QA Service
Handles generation of multiple choice questions from uploaded documents
"""

from app.models import MCCard, Document
from app.services.ai_providers.gemini import GeminiProvider
from app.services.ai_providers.mc_prompts import get_mc_generation_prompt
from app.extensions import db
import json
import re

# Try to import AIUsage if available
try:
    from app.models import AIUsage
    HAS_AI_USAGE = True
except ImportError:
    HAS_AI_USAGE = False


class DocumentQAService:
    """Service for generating MC questions from documents"""

    @staticmethod
    def generate_questions_from_document(
        document_id,
        deck_id,
        user_id,
        count=10,
        difficulty='medium',
        topics=None,
        subject_area=None
    ):
        """
        Generate multiple choice questions from a document using Gemini File API

        Args:
            document_id: ID of the document to generate questions from
            deck_id: ID of deck to associate questions with
            user_id: ID of requesting user
            count: Number of questions to generate (default: 10)
            difficulty: Difficulty level as string ('easy', 'medium', 'hard', 'expert')
            topics: Optional specific topics/sections to focus on
            subject_area: Optional subject category

        Returns:
            dict with success, questions list, and metadata
        """
        try:
            # Get document
            document = Document.query.filter_by(id=document_id, user_id=user_id).first()
            if not document:
                return {
                    'success': False,
                    'error': 'Document not found',
                    'questions': [],
                    'generated_count': 0
                }

            # Check if document is ready
            if document.processing_status != 'ready' or not document.gemini_file_uri:
                return {
                    'success': False,
                    'error': 'Document is not ready for processing',
                    'questions': [],
                    'generated_count': 0
                }

            # Check if Gemini cache expired
            if document.is_gemini_cache_expired():
                return {
                    'success': False,
                    'error': 'Document cache has expired. Please refresh the cache.',
                    'questions': [],
                    'generated_count': 0
                }

            # Get AI provider
            ai_provider = GeminiProvider()
            if not ai_provider.is_available():
                return {
                    'success': False,
                    'error': 'AI provider not available',
                    'questions': [],
                    'generated_count': 0
                }

            # Convert difficulty string to numeric (1-5 scale)
            difficulty_map = {
                'easy': 1,
                'medium': 3,
                'hard': 4,
                'expert': 5
            }
            difficulty_numeric = difficulty_map.get(difficulty.lower(), 3)

            # Build prompt for document-based generation
            prompt = DocumentQAService._build_document_prompt(
                document=document,
                count=count,
                difficulty=difficulty,
                topics=topics,
                subject_area=subject_area
            )

            # Generate with document context using Gemini File API
            response = ai_provider.generate_with_file(
                prompt=prompt,
                file_uri=document.gemini_file_uri
            )

            if not response.get('success', False) and not response.get('text'):
                return {
                    'success': False,
                    'error': response.get('error', 'AI returned empty response'),
                    'questions': [],
                    'generated_count': 0
                }

            response_text = response.get('text', '')

            # Parse response into MCCard objects
            questions, parse_errors = DocumentQAService._parse_document_questions(
                response_text=response_text,
                deck_id=deck_id,
                document_id=document_id,
                difficulty=difficulty_numeric,
                generation_topic=topics or f"Document: {document.original_filename}"
            )

            if not questions:
                error_msg = f'Failed to parse AI response. {parse_errors}' if parse_errors else 'No valid questions generated'
                return {
                    'success': False,
                    'error': error_msg,
                    'questions': [],
                    'generated_count': 0,
                    'raw_response': response_text[:500]
                }

            # Log AI usage
            if HAS_AI_USAGE:
                try:
                    tokens_used = response.get('tokens_used', 0)
                    AIUsage.log_usage(
                        user_id=user_id,
                        operation_type='document_mc_generation',
                        tokens_used=tokens_used,
                        success=True
                    )
                except Exception as log_error:
                    print(f"Failed to log AI usage: {log_error}")

            return {
                'success': True,
                'questions': questions,
                'generated_count': len(questions),
                'requested_count': count,
                'document_id': document_id,
                'document_name': document.original_filename,
                'parse_warnings': parse_errors if parse_errors else None
            }

        except Exception as e:
            print(f"Document QA generation error: {str(e)}")
            import traceback
            traceback.print_exc()

            return {
                'success': False,
                'error': f'Generation failed: {str(e)}',
                'questions': [],
                'generated_count': 0
            }

    @staticmethod
    def _build_document_prompt(document, count, difficulty, topics, subject_area):
        """
        Build prompt for document-based question generation

        Args:
            document: Document model instance
            count: Number of questions
            difficulty: Difficulty level string
            topics: Optional topic focus
            subject_area: Optional subject category

        Returns:
            Formatted prompt string
        """
        base_prompt = f"""Generate {count} multiple-choice questions from this document.

Requirements:
- Difficulty level: {difficulty}
- Questions should test understanding of the document's content
- Include 4 answer choices (A, B, C, D) for each question
- Provide explanations for why each incorrect answer is wrong (misconceptions)
- Tag each question with relevant concept tags from the document
"""

        if topics:
            base_prompt += f"\n- Focus specifically on these topics: {topics}"

        if subject_area:
            base_prompt += f"\n- Subject area: {subject_area}"

        base_prompt += """

Return your response as a JSON object with this exact structure:
{
  "questions": [
    {
      "question": "Question text here?",
      "choices": {
        "A": "First choice",
        "B": "Second choice",
        "C": "Third choice",
        "D": "Fourth choice"
      },
      "correct_answer": "B",
      "misconceptions": {
        "A": "Why this is wrong",
        "C": "Why this is wrong",
        "D": "Why this is wrong"
      },
      "difficulty": 3,
      "concept_tags": ["tag1", "tag2"]
    }
  ]
}

Generate questions that test comprehension, application, and analysis of the document's content."""

        return base_prompt

    @staticmethod
    def _parse_document_questions(response_text, deck_id, document_id, difficulty, generation_topic):
        """
        Parse AI response into MCCard objects for document-based questions
        Reuses parsing logic from mc_generator_service with document-specific fields

        Returns:
            tuple: (list of MCCard objects, error messages string or None)
        """
        errors = []

        try:
            # Extract JSON from markdown if present
            json_text = DocumentQAService._extract_json(response_text)

            if not json_text:
                return [], "No JSON content found in response"

            # Parse JSON
            data = None
            try:
                data = json.loads(json_text)
            except json.JSONDecodeError as e:
                errors.append(f"JSON parse failed: {e.msg}")
                # Attempt recovery
                data = DocumentQAService._attempt_json_recovery(json_text)
                if not data:
                    return [], f"Could not parse or recover JSON. Preview: {response_text[:300]}"

            if not data:
                return [], "Failed to extract valid JSON structure"

            # Extract questions array
            questions_data = None
            if isinstance(data, dict):
                questions_data = data.get('questions') or data.get('cards')
            elif isinstance(data, list):
                questions_data = data

            if not questions_data or not isinstance(questions_data, list):
                return [], f"No valid 'questions' array found"

            # Parse individual questions
            cards = []
            for idx, q_data in enumerate(questions_data):
                try:
                    card = DocumentQAService._parse_single_question(
                        q_data=q_data,
                        deck_id=deck_id,
                        document_id=document_id,
                        difficulty=difficulty,
                        generation_topic=generation_topic
                    )
                    if card:
                        cards.append(card)
                    else:
                        errors.append(f"Q{idx + 1}: Invalid structure")
                except Exception as e:
                    errors.append(f"Q{idx + 1}: {str(e)}")
                    continue

            if not cards:
                return [], f"No valid questions generated. Errors: {'; '.join(errors)}"

            error_msg = '; '.join(errors) if errors else None
            return cards, error_msg

        except Exception as e:
            import traceback
            traceback.print_exc()
            return [], f"Parse error: {str(e)}"

    @staticmethod
    def _parse_single_question(q_data, deck_id, document_id, difficulty, generation_topic):
        """
        Parse a single question dict into MCCard object with document reference

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

        # Validate choices
        required_choices = ['A', 'B', 'C', 'D']
        if not all(choice in choices for choice in required_choices):
            return None

        # Get misconceptions
        misconceptions = q_data.get('misconceptions', {})

        # Get metadata
        q_difficulty = q_data.get('difficulty', difficulty)
        concept_tags = q_data.get('concept_tags', [])

        # Create MCCard with document reference
        card = MCCard(
            deck_id=deck_id,
            document_id=document_id,  # Link to source document
            question_text=question_text,
            choice_a=str(choices['A'])[:500],
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
            generation_topic=generation_topic,
            ai_provider='gemini'
        )

        return card

    @staticmethod
    def _extract_json(text):
        """Extract JSON from text, handling markdown code blocks"""
        json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if json_match:
            return json_match.group(1).strip()

        code_match = re.search(r'```\s*(.*?)\s*```', text, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()

        # Find first { or [ and last } or ]
        start_brace = text.find('{')
        start_bracket = text.find('[')

        start_pos = -1
        if start_brace != -1 and start_bracket != -1:
            start_pos = min(start_brace, start_bracket)
        elif start_brace != -1:
            start_pos = start_brace
        elif start_bracket != -1:
            start_pos = start_bracket

        if start_pos != -1:
            if text[start_pos] == '{':
                end_pos = text.rfind('}')
            else:
                end_pos = text.rfind(']')

            if end_pos > start_pos:
                return text[start_pos:end_pos + 1].strip()

        return text.strip()

    @staticmethod
    def _attempt_json_recovery(json_text):
        """Attempt to recover malformed JSON"""
        try:
            # Remove trailing commas
            fixed = re.sub(r',\s*([}\]])', r'\1', json_text)
            return json.loads(fixed)
        except:
            return None

    @staticmethod
    def get_document_questions(document_id, user_id):
        """
        Get all MC questions generated from a specific document

        Args:
            document_id: ID of the document
            user_id: ID of the user (for authorization)

        Returns:
            List of MCCard objects or None if document not found
        """
        # Verify document belongs to user
        document = Document.query.filter_by(id=document_id, user_id=user_id).first()
        if not document:
            return None

        # Get all questions linked to this document
        questions = MCCard.query.filter_by(document_id=document_id).order_by(MCCard.created_at.desc()).all()

        return questions

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
    def generate_questions_for_section(document_id, section_text, deck_id, user_id, count=5, difficulty='medium'):
        """
        Generate questions for a specific section of text from a document
        PLACEHOLDER for Phase 3 enhancement - user highlights text, generates questions

        Args:
            document_id: ID of source document
            section_text: The highlighted/selected text
            deck_id: ID of deck to associate with
            user_id: ID of requesting user
            count: Number of questions to generate
            difficulty: Difficulty level

        Returns:
            dict with success status and questions
        """
        # TODO: Implement in future enhancement
        return {
            'success': False,
            'error': 'Section-based generation not yet implemented',
            'questions': [],
            'generated_count': 0
        }

    @staticmethod
    def regenerate_question(question_id, user_id, reason=""):
        """
        Regenerate a single question from its source document
        Uses the same document context to create an alternative question

        Args:
            question_id: ID of the question to regenerate
            user_id: ID of requesting user
            reason: Optional reason for regeneration

        Returns:
            New MCCard object or None if failed
        """
        try:
            # Get original question
            original_card = MCCard.query.get(question_id)
            if not original_card or not original_card.document_id:
                return None

            # Verify document access
            document = Document.query.filter_by(
                id=original_card.document_id,
                user_id=user_id
            ).first()

            if not document:
                return None

            # Generate a single replacement question
            result = DocumentQAService.generate_questions_from_document(
                document_id=document.id,
                deck_id=original_card.deck_id,
                user_id=user_id,
                count=1,
                difficulty='medium',  # Could extract from original_card.difficulty
                topics=original_card.generation_topic
            )

            if result['success'] and result['questions']:
                new_card = result['questions'][0]
                # Mark with document_section if original had it
                if original_card.document_section:
                    new_card.document_section = original_card.document_section
                return new_card

            return None

        except Exception as e:
            print(f"Regenerate question error: {e}")
            return None
