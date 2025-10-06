"""
Chat Views - Routes for AI chat interface
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
# DO NOT import anything from flask_wtf.csrf here
from app.services.chat_service import ChatService
from app.services.document_service import DocumentService
from app.forms.chat_forms import (
    ChatMessageForm,
    NewChatSessionForm,
    RenameSessionForm,
    AttachDocumentForm,
    SearchSessionsForm
)
from app.models.chat_session import ChatSession
from app.models.document import Document

chat_bp = Blueprint('chat', __name__, url_prefix='/chat')


@chat_bp.route('/')
@login_required
def index():
    """
    Main chat page - displays list of chat sessions.
    Redirects to most recent session or shows empty state.
    """
    # Get user's sessions
    sessions = ChatService.get_user_sessions(current_user.id, limit=50)

    # Get stats
    stats = ChatService.get_session_stats(current_user.id)

    # If user has sessions, redirect to most recent
    if sessions:
        return redirect(url_for('chat.session', session_id=sessions[0].id))

    # Otherwise show empty state with option to create new chat
    return render_template('chat/sessions.html',
                          sessions=sessions,
                          stats=stats,
                          empty_state=True)


@chat_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_session():
    """Create a new chat session"""
    form = NewChatSessionForm()

    # Populate document choices
    user_documents = DocumentService.get_user_documents(current_user.id)
    form.document_id.choices = [(0, 'No document')] + [
        (doc.id, doc.original_filename) for doc in user_documents
    ]

    if form.validate_on_submit():
        # Create session
        document_id = form.document_id.data if form.document_id.data != 0 else None
        session = ChatService.create_session(
            user_id=current_user.id,
            title=form.title.data or 'New Chat',
            document_id=document_id
        )

        flash('New chat session created', 'success')
        return redirect(url_for('chat.session', session_id=session.id))

    return render_template('chat/new_session.html', form=form)


@chat_bp.route('/<int:session_id>')
@login_required
def session(session_id):
    """
    Display chat interface for a specific session.
    Shows conversation history and input form.
    """
    # Get session with permission check
    session = ChatService.get_session(session_id, current_user.id)
    if not session:
        flash('Chat session not found', 'error')
        return redirect(url_for('chat.index'))

    # Get all user's sessions for sidebar
    all_sessions = ChatService.get_user_sessions(current_user.id, limit=50)

    # Get messages for this session
    messages = ChatService.get_session_messages(session_id, current_user.id)

    # Get user's documents for attachment
    user_documents = DocumentService.get_user_documents(current_user.id)

    # Forms
    message_form = ChatMessageForm()
    attach_form = AttachDocumentForm()
    attach_form.document_id.choices = [(doc.id, doc.original_filename) for doc in user_documents]

    return render_template('chat/interface.html',
                          session=session,
                          sessions=all_sessions,
                          messages=messages,
                          message_form=message_form,
                          attach_form=attach_form,
                          current_session_id=session_id)


@chat_bp.route('/<int:session_id>/send', methods=['POST'])
@login_required
def send_message(session_id):
    """
    AJAX endpoint for sending a message and receiving AI response.
    Returns JSON with user message and AI response.
    """
    # Get message from request
    data = request.get_json()
    user_message = data.get('message', '').strip()

    if not user_message:
        return jsonify({
            'success': False,
            'error': 'Message cannot be empty'
        }), 400

    # Send message and get response
    result = ChatService.send_message(session_id, user_message, current_user.id)

    if result['success']:
        return jsonify(result), 200
    else:
        return jsonify(result), 500


@chat_bp.route('/<int:session_id>/messages')
@login_required
def get_messages(session_id):
    """
    AJAX endpoint to fetch messages for a session.
    Supports pagination with limit/offset.
    """
    limit = request.args.get('limit', 100, type=int)
    offset = request.args.get('offset', 0, type=int)

    messages = ChatService.get_session_messages(session_id, current_user.id, limit, offset)

    return jsonify({
        'success': True,
        'messages': messages,
        'count': len(messages)
    })


@chat_bp.route('/<int:session_id>/attach-document/<int:document_id>', methods=['POST'])
@login_required
def attach_document(session_id, document_id):
    """Attach a document to the chat session"""
    result = ChatService.attach_document_to_session(session_id, document_id, current_user.id)

    if result['success']:
        flash(result['message'], 'success')
    else:
        flash(result['error'], 'error')

    # Return JSON for AJAX or redirect for form submission
    if request.is_json:
        return jsonify(result)
    return redirect(url_for('chat.session', session_id=session_id))


@chat_bp.route('/<int:session_id>/detach-document', methods=['POST'])
@login_required
def detach_document(session_id):
    """Remove document attachment from chat session"""
    result = ChatService.detach_document_from_session(session_id, current_user.id)

    if result['success']:
        flash(result['message'], 'success')
    else:
        flash(result['error'], 'error')

    if request.is_json:
        return jsonify(result)
    return redirect(url_for('chat.session', session_id=session_id))


@chat_bp.route('/<int:session_id>/rename', methods=['POST'])
@login_required
def rename_session(session_id):
    """Rename a chat session"""
    form = RenameSessionForm()

    if form.validate_on_submit():
        result = ChatService.rename_session(session_id, form.title.data, current_user.id)

        if result['success']:
            flash(result['message'], 'success')
        else:
            flash(result['error'], 'error')

    return redirect(url_for('chat.session', session_id=session_id))


@chat_bp.route('/<int:session_id>/delete', methods=['POST'])
@login_required
def delete_session(session_id):
    """Delete a chat session"""
    result = ChatService.delete_session(session_id, current_user.id)

    if result['success']:
        flash(result['message'], 'success')
        return redirect(url_for('chat.index'))
    else:
        flash(result['error'], 'error')
        return redirect(url_for('chat.session', session_id=session_id))


@chat_bp.route('/sessions/list')
@login_required
def sessions_list():
    """
    API endpoint to get list of sessions (for sidebar refresh).
    Returns JSON with session summaries.
    """
    sessions = ChatService.get_user_sessions(current_user.id, limit=50)

    return jsonify({
        'success': True,
        'sessions': [session.get_conversation_summary() for session in sessions]
    })


@chat_bp.route('/stats')
@login_required
def stats():
    """Get user's chat statistics"""
    stats = ChatService.get_session_stats(current_user.id)

    return jsonify({
        'success': True,
        'stats': stats
    })


@chat_bp.route('/<int:session_id>/info')
@login_required
def session_info(session_id):
    """Get detailed information about a session"""
    session = ChatService.get_session(session_id, current_user.id)

    if not session:
        return jsonify({
            'success': False,
            'error': 'Session not found'
        }), 404

    return jsonify({
        'success': True,
        'session': session.get_conversation_summary()
    })
