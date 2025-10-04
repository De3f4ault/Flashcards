from datetime import datetime
from flask import flash


def flash_errors(form):
    """Flash all form errors"""
    for field, errors in form.errors.items():
        for error in errors:
            flash(f"{field.replace('_', ' ').title()}: {error}", 'error')


def format_datetime(dt, format='%B %d, %Y at %I:%M %p'):
    """Format datetime for display"""
    if dt:
        return dt.strftime(format)
    return ''


def time_ago(dt):
    """Get human-readable time ago string"""
    if not dt:
        return 'Unknown'

    now = datetime.utcnow()
    diff = now - dt

    days = diff.days
    seconds = diff.seconds

    if days > 365:
        years = days // 365
        return f"{years} year{'s' if years > 1 else ''} ago"
    elif days > 30:
        months = days // 30
        return f"{months} month{'s' if months > 1 else ''} ago"
    elif days > 0:
        return f"{days} day{'s' if days > 1 else ''} ago"
    elif seconds > 3600:
        hours = seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif seconds > 60:
        minutes = seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    else:
        return "Just now"


def truncate_text(text, length=50, suffix='...'):
    """Truncate text to specified length"""
    if len(text) <= length:
        return text
    return text[:length].strip() + suffix


def get_difficulty_badge_class(difficulty):
    """Get Bootstrap badge class for difficulty level"""
    classes = {
        1: 'badge-success',    # Very Easy - Green
        2: 'badge-info',       # Easy - Blue
        3: 'badge-warning',    # Medium - Yellow
        4: 'badge-danger',     # Hard - Red
        5: 'badge-dark'        # Very Hard - Dark
    }
    return classes.get(difficulty, 'badge-secondary')


def get_accuracy_badge_class(accuracy):
    """Get Bootstrap badge class for accuracy percentage"""
    if accuracy >= 90:
        return 'badge-success'
    elif accuracy >= 70:
        return 'badge-info'
    elif accuracy >= 50:
        return 'badge-warning'
    else:
        return 'badge-danger'


def pluralize(count, singular, plural=None):
    """Return singular or plural form based on count"""
    if plural is None:
        plural = singular + 's'
    return singular if count == 1 else plural


def safe_int(value, default=0):
    """Safely convert value to int"""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def calculate_study_streak(study_dates):
    """Calculate consecutive study days streak"""
    if not study_dates:
        return 0

    # Sort dates in descending order
    sorted_dates = sorted(set(date.date() for date in study_dates), reverse=True)

    if not sorted_dates:
        return 0

    today = datetime.utcnow().date()
    streak = 0

    # Check if user studied today or yesterday
    if sorted_dates[0] == today:
        streak = 1
        check_date = today
    elif len(sorted_dates) > 1 and sorted_dates[0] == today - timedelta(days=1):
        streak = 1
        check_date = sorted_dates[0]
    else:
        return 0

    # Count consecutive days
    for i in range(1, len(sorted_dates)):
        expected_date = check_date - timedelta(days=i)
        if sorted_dates[i] == expected_date:
            streak += 1
        else:
            break

    return streak


def get_study_recommendation(stats):
    """Get study recommendation based on deck statistics"""
    if stats['total_cards'] == 0:
        return "Add some flashcards to start studying!", "info"

    if stats['unstudied_cards'] == stats['total_cards']:
        return "Start studying this new deck!", "success"

    if stats['cards_needing_review'] > 0:
        return f"{stats['cards_needing_review']} cards need review", "warning"

    if stats['avg_accuracy'] < 70:
        return "Keep practicing to improve your accuracy", "info"

    if stats['avg_accuracy'] >= 90:
        return "Great job! You've mastered this deck!", "success"

    return "Continue studying to maintain your progress", "info"
