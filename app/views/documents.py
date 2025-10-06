"""
Documents Views
Routes for document upload, viewing, and management
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, abort
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.forms.document_forms import DocumentUploadForm, DocumentSearchForm
from app.services.document_service import DocumentService
from app.services.gemini_file_service import GeminiFileService
from app.services.document_qa_service import DocumentQAService
from app.models import Document, Deck

documents_bp = Blueprint('documents', __name__, url_prefix='/documents')


@documents_bp.route('/')
@login_required
def library():
    """Display user's document library"""
    # Get filter/sort parameters
    search_form = DocumentSearchForm(request.args)
    sort_by = request.args.get('sort_by', 'upload_date')
    order = request.args.get('order', 'desc')
    file_type = request.args.get('file_type', 'all')

    # Get documents
    documents = DocumentService.get_user_documents(
        current_user.id,
        order_by=sort_by,
        ascending=(order == 'asc')
    )

    # Filter by file type if specified
    if file_type != 'all':
        documents = [doc for doc in documents if doc.file_type == file_type]

    # Get storage stats
    storage_stats = DocumentService.get_user_storage_usage(current_user.id)

    # Get question counts for each document
    doc_question_counts = {}
    for doc in documents:
        questions = DocumentQAService.get_document_questions(doc.id, current_user.id)
        doc_question_counts[doc.id] = len(questions) if questions else 0

    return render_template(
        'documents/library.html',
        title='My Documents',
        documents=documents,
        search_form=search_form,
        storage_stats=storage_stats,
        doc_question_counts=doc_question_counts
    )


@documents_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    """Handle document upload"""
    form = DocumentUploadForm()

    if form.validate_on_submit():
        try:
            file = form.document.data
            custom_title = form.title.data or None

            # Create document (saves locally and uploads to Gemini)
            document = DocumentService.create_document(
                user_id=current_user.id,
                file=file,
                original_filename=custom_title or file.filename
            )

            if document:
                if document.processing_status == 'ready':
                    flash(f'Document "{document.original_filename}" uploaded successfully!', 'success')
                elif document.processing_status == 'error':
                    flash(f'Document uploaded but Gemini processing failed: {document.error_message}', 'warning')
                else:
                    flash(f'Document "{document.original_filename}" uploaded and processing...', 'info')

                return redirect(url_for('documents.view', id=document.id))
            else:
                flash('Failed to upload document. Please try again.', 'error')

        except ValueError as e:
            flash(str(e), 'error')
        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'error')

    return render_template(
        'documents/upload.html',
        title='Upload Document',
        form=form
    )


@documents_bp.route('/<int:id>')
@login_required
def view(id):
    """View document details"""
    document = DocumentService.get_document(id, current_user.id)

    if not document:
        flash('Document not found', 'error')
        return redirect(url_for('documents.library'))

    # Get document statistics
    stats = DocumentService.get_document_stats(id)

    # Get generated questions count
    questions = DocumentQAService.get_document_questions(id, current_user.id)
    stats['questions_count'] = len(questions) if questions else 0

    # Get user's decks for the generation form
    user_decks = Deck.query.filter_by(user_id=current_user.id).order_by(Deck.name).all()

    return render_template(
        'documents/view.html',
        title=document.original_filename,
        document=document,
        stats=stats,
        user_decks=user_decks
    )


@documents_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    """Delete a document"""
    document = DocumentService.get_document(id, current_user.id)

    if not document:
        flash('Document not found', 'error')
        return redirect(url_for('documents.library'))

    filename = document.original_filename

    if DocumentService.delete_document(id, current_user.id):
        flash(f'Document "{filename}" deleted successfully', 'success')
    else:
        flash('Failed to delete document', 'error')

    return redirect(url_for('documents.library'))


@documents_bp.route('/<int:id>/refresh-cache', methods=['POST'])
@login_required
def refresh_cache(id):
    """Manually refresh Gemini cache for a document"""
    document = DocumentService.get_document(id, current_user.id)

    if not document:
        return jsonify({'success': False, 'error': 'Document not found'}), 404

    try:
        gemini_service = GeminiFileService()
        success = gemini_service.refresh_expired_file(document)

        if success:
            return jsonify({
                'success': True,
                'message': 'Cache refreshed successfully',
                'expires_at': document.gemini_expires_at.isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': document.error_message or 'Failed to refresh cache'
            }), 500

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@documents_bp.route('/<int:id>/info')
@login_required
def info(id):
    """Get document information as JSON"""
    document = DocumentService.get_document(id, current_user.id)

    if not document:
        return jsonify({'error': 'Document not found'}), 404

    return jsonify(document.to_dict())


