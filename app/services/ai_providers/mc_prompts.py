"""
MC Question Generation Prompts
Specialized prompts for generating multiple choice questions with misconception analysis
"""

MC_GENERATION_PROMPT = """You are an expert educational content creator specializing in multiple choice question design.

Generate {count} high-quality multiple choice questions about: {topic}

Difficulty level: {difficulty} (1=Beginner, 5=Expert)
Subject area: {subject_area}
{context_section}

CRITICAL REQUIREMENTS:
1. Each question must have EXACTLY 4 choices (A, B, C, D)
2. EXACTLY ONE choice must be correct
3. Each INCORRECT choice must represent a specific misconception or common error
4. Question must be clear and unambiguous
5. All choices must be plausible to someone who doesn't fully understand the concept

DIFFICULTY GUIDELINES:
- Level 1-2 (Beginner/Easy): Basic recall, definitions, simple concepts
- Level 3 (Medium): Application, understanding relationships, multi-step thinking
- Level 4-5 (Advanced/Expert): Analysis, synthesis, complex scenarios, edge cases

MISCONCEPTION QUALITY:
Each wrong answer should represent:
- A specific conceptual misunderstanding (not just random wrong facts)
- Common student errors based on incomplete understanding
- Predictable mistakes from similar-looking concepts
- Logical errors in reasoning about the topic

Return ONLY valid JSON in this EXACT format (no markdown, no explanation):
{{
  "questions": [
    {{
      "question": "Clear, specific question text here?",
      "choices": {{
        "A": "First choice text",
        "B": "Second choice text",
        "C": "Third choice text",
        "D": "Fourth choice text"
      }},
      "correct_answer": "B",
      "misconceptions": {{
        "A": "Specific explanation of why this wrong answer is tempting and what misconception it represents",
        "C": "Explanation for this misconception",
        "D": "Explanation for this misconception"
      }},
      "concept_tags": ["tag1", "tag2", "tag3"]
    }}
  ]
}}

VALIDATION CHECKLIST (ensure each question):
✓ Has exactly 4 choices
✓ Has exactly 1 correct answer
✓ Question ends with ? if it's a question
✓ All choices are complete sentences or phrases
✓ Misconceptions explain WHY the wrong answer is tempting
✓ Concept tags are specific and relevant
✓ No duplicate choices
✓ Choices are similar in length and structure"""


MC_REGENERATE_SINGLE_PROMPT = """You are an expert educational content creator. The user is not satisfied with this question and wants a better version.

Original question:
{original_question}

Topic: {topic}
Difficulty: {difficulty}
Reason for regeneration: {reason}

Generate ONE new, improved multiple choice question on the same concept but with:
- Different wording that's clearer
- Different but equally valid choices
- Better misconception explanations
- Same difficulty level

Return ONLY valid JSON in this EXACT format:
{{
  "question": "Improved question text?",
  "choices": {{
    "A": "First choice",
    "B": "Second choice",
    "C": "Third choice",
    "D": "Fourth choice"
  }},
  "correct_answer": "A",
  "misconceptions": {{
    "B": "Why this is wrong and what misconception it represents",
    "C": "Misconception explanation",
    "D": "Misconception explanation"
  }},
  "concept_tags": ["tag1", "tag2"]
}}"""


MC_VALIDATION_PROMPT = """You are a quality control expert for educational content.

Analyze this multiple choice question for quality issues:

Question: {question}
Choices: {choices}
Correct Answer: {correct_answer}

Check for these issues:
1. Is the question clear and unambiguous?
2. Are there exactly 4 choices?
3. Is exactly one answer marked correct?
4. Are any choices duplicates or nearly identical?
5. Are the wrong choices plausible misconceptions (not obviously wrong)?
6. Is the question actually testing understanding (not just memorization)?
7. Are choices of similar length and complexity?

Return ONLY valid JSON:
{{
  "is_valid": true/false,
  "quality_score": 0-100,
  "issues": ["List of specific issues found, if any"],
  "suggestions": ["Specific improvements that could be made"]
}}"""


def get_mc_generation_prompt(topic, count, difficulty, subject_area, additional_context=None):
    """
    Build the full MC generation prompt with parameters

    Args:
        topic: Main topic for questions
        count: Number of questions to generate
        difficulty: 1-5 difficulty level
        subject_area: Subject category
        additional_context: Optional additional instructions

    Returns:
        Formatted prompt string
    """
    context_section = ""
    if additional_context:
        context_section = f"Additional context/instructions: {additional_context}"

    return MC_GENERATION_PROMPT.format(
        count=count,
        topic=topic,
        difficulty=difficulty,
        subject_area=subject_area,
        context_section=context_section
    )


def get_mc_regenerate_prompt(original_question, topic, difficulty, reason="User requested improvement"):
    """Build prompt for regenerating a single question"""
    return MC_REGENERATE_SINGLE_PROMPT.format(
        original_question=original_question,
        topic=topic,
        difficulty=difficulty,
        reason=reason
    )


def get_mc_validation_prompt(question, choices, correct_answer):
    """Build prompt for validating question quality"""
    choices_str = "\n".join([f"{letter}: {text}" for letter, text in choices.items()])

    return MC_VALIDATION_PROMPT.format(
        question=question,
        choices=choices_str,
        correct_answer=correct_answer
    )


# Subject area mappings for better context
SUBJECT_AREAS = {
    'science': 'Science (Biology, Chemistry, Physics, Earth Science)',
    'math': 'Mathematics (Algebra, Geometry, Calculus, Statistics)',
    'history': 'History (World History, US History, Ancient History)',
    'language': 'Language Arts (Grammar, Literature, Writing, Reading)',
    'social_studies': 'Social Studies (Geography, Civics, Economics, Sociology)',
    'computer_science': 'Computer Science (Programming, Algorithms, Data Structures)',
    'general': 'General Knowledge (Cross-disciplinary topics)'
}


def get_subject_area_description(subject_key):
    """Get full description for a subject area"""
    return SUBJECT_AREAS.get(subject_key.lower(), SUBJECT_AREAS['general'])
