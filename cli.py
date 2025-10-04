#!/usr/bin/env python3
"""
CLI script for database and application management
"""

import click
from app import create_app
from app.extensions import db
from app.models import User, Deck, Flashcard
from app.services import AuthService, DeckService, StudyService


@click.group()
def cli():
    """Flask Flashcards CLI"""
    pass


@cli.command()
def init_db():
    """Initialize the database"""
    app = create_app()
    with app.app_context():
        db.create_all()
        click.echo('Database initialized successfully!')


@cli.command()
def reset_db():
    """Reset the database (WARNING: This will delete all data)"""
    if click.confirm('This will delete all data. Are you sure?'):
        app = create_app()
        with app.app_context():
            db.drop_all()
            db.create_all()
            click.echo('Database reset successfully!')


@cli.command()
@click.option('--username', prompt=True, help='Username for the admin user')
@click.option('--email', prompt=True, help='Email for the admin user')
@click.option('--password', prompt=True, hide_input=True, help='Password for the admin user')
def create_admin(username, email, password):
    """Create an admin user"""
    app = create_app()
    with app.app_context():
        user, message = AuthService.register_user(username, email, password)
        if user:
            click.echo(f'Admin user created: {username}')
        else:
            click.echo(f'Error: {message}')


@cli.command()
def create_sample_data():
    """Create sample data for testing"""
    app = create_app()
    with app.app_context():
        # Create sample user
        user, _ = AuthService.register_user('demo', 'demo@example.com', 'password123')
        if not user:
            user = AuthService.get_user_by_username('demo')

        # Create sample deck
        deck = DeckService.create_deck(
            user_id=user.id,
            name='Spanish Vocabulary',
            description='Basic Spanish words and phrases',
            is_public=True
        )

        # Create sample flashcards
        sample_cards = [
            {'front_text': 'Hello', 'back_text': 'Hola'},
            {'front_text': 'Goodbye', 'back_text': 'Adiós'},
            {'front_text': 'Please', 'back_text': 'Por favor'},
            {'front_text': 'Thank you', 'back_text': 'Gracias'},
            {'front_text': 'Yes', 'back_text': 'Sí'},
            {'front_text': 'No', 'back_text': 'No'},
            {'front_text': 'Water', 'back_text': 'Agua'},
            {'front_text': 'Food', 'back_text': 'Comida'},
            {'front_text': 'House', 'back_text': 'Casa'},
            {'front_text': 'Friend', 'back_text': 'Amigo/Amiga'}
        ]

        StudyService.bulk_create_flashcards(deck.id, sample_cards)

        click.echo(f'Sample data created!')
        click.echo(f'- User: demo (password: password123)')
        click.echo(f'- Deck: {deck.name} with {len(sample_cards)} cards')


@cli.command()
def stats():
    """Show application statistics"""
    app = create_app()
    with app.app_context():
        user_count = User.query.count()
        deck_count = Deck.query.count()
        card_count = Flashcard.query.count()
        public_deck_count = Deck.query.filter_by(is_public=True).count()

        click.echo('Application Statistics:')
        click.echo(f'- Total Users: {user_count}')
        click.echo(f'- Total Decks: {deck_count}')
        click.echo(f'- Public Decks: {public_deck_count}')
        click.echo(f'- Total Flashcards: {card_count}')


if __name__ == '__main__':
    cli()
