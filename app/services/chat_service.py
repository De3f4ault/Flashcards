"""
Chat Service
Business logic for AI chat functionality
"""

from datetime import datetime
from sqlalchemy import desc, or_
from app.extensions import db
from app.models import ChatSession, ChatMessage, Document, User
from app.services.gemini_file_service import GeminiFileService


class ChatService:
    """Service for managing chat sessions and messages"""

    @staticmethod
    def create_session(user_id, title=None, document_id=None):
        """
        Create a new chat session

        Args:
            user_id: The user creating the session
            title: Optional session title
            document_id: Optional document to attach

        Returns:
            ChatSession: The created session or None if error
        """
        try:
            # If document is attached, verify it belongs to user
            if document_id:
                document = Document.query.get(document_id)
                if not document or document.user_id != user_id:
                    return None

            session = ChatSession(
                user_id=user_id,
                title=title or "New Chat",
                document_id=document_id
            )

            db.session.add(session)
            db.session.commit()

            return session

        except Exception as e:
            db.session.rollback()
            print(f"Error creating chat session: {e}")
            return None

    @staticmethod
    def send_message(session_id, user_message, user_id):
        """
        Send a message in a chat session and get AI response

        Args:
            session_id: The chat session ID
            user_message: The user's message text
            user_id: The user making the request

        Returns:
            dict: Response data or None if error
        """
        from app.services.ai_service import AIService
        from app.services.ai_providers.chat_prompts import (
            format_conversation_history,
            get_base_system_prompt,
            get_document_aware_prompt
        )

        # Initialize Gemini file service
        gemini_file_service = GeminiFileService()

        try:
            session = ChatSession.query.get(session_id)
            if not session:
                return {
                    'success': False,
                    'error': 'Session not found'
                }

            # Permission check
            if session.user_id != user_id:
                return {
                    'success': False,
                    'error': 'Access denied'
                }

            # Check if document is attached and refresh cache if needed
            document_context = None
            if session.document_id:
                document = Document.query.get(session.document_id)
                if document and document.is_gemini_cache_expired():
                    gemini_file_service.refresh_expired_file(document)
                    db.session.commit()
                document_context = document

            # Create user message
            user_msg = ChatMessage.create_user_message(session_id, user_message)
            db.session.add(user_msg)
            db.session.flush()

            # Get conversation history
            history = session.get_recent_messages(limit=20)
            formatted_history = format_conversation_history(history)

            # Get system prompt
            if document_context:
                system_prompt = get_document_aware_prompt(document_context.original_filename)
            else:
                system_prompt = get_base_system_prompt()

            # Generate AI response - FIXED: Use static method directly
            if document_context and document_context.gemini_file_uri:
                # Use document context
                response = AIService.generate_with_file(
                    prompt=user_message,
                    file_uri=document_context.gemini_file_uri,
                    conversation_history=formatted_history,
                    system_prompt=system_prompt,
                    user_id=user_id  # Added user_id parameter
                )
            else:
                # Regular chat
                response = AIService.generate_chat_response(
                    user_message=user_message,
                    conversation_history=formatted_history,
                    system_prompt=system_prompt,
                    user_id=user_id  # Added user_id parameter
                )

            if response.get('success'):
                # Create assistant message
                assistant_msg = ChatMessage.create_assistant_message(
                    session_id,
                    response['content'],
                    response.get('tokens_used', 0)
                )
                db.session.add(assistant_msg)

                # Update session statistics
                session.message_count += 2
                session.total_tokens_used += user_msg.tokens_used + assistant_msg.tokens_used
                session.update_last_message_time()

                db.session.commit()

                return {
                    'success': True,
                    'user_message': user_msg.to_dict(),
                    'assistant_message': assistant_msg.to_dict(),
                    'session': {
                        'message_count': session.message_count,
                        'total_tokens': session.total_tokens_used
                    }
                }
            else:
                # Handle error
                error_msg = ChatMessage.create_error_message(
                    session_id,
                    response.get('error', 'Failed to generate response')
                )
                db.session.add(error_msg)
                db.session.commit()

                return {
                    'success': False,
                    'error': response.get('error', 'Failed to generate response')
                }

        except Exception as e:
            db.session.rollback()
            print(f"Chat service error: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def get_session_messages(session_id, user_id, limit=None):
        """
        Get all messages for a session

        Args:
            session_id: The chat session ID
            user_id: The user making the request
            limit: Optional limit on number of messages

        Returns:
            list: List of messages or None if error
        """
        try:
            session = ChatSession.query.get(session_id)
            if not session or session.user_id != user_id:
                return None

            query = ChatMessage.query.filter_by(session_id=session_id).order_by(ChatMessage.timestamp)

            if limit:
                query = query.limit(limit)

            return query.all()

        except Exception as e:
            print(f"Error getting session messages: {e}")
            return None

    @staticmethod
    def get_user_sessions(user_id, search=None, sort_by='recent', limit=None):
        """
        Get all chat sessions for a user

        Args:
            user_id: The user ID
            search: Optional search term for session titles
            sort_by: Sort method ('recent', 'oldest', 'title', 'messages')
            limit: Optional limit on number of sessions

        Returns:
            list: List of chat sessions
        """
        try:
            query = ChatSession.query.filter_by(user_id=user_id)

            # Apply search filter
            if search:
                query = query.filter(ChatSession.title.ilike(f'%{search}%'))

            # Apply sorting
            if sort_by == 'recent':
                query = query.order_by(desc(ChatSession.last_message_at))
            elif sort_by == 'oldest':
                query = query.order_by(ChatSession.created_at)
            elif sort_by == 'title':
                query = query.order_by(ChatSession.title)
            elif sort_by == 'messages':
                query = query.order_by(desc(ChatSession.message_count))
            else:
                query = query.order_by(desc(ChatSession.last_message_at))

            if limit:
                query = query.limit(limit)

            return query.all()

        except Exception as e:
            print(f"Error getting user sessions: {e}")
            return []

    @staticmethod
    def get_session(session_id, user_id):
        """
        Get a single session with permission check

        Args:
            session_id: The session ID
            user_id: The user making the request

        Returns:
            ChatSession: The session or None if not found/no permission
        """
        try:
            session = ChatSession.query.get(session_id)
            if session and session.user_id == user_id:
                return session
            return None

        except Exception as e:
            print(f"Error getting session: {e}")
            return None

    @staticmethod
    def delete_session(session_id, user_id):
        """
        Delete a chat session and all its messages

        Args:
            session_id: The session ID
            user_id: The user making the request

        Returns:
            dict: Result with success status and message
        """
        try:
            session = ChatSession.query.get(session_id)
            if not session or session.user_id != user_id:
                return {
                    'success': False,
                    'error': 'Session not found or access denied'
                }

            # Delete all messages first
            ChatMessage.query.filter_by(session_id=session_id).delete()

            # Delete session
            db.session.delete(session)
            db.session.commit()

            return {
                'success': True,
                'message': 'Chat session deleted successfully'
            }

        except Exception as e:
            db.session.rollback()
            print(f"Error deleting session: {e}")
            return {
                'success': False,
                'error': f'Failed to delete session: {str(e)}'
            }

    @staticmethod
    def rename_session(session_id, new_title, user_id):
        """
        Rename a chat session

        Args:
            session_id: The session ID
            new_title: The new title
            user_id: The user making the request

        Returns:
            dict: Result with success status and message
        """
        try:
            session = ChatSession.query.get(session_id)
            if not session or session.user_id != user_id:
                return {
                    'success': False,
                    'error': 'Session not found or access denied'
                }

            session.title = new_title
            db.session.commit()

            return {
                'success': True,
                'message': 'Session renamed successfully',
                'session': session.to_dict()
            }

        except Exception as e:
            db.session.rollback()
            print(f"Error renaming session: {e}")
            return {
                'success': False,
                'error': f'Failed to rename session: {str(e)}'
            }

    @staticmethod
    def attach_document_to_session(session_id, document_id, user_id):
        """
        Attach a document to a chat session

        Args:
            session_id: The chat session ID
            document_id: The document to attach
            user_id: The user making the request

        Returns:
            dict: Updated session info or error
        """
        # Initialize Gemini file service
        gemini_file_service = GeminiFileService()

        try:
            session = ChatSession.query.get(session_id)
            document = Document.query.get(document_id)

            if not session or not document:
                return {
                    'success': False,
                    'error': 'Session or document not found'
                }

            # Permission checks
            if session.user_id != user_id or document.user_id != user_id:
                return {
                    'success': False,
                    'error': 'Access denied'
                }

            # Refresh cache if needed
            if document.is_gemini_cache_expired():
                success = gemini_file_service.refresh_expired_file(document)
                if not success:
                    return {
                        'success': False,
                        'error': 'Document cache expired and refresh failed'
                    }
                db.session.commit()

            # Check if file is active
            if not gemini_file_service.check_file_active(document.gemini_file_name):
                return {
                    'success': False,
                    'error': 'Document not available in Gemini cache'
                }

            # Attach document
            session.attach_document(document_id)
            db.session.commit()

            return {
                'success': True,
                'message': f'Document "{document.original_filename}" attached successfully',
                'session': session.to_dict(),
                'document': document.to_dict()
            }

        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': f'Failed to attach document: {str(e)}'
            }

    @staticmethod
    def detach_document(session_id, user_id):
        """
        Remove document from a chat session

        Args:
            session_id: The chat session ID
            user_id: The user making the request

        Returns:
            dict: Result with success status and message
        """
        try:
            session = ChatSession.query.get(session_id)
            if not session or session.user_id != user_id:
                return {
                    'success': False,
                    'error': 'Session not found or access denied'
                }

            session.detach_document()
            db.session.commit()

            return {
                'success': True,
                'message': 'Document detached successfully',
                'session': session.to_dict()
            }

        except Exception as e:
            db.session.rollback()
            print(f"Error detaching document: {e}")
            return {
                'success': False,
                'error': f'Failed to detach document: {str(e)}'
            }

    @staticmethod
    def detach_document_from_session(session_id, user_id):
        """
        Alias for detach_document for backward compatibility

        Args:
            session_id: The chat session ID
            user_id: The user making the request

        Returns:
            dict: Result with success status and message
        """
        return ChatService.detach_document(session_id, user_id)

    @staticmethod
    def get_user_stats(user_id):
        """
        Get chat statistics for a user

        Args:
            user_id: The user ID

        Returns:
            dict: Statistics dictionary
        """
        try:
            total_sessions = ChatSession.query.filter_by(user_id=user_id).count()
            total_messages = db.session.query(ChatMessage).join(ChatSession).filter(
                ChatSession.user_id == user_id
            ).count()
            total_tokens = db.session.query(db.func.sum(ChatSession.total_tokens_used)).filter(
                ChatSession.user_id == user_id
            ).scalar() or 0

            return {
                'total_sessions': total_sessions,
                'total_messages': total_messages,
                'total_tokens': total_tokens,
                'avg_messages_per_session': round(total_messages / total_sessions, 1) if total_sessions > 0 else 0
            }

        except Exception as e:
            print(f"Error getting user stats: {e}")
            return {
                'total_sessions': 0,
                'total_messages': 0,
                'total_tokens': 0,
                'avg_messages_per_session': 0
            }

    @staticmethod
    def get_session_stats(user_id):
        """
        Alias for get_user_stats for backward compatibility

        Args:
            user_id: The user ID

        Returns:
            dict: Statistics dictionary
        """
        return ChatService.get_user_stats(user_id)
