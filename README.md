# Flask Flashcards

A modern, scalable flashcard application built with Flask. Create, study, and manage flashcard decks with intelligent spaced repetition and progress tracking.

## Features

### 🎯 Core Features
- **User Authentication**: Secure registration, login, and profile management
- **Deck Management**: Create, edit, and organize flashcard decks
- **Smart Study Sessions**: Multiple study modes with progress tracking
- **Public/Private Decks**: Share decks with the community or keep them private
- **Bulk Import**: Quickly add multiple cards with text parsing
- **Statistics & Analytics**: Track your learning progress and performance

### 📊 Study Features
- **Multiple Study Modes**:
  - Random order
  - Difficulty-based (easy to hard, hard to easy)
  - Performance-based (worst to best accuracy)
  - Chronological (newest/oldest first)
  - Least studied cards first

- **Adaptive Difficulty**: Cards adjust difficulty based on your performance
- **Review System**: Identify cards that need more practice
- **Progress Tracking**: Monitor accuracy, study streaks, and improvement

### 🔧 Technical Features
- Clean, modular architecture following Flask best practices
- Service layer for business logic separation
- Comprehensive form validation
- Template filters and helpers
- Database migrations support
- CLI tools for administration

## Quick Start

### Prerequisites
- Python 3.8+
- pip (Python package installer)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/flask-flashcards.git
   cd flask-flashcards
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

5. **Initialize database**
   ```bash
   python cli.py init-db
   ```

6. **Create sample data (optional)**
   ```bash
   python cli.py create-sample-data
   ```

7. **Run the application**
   ```bash
   python run.py
   ```

Visit `http://localhost:5000` to start using the application!

## Project Structure

```
flashcards-mvp/
├── app/
│   ├── __init__.py              # App factory
│   ├── config.py                # Configuration classes
│   ├── extensions.py            # Initialize extensions
│   ├── routes.py                # Unified routes registration
│   ├── models/                  # Database models
│   │   ├── base.py              # Base model with common fields
│   │   ├── user.py              # User model
│   │   ├── deck.py              # Deck model
│   │   └── flashcard.py         # Flashcard model
│   ├── services/                # Business logic layer
│   │   ├── base_service.py      # Common service patterns
│   │   ├── auth_service.py      # Authentication logic
│   │   ├── deck_service.py      # Deck management logic
│   │   └── study_service.py     # Study session logic
│   ├── views/                   # View functions (controllers)
│   │   ├── main.py              # Homepage, dashboard
│   │   ├── auth.py              # Authentication views
│   │   ├── decks.py             # Deck management views
│   │   └── study.py             # Study session views
│   ├── forms/                   # WTForms for validation
│   │   ├── base_forms.py        # Common form patterns
│   │   ├── auth_forms.py        # Authentication forms
│   │   └── deck_forms.py        # Deck and card forms
│   ├── utils/                   # Utility functions
│   │   ├── decorators.py        # Custom decorators
│   │   ├── helpers.py           # Helper functions
│   │   └── validators.py        # Custom validators
│   ├── templates/               # Jinja2 templates
│   └── static/                  # CSS, JS, images
├── migrations/                  # Database migrations
├── cli.py                       # CLI commands
├── run.py                       # Application entry point
├── requirements.txt             # Python dependencies
└── .env                         # Environment variables
```

## CLI Commands

The application includes a command-line interface for common tasks:

```bash
# Initialize database
python cli.py init-db

# Reset database (WARNING: deletes all data)
python cli.py reset-db

# Create admin user
python cli.py create-admin

# Create sample data for testing
python cli.py create-sample-data

# Show application statistics
python cli.py stats
```

## Configuration

### Environment Variables

Create a `.env` file with the following variables:

```bash
# Flask Configuration
FLASK_ENV=development
SECRET_KEY=your-secret-key-here

# Database
DATABASE_URL=sqlite:///flashcards.db

# Application Settings
CARDS_PER_PAGE=20
DECKS_PER_PAGE=12
```

### Database Configuration

**Development (SQLite)**:
```
DATABASE_URL=sqlite:///flashcards.db
```

**Production (PostgreSQL)**:
```
DATABASE_URL=postgresql://username:password@localhost/flashcards
```

## Usage

### Creating Your First Deck

1. Register an account or log in
2. Click "Create New Deck" on your dashboard
3. Fill in the deck name and description
4. Add flashcards individually or use bulk import

### Bulk Import Format

Use the bulk import feature to quickly add multiple cards:

```
Question 1 | Answer 1
Question 2 | Answer 2
Question 3 | Answer 3
```

### Study Sessions

1. Navigate to a deck and click "Study"
2. Choose your study mode and number of cards
3. Answer each card and mark yourself correct/incorrect
4. Review your session results and statistics

## Development

### Adding New Features

The application follows a clear architectural pattern:

1. **Models**: Define your data structure in `app/models/`
2. **Services**: Add business logic in `app/services/`
3. **Forms**: Create form validation in `app/forms/`
4. **Views**: Handle HTTP requests in `app/views/`
5. **Templates**: Create the UI in `app/templates/`

### Database Migrations

When you modify models, create migrations:

```bash
flask db migrate -m "Description of changes"
flask db upgrade
```

### Testing

Run the application locally and test with sample data:

```bash
python cli.py create-sample-data
python run.py
```

## Deployment

### Production Checklist

1. Set `FLASK_ENV=production`
2. Use a strong `SECRET_KEY`
3. Configure PostgreSQL database
4. Set up a reverse proxy (nginx)
5. Use a WSGI server (gunicorn)
6. Enable HTTPS

### Example Production Setup

```bash
# Install production dependencies
pip install gunicorn psycopg2-binary

# Run with gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 "app:create_app()"
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

If you encounter any issues or have questions:

1. Check the documentation
2. Search existing issues
3. Create a new issue with detailed information

---

**Happy Learning! 📚✨**