@documents_bp.route('/api/upload-status/<int:id>')
@login_required
def upload_status(id):
    """Check upload/processing status (for AJAX polling)"""
    document = Document.query.filter_by(id=id, user_id=current_user.id).first()

    if not document:
        return jsonify({'error': 'Document not found'}), 404

    return jsonify({
        'status': document.processing_status,
        'error': document.error_message,
        'gemini_ready': document.gemini_file_uri is not None
    })


# ===== Phase 3: Question Generation Routes =====

@documents_bp.route('/<int:id>/generate-questions', methods=['POST'])
@login_required
def generate_questions(id):
    """
    Generate multiple choice questions from a document
    Form data: count, difficulty, deck_id, topics (optional)
    """
    document = DocumentService.get_document(id, current_user.id)

    if not document:
        flash('Document not found', 'error')
        return redirect(url_for('documents.library'))

    # Validate document is ready
    if document.processing_status != 'ready':
        flash('Document is not ready for question generation', 'error')
        return redirect(url_for('documents.view', id=id))

    if document.is_gemini_cache_expired():
        flash('Document cache has expired. Please refresh the cache first.', 'warning')
        return redirect(url_for('documents.view', id=id))

    try:
        # Get form parameters
        count = int(request.form.get('count', 10))
        difficulty = request.form.get('difficulty', 'medium')
        deck_id = int(request.form.get('deck_id'))
        topics = request.form.get('topics', '').strip() or None

        # Validate deck ownership
        deck = Deck.query.filter_by(id=deck_id, user_id=current_user.id).first()
        if not deck:
            flash('Invalid deck selected', 'error')
            return redirect(url_for('documents.view', id=id))

        # Validate count
        if count < 1 or count > 50:
            flash('Question count must be between 1 and 50', 'error')
            return redirect(url_for('documents.view', id=id))

        # Generate questions
        result = DocumentQAService.generate_questions_from_document(
            document_id=id,
            deck_id=deck_id,
            user_id=current_user.id,
            count=count,
            difficulty=difficulty,
            topics=topics
        )

        if result['success']:
            # Save questions to database
            save_result = DocumentQAService.save_questions(result['questions'])

            if save_result['success']:
                flash(
                    f"Successfully generated {save_result['saved_count']} questions from {document.original_filename}!",
                    'success'
                )
                return redirect(url_for('documents.questions', id=id))
            else:
                flash(f"Questions generated but failed to save: {save_result['error']}", 'error')
                return redirect(url_for('documents.view', id=id))
        else:
            flash(f"Failed to generate questions: {result['error']}", 'error')
            return redirect(url_for('documents.view', id=id))

    except ValueError as e:
        flash(f'Invalid input: {str(e)}', 'error')
        return redirect(url_for('documents.view', id=id))
    except Exception as e:
        flash(f'Error generating questions: {str(e)}', 'error')
        return redirect(url_for('documents.view', id=id))


@documents_bp.route('/<int:id>/questions')
@login_required
def questions(id):
    """
    View all questions generated from a document
    Shows question list with stats and management options
    """
    document = DocumentService.get_document(id, current_user.id)

    if not document:
        flash('Document not found', 'error')
        return redirect(url_for('documents.library'))

    # Get all questions for this document
    questions = DocumentQAService.get_document_questions(id, current_user.id)

    if questions is None:
        flash('Unable to load questions', 'error')
        return redirect(url_for('documents.view', id=id))

    # Group questions by deck
    questions_by_deck = {}
    for question in questions:
        deck_name = question.deck.name if question.deck else 'Unknown Deck'
        if deck_name not in questions_by_deck:
            questions_by_deck[deck_name] = []
        questions_by_deck[deck_name].append(question)

    return render_template(
        'documents/questions.html',
        title=f'Questions: {document.original_filename}',
        document=document,
        questions=questions,
        questions_by_deck=questions_by_deck,
        total_questions=len(questions)
    )


@documents_bp.route('/<int:id>/study')
@login_required
def study(id):
    """
    Start MC study session with questions from this document
    Filters MC study to only questions from this document
    """
    document = DocumentService.get_document(id, current_user.id)

    if not document:
        flash('Document not found', 'error')
        return redirect(url_for('documents.library'))

    # Get questions from this document
    questions = DocumentQAService.get_document_questions(id, current_user.id)

    if not questions:
        flash('No questions generated from this document yet', 'info')
        return redirect(url_for('documents.view', id=id))

    # Get the deck_id from first question (all should be in same deck ideally)
    # Or allow user to select which deck's questions to study
    deck_ids = list(set(q.deck_id for q in questions))

    if len(deck_ids) == 1:
        # All questions in one deck - redirect to MC study with filter
        return redirect(url_for(
            'mc_study.start',
            deck_id=deck_ids[0],
            document_id=id
        ))
    else:
        # Questions across multiple decks - let user choose
        flash(f'Questions are in {len(deck_ids)} different decks. Please select a deck to study.', 'info')
        return redirect(url_for('documents.questions', id=id))
