"""
Chat Prompts - System prompts and conversation formatting for AI chat
"""

from datetime import datetime


def get_base_system_prompt():
    """
    Base system prompt for general study assistant conversations.

    Returns:
        str: System prompt text
    """
    return """You are an intelligent study assistant helping students learn effectively. Your role is to:

1. Answer questions clearly and concisely
2. Explain complex concepts in simple terms
3. Provide examples and analogies when helpful
4. Encourage critical thinking by asking clarifying questions
5. Break down difficult topics into manageable pieces
6. Suggest study strategies and learning techniques
7. Be patient, supportive, and encouraging

Guidelines:
- Keep responses focused and relevant to studying/learning
- Use markdown formatting for better readability
- Include code blocks with syntax highlighting when showing code
- Use bullet points and numbered lists for clarity
- If you don't know something, admit it rather than guessing
- Encourage the student to think through problems rather than just giving answers

Remember: Your goal is to help students understand and learn, not just provide answers."""


def get_document_aware_prompt(document_filename):
    """
    System prompt for conversations with an attached document.

    Args:
        document_filename (str): Name of the attached document

    Returns:
        str: Enhanced system prompt with document context
    """
    return f"""You are an intelligent study assistant helping students learn from their study materials.

IMPORTANT: The student has attached a document "{document_filename}" to this conversation.
You have access to the full content of this document and should reference it when answering questions.

Your role is to:
1. Answer questions about the attached document accurately
2. Explain concepts from the document clearly
3. Help the student understand difficult sections
4. Make connections between different parts of the document
5. Provide additional context or examples related to the document content
6. Create summaries of sections when requested
7. Help identify key concepts and important information

Guidelines for document-based conversations:
- Always reference the document when answering questions about it
- Quote specific sections when relevant (keep quotes concise)
- If asked about something not in the document, clearly state that
- Help the student navigate and understand the structure of the document
- Suggest study strategies specific to the document's content
- Point out relationships between concepts in the document

Remember: Base your answers on the document content while adding helpful explanations and context."""


def get_question_generation_prompt(document_context=None):
    """
    Prompt for generating study questions from documents.
    Used in Phase 3 but defined here for consistency.

    Args:
        document_context (str, optional): Context about the document

    Returns:
        str: Question generation prompt
    """
    base = """Generate thoughtful study questions based on the provided document content.

Requirements:
- Create questions that test understanding, not just memorization
- Cover different difficulty levels (easy, medium, hard)
- Include questions about key concepts, relationships, and applications
- Ensure questions are clear and unambiguous
- Provide correct answers with brief explanations"""

    if document_context:
        return f"{base}\n\nDocument context: {document_context}"

    return base


def format_conversation_history(messages, include_system=False):
    """
    Format conversation history for Gemini API.
    Converts ChatMessage objects to Gemini's expected format.

    Args:
        messages (list): List of ChatMessage objects
        include_system (bool): Whether to include system messages

    Returns:
        list: Formatted messages for Gemini API
    """
    formatted = []

    for msg in messages:
        # Get role value (handle both enum and string)
        from app.models.chat_message import MessageRole
        role_value = msg.role.value if isinstance(msg.role, MessageRole) else msg.role

        # Skip system messages unless requested
        if role_value == 'system' and not include_system:
            continue

        # Gemini uses 'model' instead of 'assistant'
        gemini_role = 'model' if role_value == 'assistant' else role_value

        formatted.append({
            'role': gemini_role,
            'parts': [{'text': msg.content}]
        })

    return formatted


def get_welcome_message():
    """
    Get a friendly welcome message for new chat sessions.

    Returns:
        str: Welcome message text
    """
    return """Hello! I'm your AI study assistant. I'm here to help you learn and understand your study materials.

You can:
- Ask me questions about any topic
- Attach documents for context-aware discussions
- Request explanations of difficult concepts
- Get study tips and learning strategies

How can I help you today?"""


def get_document_attached_message(document_name):
    """
    Message to send when a document is attached to the conversation.

    Args:
        document_name (str): Name of the attached document

    Returns:
        str: Confirmation message
    """
    return f"""I now have access to "{document_name}". I can help you:

- Understand concepts from this document
- Answer questions about specific sections
- Summarize key points
- Generate study questions
- Explain difficult parts

What would you like to know about this document?"""


def get_document_detached_message():
    """
    Message to send when a document is removed from the conversation.

    Returns:
        str: Confirmation message
    """
    return """The document has been removed from this conversation. I'm now in general study assistant mode.

Feel free to ask me anything or attach a different document!"""


def get_error_message(error_type='general'):
    """
    Get appropriate error message based on error type.

    Args:
        error_type (str): Type of error ('general', 'timeout', 'api_limit', 'document')

    Returns:
        str: User-friendly error message
    """
    messages = {
        'general': "I apologize, but I encountered an error processing your request. Please try again.",

        'timeout': "The request took too long to process. This might be due to a complex question or large document. Please try breaking down your question or asking something more specific.",

        'api_limit': "I've reached the API rate limit. Please wait a moment and try again.",

        'document': "I had trouble accessing the attached document. The document might have expired or been removed. Try refreshing the document cache or attaching it again.",

        'content_filter': "I cannot provide a response to that request as it may violate content policies. Please rephrase your question."
    }

    return messages.get(error_type, messages['general'])


def truncate_conversation_for_context(messages, max_messages=20, max_tokens=8000):
    """
    Truncate conversation history to fit within token limits.
    Keeps most recent messages and ensures we don't exceed context window.

    Args:
        messages (list): List of ChatMessage objects
        max_messages (int): Maximum number of messages to include
        max_tokens (int): Approximate maximum tokens to include

    Returns:
        list: Truncated list of messages
    """
    if len(messages) <= max_messages:
        # Check estimated tokens
        estimated_tokens = sum(msg.estimate_tokens() for msg in messages)
        if estimated_tokens <= max_tokens:
            return messages

    # Start with most recent messages
    truncated = []
    total_tokens = 0

    for msg in reversed(messages):
        msg_tokens = msg.estimate_tokens()
        if total_tokens + msg_tokens > max_tokens or len(truncated) >= max_messages:
            break
        truncated.insert(0, msg)
        total_tokens += msg_tokens

    return truncated


def create_context_summary_prompt(messages):
    """
    Create a prompt to summarize conversation history when it gets too long.

    Args:
        messages (list): List of messages to summarize

    Returns:
        str: Summary prompt
    """
    conversation_text = "\n\n".join([
        f"{'User' if msg.is_from_user() else 'Assistant'}: {msg.content}"
        for msg in messages
    ])

    return f"""Please provide a brief summary of the following conversation to maintain context:

{conversation_text}

Summarize the key topics discussed and any important conclusions or information shared. Keep it concise (2-3 sentences)."""


def format_message_for_display(message):
    """
    Format a message for display in the UI with proper markdown rendering.

    Args:
        message (ChatMessage): Message to format

    Returns:
        dict: Formatted message data for UI
    """
    return {
        'id': message.id,
        'role': message.role.value if hasattr(message.role, 'value') else message.role,
        'content': message.content,
        'timestamp': message.get_formatted_timestamp(),
        'tokens': message.tokens_used,
        'has_error': message.has_error,
        'error_message': message.error_message
    }
