"""
MC Study Service
Handles logic for MC study sessions, answer processing, and basic statistics
"""

from typing import List, Dict, Optional
from datetime import datetime
from app.models import MCCard, MCSession, MCAttempt
from app.extensions import db
import random


class MCStudyService:
    """Service for managing MC study sessions"""

    @staticmethod
    def create_session(deck_id: int, user_id: int, session_title: Optional[str] = None) -> MCSession:
        """
        Create a new MC study session

        Args:
            deck_id: Deck to study
            user_id: User creating the session
            session_title: Optional title for the session

        Returns:
            MCSession object
        """
        session = MCSession(
            deck_id=deck_id,
            user_id=user_id,
            session_title=session_title,
            started_at=datetime.utcnow(),
            is_completed=False,
            total_questions=0,
            correct_count=0
        )

        db.session.add(session)
        db.session.commit()

        return session

    @staticmethod
    def get_session_cards(deck_id: int, shuffle: bool = True) -> List[MCCard]:
        """
        Get all MC cards for a deck

        Args:
            deck_id: Deck ID
            shuffle: Whether to randomize order

        Returns:
            List of MCCard objects
        """
        cards = MCCard.query.filter_by(deck_id=deck_id).all()

        if shuffle:
            random.shuffle(cards)

        return cards

    @staticmethod
    def record_attempt(
        session_id: int,
        card_id: int,
        user_id: int,
        selected_choice: str,
        confidence_rating: int,
        time_spent_seconds: int
    ) -> Dict:
        """
        Record a user's answer attempt

        Args:
            session_id: Current session ID
            card_id: Card being answered
            user_id: User ID
            selected_choice: Letter chosen (A, B, C, D)
            confidence_rating: 1-5 confidence level
            time_spent_seconds: Seconds spent on question

        Returns:
            Dict with attempt data and correctness info
        """
        # Get card to check correct answer
        card = MCCard.query.get(card_id)
        if not card:
            return {'success': False, 'error': 'Card not found'}

        # Check if answer is correct
        is_correct = card.is_correct(selected_choice)

        # Create attempt record
        attempt = MCAttempt(
            session_id=session_id,
            card_id=card_id,
            user_id=user_id,
            selected_choice=selected_choice.upper(),
            is_correct=is_correct,
            confidence_rating=confidence_rating,
            time_spent_seconds=time_spent_seconds
        )

        db.session.add(attempt)

        # Update session metrics
        session = MCSession.query.get(session_id)
        if session:
            session.add_attempt_result(is_correct)

        db.session.commit()

        return {
            'success': True,
            'is_correct': is_correct,
            'correct_answer': card.correct_answer,
            'selected_choice': selected_choice.upper(),
            'misconception': card.get_misconception(selected_choice) if not is_correct else None,
            'attempt_id': attempt.id
        }

    @staticmethod
    def complete_session(session_id: int) -> Dict:
        """
        Mark a session as complete and finalize metrics

        Args:
            session_id: Session to complete

        Returns:
            Dict with session summary
        """
        session = MCSession.query.get(session_id)
        if not session:
            return {'success': False, 'error': 'Session not found'}

        session.mark_complete()
        db.session.commit()

        return {
            'success': True,
            'summary': session.get_summary_stats()
        }

    @staticmethod
    def get_session_progress(session_id: int) -> Dict:
        """
        Get current progress in a session

        Args:
            session_id: Session ID

        Returns:
            Dict with progress info
        """
        session = MCSession.query.get(session_id)
        if not session:
            return {'success': False}

        return {
            'success': True,
            'total_questions': session.total_questions,
            'correct_count': session.correct_count,
            'accuracy': session.get_accuracy_percentage(),
            'is_completed': session.is_completed
        }

    @staticmethod
    def get_feedback_data(attempt_id: int) -> Dict:
        """
        Get comprehensive feedback data for an attempt

        Args:
            attempt_id: MCAttempt ID

        Returns:
            Dict with feedback information
        """
        attempt = MCAttempt.query.get(attempt_id)
        if not attempt:
            return {'success': False, 'error': 'Attempt not found'}

        card = attempt.card

        feedback = {
            'success': True,
            'is_correct': attempt.is_correct,
            'selected_choice': attempt.selected_choice,
            'correct_answer': card.correct_answer,
            'question': card.question_text,
            'choices': card.get_choices_dict(),
            'time_spent': attempt.get_time_formatted(),
            'confidence': attempt.get_confidence_label()
        }

        if not attempt.is_correct:
            # Include misconception for wrong answer
            feedback['misconception'] = card.get_misconception(attempt.selected_choice)
            feedback['correct_explanation'] = f"The correct answer is {card.correct_answer}: {card.get_choices_dict()[card.correct_answer]}"
        else:
            # For correct answers, just congratulate
            feedback['message'] = "Correct! Great work."

        return feedback

    @staticmethod
    def get_deck_mc_stats(deck_id: int) -> Dict:
        """
        Get statistics about MC cards in a deck

        Args:
            deck_id: Deck ID

        Returns:
            Dict with deck statistics
        """
        cards = MCCard.query.filter_by(deck_id=deck_id).all()

        if not cards:
            return {
                'total_cards': 0,
                'total_attempts': 0,
                'avg_accuracy': 0.0
            }

        total_attempts = 0
        total_correct = 0

        for card in cards:
            stats = card.get_accuracy_stats()
            total_attempts += stats['times_attempted']
            total_correct += stats['times_correct']

        avg_accuracy = (total_correct / total_attempts * 100) if total_attempts > 0 else 0.0

        return {
            'total_cards': len(cards),
            'total_attempts': total_attempts,
            'avg_accuracy': round(avg_accuracy, 1),
            'ai_generated_count': sum(1 for c in cards if c.ai_generated)
        }

    @staticmethod
    def get_user_sessions(user_id: int, deck_id: Optional[int] = None, limit: int = 10) -> List[MCSession]:
        """
        Get recent study sessions for a user

        Args:
            user_id: User ID
            deck_id: Optional deck filter
            limit: Max sessions to return

        Returns:
            List of MCSession objects
        """
        query = MCSession.query.filter_by(user_id=user_id)

        if deck_id:
            query = query.filter_by(deck_id=deck_id)

        sessions = query.order_by(MCSession.started_at.desc()).limit(limit).all()

        return sessions

    @staticmethod
    def delete_card(card_id: int) -> Dict:
        """
        Delete an MC card and all associated attempts

        Args:
            card_id: Card to delete

        Returns:
            Dict with success status
        """
        try:
            card = MCCard.query.get(card_id)
            if not card:
                return {'success': False, 'error': 'Card not found'}

            db.session.delete(card)
            db.session.commit()

            return {'success': True}

        except Exception as e:
            db.session.rollback()
            return {'success': False, 'error': str(e)}

    @staticmethod
    def get_next_card_in_session(session_id: int, answered_card_ids: List[int]) -> Optional[MCCard]:
        """
        Get the next card to show in a session

        Args:
            session_id: Current session
            answered_card_ids: List of card IDs already answered

        Returns:
            Next MCCard or None if no more cards
        """
        session = MCSession.query.get(session_id)
        if not session:
            return None

        # Get all cards in deck that haven't been answered yet
        cards = MCCard.query.filter(
            MCCard.deck_id == session.deck_id,
            ~MCCard.id.in_(answered_card_ids)
        ).all()

        if not cards:
            return None

        # Return first available card (already shuffled when session started)
        return cards[0]
