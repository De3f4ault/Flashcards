from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, logout_user, current_user
from app.forms import LoginForm, RegistrationForm, ChangePasswordForm, ProfileForm
from app.services import AuthService
from app.extensions import db
from app.config import Config

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login page"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        user, message = AuthService.authenticate_user(
            form.username_or_email.data,
            form.password.data
        )

        if user:
            AuthService.login_user_session(user, remember=form.remember_me.data)
            flash(message, 'success')

            # Redirect to next page if specified, otherwise dashboard
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('main.dashboard'))
        else:
            flash(message, 'error')

    return render_template('auth/login.html', title='Sign In', form=form)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = RegistrationForm()
    if form.validate_on_submit():
        user, message = AuthService.register_user(
            username=form.username.data,
            email=form.email.data,
            password=form.password.data
        )

        if user:
            flash(f'{message} You can now sign in.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash(message, 'error')

    return render_template('auth/register.html', title='Create Account', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    """User logout"""
    username = current_user.username
    AuthService.logout_user_session()
    flash(f'Goodbye, {username}! You have been logged out.', 'info')
    return redirect(url_for('main.index'))


@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile page"""
    form = ProfileForm(
        original_username=current_user.username,
        original_email=current_user.email
    )

    if form.validate_on_submit():
        AuthService.update(
            current_user,
            username=form.username.data,
            email=form.email.data
        )
        flash('Your profile has been updated successfully.', 'success')
        return redirect(url_for('auth.profile'))

    # Pre-populate form with current data
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email

    return render_template('auth/profile.html', title='Profile', form=form)


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change password page"""
    form = ChangePasswordForm()

    if form.validate_on_submit():
        # Verify current password
        if current_user.check_password(form.current_password.data):
            AuthService.update_password(current_user, form.new_password.data)
            flash('Your password has been updated successfully.', 'success')
            return redirect(url_for('auth.profile'))
        else:
            flash('Current password is incorrect.', 'error')

    return render_template('auth/change_password.html', title='Change Password', form=form)


@auth_bp.route('/account')
@login_required
def account():
    """Account overview page"""
    user_stats = {
        'total_decks': current_user.get_deck_count(),
        'total_cards': current_user.get_total_cards(),
        'account_age': (current_user.created_at).strftime('%B %d, %Y')
    }

    return render_template('auth/account.html', title='Account', stats=user_stats)


# ============================================================================
# NEW: AI FEATURES MANAGEMENT
# ============================================================================

@auth_bp.route('/toggle-ai', methods=['POST'])
@login_required
def toggle_ai():
    """Toggle AI features for the current user"""

    # Check if AI is globally enabled
    if not Config.AI_ENABLED:
        flash('AI features are not available at this time.', 'warning')
        return redirect(url_for('auth.profile'))

    # Toggle AI status
    current_user.ai_enabled = not current_user.ai_enabled

    # If enabling AI and user has no credits, give them free credits
    if current_user.ai_enabled and current_user.ai_credits == 0:
        current_user.ai_credits = Config.AI_FREE_CREDITS_PER_USER

    # Save changes
    db.session.commit()

    if current_user.ai_enabled:
        flash(f'AI features enabled! You have {current_user.get_ai_credits_display()} credits.', 'success')
    else:
        flash('AI features have been disabled.', 'info')

    return redirect(url_for('auth.profile'))
