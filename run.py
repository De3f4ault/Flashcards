#!/usr/bin/env python3
"""
Flask Flashcards Application
Run this file to start the development server
"""

import os
from dotenv import load_dotenv

# CRITICAL: Load environment variables from .env file BEFORE importing app
load_dotenv()

from app import create_app

# Create app instance
app = create_app()

if __name__ == '__main__':
    # Get port from environment variable or use default
    port = int(os.environ.get('PORT', 5000))

    # Run the app
    app.run(
        host='0.0.0.0',
        port=port,
        debug=app.config.get('DEBUG', False)
    )
