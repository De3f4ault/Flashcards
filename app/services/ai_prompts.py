"""
Centralized AI prompt templates
All prompts for AI operations are defined here for easy management
"""

PROMPTS = {
    'generate_cards': """You are an expert educational content creator specializing in flashcard generation.

Generate {count} high-quality flashcards about: {topic}

Difficulty level: {difficulty}
Additional context: {additional_context}

Requirements:
- Create clear, concise questions on the FRONT
- Provide accurate, complete answers on the BACK
- For {difficulty} difficulty:
  * easy: Basic recall and definitions
  * medium: Application and understanding
  * hard: Analysis, synthesis, and complex concepts
- Front should be 5-50 words
- Back should be 10-200 words
- Each card should test one specific concept
- Use clear, educational language

Return ONLY a valid JSON array of objects in this exact format:
[
  {{"front": "Question here?", "back": "Answer here."}},
  {{"front": "Question here?", "back": "Answer here."}}
]

Do not include any markdown formatting, explanations, or text outside the JSON array.""",

    'enhance_card': """You are an educational content improvement specialist.

Current flashcard:
FRONT: {front_text}
BACK: {back_text}

Enhancement type: {enhancement_type}

Instructions based on enhancement type:
- clarity: Make the question clearer and the answer more precise
- examples: Add concrete examples to the answer
- simplify: Simplify language for easier understanding
- detail: Add more comprehensive details to the answer

Return ONLY a valid JSON object in this exact format:
{{
  "front": "Improved front text",
  "back": "Improved back text",
  "suggestions": ["Why this change improves learning", "Additional suggestion"]
}}

Do not include any markdown formatting, explanations, or text outside the JSON object.""",

    'generate_hint': """You are a helpful tutor providing hints to students.

The student is studying this flashcard:
QUESTION: {card_front}
ANSWER: {card_back}

The student has attempted this card {previous_attempts} time(s) and needs a hint.

Generate a helpful hint that:
- Does NOT reveal the answer directly
- Guides thinking in the right direction
- Gets progressively more specific if previous_attempts > 0
- Is 1-3 sentences long
- Uses guiding questions or partial information

Return ONLY the hint text, no JSON, no markdown, no extra formatting.""",

    'suggest_tags': """You are a content categorization specialist.

Analyze this flashcard and suggest relevant tags:
FRONT: {card_front}
BACK: {card_back}

Generate {max_tags} relevant tags that:
- Categorize the subject matter
- Are 1-3 words each
- Use lowercase
- Are commonly used educational categories
- Help organize related cards

Return ONLY a valid JSON array of strings:
["tag1", "tag2", "tag3"]

Do not include any markdown formatting, explanations, or text outside the JSON array."""
}


# Fallback prompts if main ones fail
FALLBACK_PROMPTS = {
    'generate_cards': "Generate {count} flashcards about {topic}. Return as JSON array with 'front' and 'back' fields.",
    'enhance_card': "Improve this flashcard. Front: {front_text}, Back: {back_text}. Return as JSON with 'front', 'back', and 'suggestions' fields.",
    'generate_hint': "Create a hint for this question without revealing the answer: {card_front}",
    'suggest_tags': "Suggest {max_tags} relevant tags for a flashcard about: {card_front}"
}


def get_prompt(prompt_type: str, use_fallback: bool = False) -> str:
    """
    Get a prompt template by type

    Args:
        prompt_type: Type of prompt ('generate_cards', 'enhance_card', etc.)
        use_fallback: Use simpler fallback prompt if True

    Returns:
        Prompt template string
    """
    if use_fallback:
        return FALLBACK_PROMPTS.get(prompt_type, PROMPTS.get(prompt_type, ""))
    return PROMPTS.get(prompt_type, "")
