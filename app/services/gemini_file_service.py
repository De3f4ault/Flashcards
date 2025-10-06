"""
Gemini File API Service
Handles file uploads and management with Google's Gemini File API
"""

import google.generativeai as genai
from datetime import datetime, timedelta
from app.config import Config
import os
import time
import traceback


class GeminiFileService:
    """Service for managing files with Gemini File API"""

    def __init__(self):
        if Config.GEMINI_API_KEY:
            genai.configure(api_key=Config.GEMINI_API_KEY)
        else:
            raise ValueError("GEMINI_API_KEY not configured")

    def upload_file_to_gemini(self, file_path, display_name):
        """
        Upload a file to Gemini File API

        Args:
            file_path: Local path to the file
            display_name: Human-readable name for the file

        Returns:
            tuple: (file_uri, file_name, expires_at, error_message)
                   Returns (None, None, None, error_msg) on error
        """
        try:
            if not os.path.exists(file_path):
                error_msg = f"File not found: {file_path}"
                print(f"ERROR: {error_msg}")
                return None, None, None, error_msg

            # Check file size
            file_size = os.path.getsize(file_path)
            print(f"File size: {file_size} bytes ({file_size / (1024*1024):.2f} MB)")

            # Upload file to Gemini - FIXED METHOD CALL
            print(f"Uploading {display_name} to Gemini File API...")
            print(f"File path: {file_path}")

            # Use the correct method - upload_file is the correct method name
            # but let's check if we need to use the files module
            uploaded_file = genai.upload_file(
                path=file_path,
                display_name=display_name
            )

            print(f"Upload initiated. File name: {uploaded_file.name}")
            print(f"Initial state: {uploaded_file.state}")

            # Wait for processing to complete
            print(f"Waiting for Gemini to process file...")
            max_wait_time = 60  # 60 seconds max wait
            wait_time = 0

            while uploaded_file.state.name == "PROCESSING":
                if wait_time >= max_wait_time:
                    error_msg = f"Timeout: File processing took longer than {max_wait_time} seconds"
                    print(f"ERROR: {error_msg}")
                    return None, None, None, error_msg

                time.sleep(2)
                wait_time += 2
                uploaded_file = genai.get_file(uploaded_file.name)
                print(f"Processing... ({wait_time}s elapsed, state: {uploaded_file.state.name})")

            if uploaded_file.state.name == "FAILED":
                error_msg = f"Gemini file processing failed. State: {uploaded_file.state}"
                print(f"ERROR: {error_msg}")
                return None, None, None, error_msg

            if uploaded_file.state.name != "ACTIVE":
                error_msg = f"Unexpected file state: {uploaded_file.state.name}"
                print(f"ERROR: {error_msg}")
                return None, None, None, error_msg

            # Calculate expiry (48 hours from now)
            expires_at = datetime.utcnow() + timedelta(hours=Config.GEMINI_FILE_CACHE_DURATION)

            print(f"✓ File uploaded successfully!")
            print(f"  - File URI: {uploaded_file.uri}")
            print(f"  - File name: {uploaded_file.name}")
            print(f"  - State: {uploaded_file.state.name}")
            print(f"  - Expires: {expires_at}")

            return uploaded_file.uri, uploaded_file.name, expires_at, None

        except AttributeError as e:
            # If upload_file doesn't exist, try alternative approach
            error_msg = f"API method not found: {str(e)}"
            print(f"ERROR: {error_msg}")
            print("This might be a version compatibility issue.")
            print("Try updating the google-generativeai package:")
            print("pip install --upgrade google-generativeai")
            print(f"Full traceback:\n{traceback.format_exc()}")
            return None, None, None, error_msg

        except FileNotFoundError as e:
            error_msg = f"File not found: {str(e)}"
            print(f"ERROR: {error_msg}")
            return None, None, None, error_msg

        except Exception as e:
            error_msg = f"Unexpected error: {type(e).__name__}: {str(e)}"
            print(f"ERROR uploading file to Gemini: {error_msg}")
            print(f"Full traceback:\n{traceback.format_exc()}")
            return None, None, None, error_msg

        except Exception as e:
            error_msg = f"Unexpected error: {type(e).__name__}: {str(e)}"
            print(f"ERROR uploading file to Gemini: {error_msg}")
            print(f"Full traceback:\n{traceback.format_exc()}")
            return None, None, None, error_msg

    def check_file_active(self, gemini_file_name):
        """
        Check if a file is still active in Gemini cache

        Args:
            gemini_file_name: The Gemini file identifier

        Returns:
            bool: True if file is active, False otherwise
        """
        try:
            file = genai.get_file(gemini_file_name)
            return file.state.name == "ACTIVE"
        except Exception as e:
            print(f"Error checking file status: {e}")
            return False

    def delete_gemini_file(self, gemini_file_name):
        """
        Delete a file from Gemini File API

        Args:
            gemini_file_name: The Gemini file identifier

        Returns:
            bool: True if deleted successfully, False otherwise
        """
        try:
            genai.delete_file(gemini_file_name)
            print(f"File deleted from Gemini: {gemini_file_name}")
            return True
        except Exception as e:
            print(f"Error deleting file from Gemini: {e}")
            return False

    def get_file_info(self, gemini_file_name):
        """
        Retrieve file metadata from Gemini

        Args:
            gemini_file_name: The Gemini file identifier

        Returns:
            dict: File information or None if error
        """
        try:
            file = genai.get_file(gemini_file_name)
            return {
                'name': file.name,
                'display_name': file.display_name,
                'uri': file.uri,
                'state': file.state.name,
                'size_bytes': file.size_bytes,
                'mime_type': file.mime_type,
                'create_time': file.create_time,
                'update_time': file.update_time,
                'expiration_time': file.expiration_time
            }
        except Exception as e:
            print(f"Error getting file info: {e}")
            return None

    def refresh_expired_file(self, document):
        """
        Re-upload a file if its Gemini cache has expired

        Args:
            document: Document model instance

        Returns:
            bool: True if refresh successful, False otherwise
        """
        try:
            if not document.is_gemini_cache_expired():
                print(f"File cache still valid for: {document.original_filename}")
                return True

            print(f"Refreshing expired cache for: {document.original_filename}")

            file_path = document.get_storage_path()
            file_uri, file_name, expires_at, error_msg = self.upload_file_to_gemini(
                file_path,
                document.original_filename
            )

            if file_uri:
                document.update_gemini_info(file_uri, file_name, expires_at)
                return True
            else:
                document.mark_error(error_msg or "Failed to refresh Gemini cache")
                return False

        except Exception as e:
            print(f"Error refreshing file cache: {e}")
            document.mark_error(f"Cache refresh error: {str(e)}")
            return False

    def list_all_files(self):
        """
        List all files in Gemini File API (for debugging/maintenance)

        Returns:
            list: List of file information dicts
        """
        try:
            files = []
            for file in genai.list_files():
                files.append({
                    'name': file.name,
                    'display_name': file.display_name,
                    'state': file.state.name,
                    'create_time': file.create_time
                })
            return files
        except Exception as e:
            print(f"Error listing files: {e}")
            return []

    def cleanup_expired_files(self):
        """
        Remove all expired files from Gemini (maintenance utility)

        Returns:
            int: Number of files cleaned up
        """
        try:
            cleaned = 0
            for file in genai.list_files():
                # Check if file is expired or failed
                if file.state.name in ["FAILED", "INACTIVE"]:
                    self.delete_gemini_file(file.name)
                    cleaned += 1
            print(f"Cleaned up {cleaned} expired/failed files")
            return cleaned
        except Exception as e:
            print(f"Error during cleanup: {e}")
            return 0
