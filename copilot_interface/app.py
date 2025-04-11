from flask import (
    Flask,
    request,
    jsonify,
    g,
    redirect,
    url_for,
    Blueprint,
    make_response,
    render_template
)
from werkzeug.utils import safe_join, secure_filename  # secure_filename moved here
# Remove the import from security module
from werkzeug.security import generate_password_hash, check_password_hash  # If you need these
from datetime import datetime
import sys
import os
import requests
import binascii
import json
import logging
import csv
import tempfile
import re
import uuid
import base64
import time
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from pydantic import BaseModel
from google.oauth2 import service_account
from flask_compress import Compress
from pydantic_settings import BaseSettings
from tenacity import retry, stop_after_attempt, wait_exponential
from functools import lru_cache
from ratelimit import limits, sleep_and_retry, RateLimitException
from openlibrary_search import fetch_books_from_openlibrary
from dotenv import load_dotenv
from flask_socketio import SocketIO, emit
# Add at the top of your file, after imports
import socket
# Set DNS resolution timeout and configure DNS
socket.setdefaulttimeout(20)  # 20 seconds timeout

# Add at the beginning of your app.py
from dotenv import load_dotenv
load_dotenv()  # Make sure this is called before any environment variables are accessed

# Import local settings if available
try:
    from local_settings_oldish import *
    # Load values into environment
    for key, value in locals().copy().items():
        if (key.isupper() and isinstance(value, str)):
            os.environ[key] = value
except ImportError:
    pass

# Load credentials directly from file
creds_path = "google-credentials.json"
credentials = service_account.Credentials.from_service_account_file(creds_path)

# ✅ Tell Google APIs where the file is
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path

# Force usage of system DNS resolver instead of eventlet's
os.environ['EVENTLET_NO_GREENDNS'] = 'yes'

# Enable mock data by default in development mode
USE_MOCK_DATA = os.environ.get("USE_MOCK_DATA", "false").lower() == "true"

# Define OpenAI API key
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# Define Google Books API key
GOOGLE_BOOKS_API_KEY = os.environ.get("GOOGLE_BOOKS_API_KEY", "")

# Define BookResponse model
class BookResponse(BaseModel):
    title: str
    authors: list[str]
    description: str | None = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "The Great Gatsby",
                "authors": ["F. Scott Fitzgerald"],
                "description": "A story of the American dream...",
                "categories": ["Fiction", "Classic"],
                "publisher": "Scribner"
            }
        }
    }

# Initialize Blueprint
api_v1 = Blueprint('api_v1', __name__, url_prefix='/api/v1')

# Set up logging - place this near the top of the file
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define function to register routes
def register_routes(api_v1):
    """Registers all the routes for the api_v1 blueprint."""
    pass

# Define create_app function
def create_app():
    """Application factory pattern"""
    app = Flask(__name__)

    # Check if environment variables are loaded properly
    google_api_key = os.environ.get("GOOGLE_BOOKS_API_KEY", "")
    logger.info(f"Google Books API Key from env: {'Yes' if google_api_key else 'No'} (Length: {len(google_api_key)})")

    # Configure app settings
    app.config.update(
        GOOGLE_BOOKS_API_KEY=google_api_key.strip(),
        GOOGLE_APPLICATION_CREDENTIALS=creds_path,  # Add this line
        CACHE_TIMEOUT=3600  # Default value from the removed Settings class
    )
    app.config['RESULTS_DIR'] = os.path.join(os.getcwd(), "learning", "Results")
    os.makedirs(app.config['RESULTS_DIR'], exist_ok=True)

    # Move the before_request handler into the app factory
    @app.before_request
    def before_request():
        # Assign a unique request ID to `g` for tracking and logging purposes
        g.request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))
        logger.info(f"Processing request {g.request_id}: {request.method} {request.path}")

    initialize_extensions(app)
    setup_routes(app)

    # Log environment variables (masked for security)
    google_api_key = os.environ.get("GOOGLE_BOOKS_API_KEY", "")
    logger.info(f"Google Books API Key configured: {'Yes' if google_api_key else 'No'} (Length: {len(google_api_key)})")
    
    app.config.update(
        GOOGLE_BOOKS_API_KEY=google_api_key.strip(),
        # ... rest of your config ...
    )

    return app

def initialize_extensions(app):
    """Initialize Flask extensions."""
    compress = Compress()
    compress.init_app(app)

def setup_routes(app):
    """Set up routes and blueprints."""
    # API endpoints
    
    @app.route("/api")
    def api_index():
        """Serve the LibraryCloud API interface"""
        return render_template('api_s_index.html')
        
    @app.route('/home')
    def home():
        return redirect(url_for('home_page'))
    
    # Book search endpoints
    @app.route("/search_books")
    def search_books():
        """Search books endpoint with enhanced metadata extraction and mock data fallback."""
        query = request.args.get("query")
        if not query:
            return jsonify({"error": "Query parameter is required"}), 400
    
        try:
            # Try to fetch real data with a short timeout
            mock_param = request.args.get("mock", "")
            use_mock = (mock_param.lower() == "true" if mock_param else USE_MOCK_DATA)
            
            if (use_mock):
                # Use mock data if explicitly requested
                books = get_mock_books(query, "google")
                return jsonify({
                    "message": f"Found {len(books)} mock books for '{query}'",
                    "books": books,
                    "drive_link": None,
                    "mock": True
                })
            
            # Try to fetch real data
            books = fetch_books_from_google(query)
            
            if not books:
                # Fallback to mock if no real books found
                books = get_mock_books(query, "google")
                return jsonify({
                    "message": f"No real books found. Returning {len(books)} mock books for '{query}'",
                    "books": books,
                    "drive_link": None,
                    "mock": True
                })
                
            # Upload results to Google Drive
            file_path = upload_search_results_to_drive(books, query)
            return jsonify({
                "message": f"Found {len(books)} books for '{query}'",
                "books": books,
                "drive_link": file_path,
                "mock": False
            })
        except Exception as e:
            # Always fallback to mock data on error
            mock_books = get_mock_books(query, "google")
            return jsonify({
                "message": f"API error. Returning {len(mock_books)} mock books for '{query}'",
                "books": mock_books,
                "drive_link": None,
                "mock": True,
                "error": str(e)
            })

    # Other API routes...
    
    # Chat interface route
    @app.route('/')
    def home_page():
        """Serve the main Illustrator Co-Pilot interface"""
        return render_template('index.html')
    # Removed duplicate route definition for '/'
    app.register_blueprint(api_v1)

    # Register core routes
    @app.route("/api/welcome")
    def api_welcome():
        return "<h1>Welcome to the LibraryCloud API!</h1>"

    @app.route("/test_drive")
    def test_drive():
        try:
            # Log credential information for debugging
            logger.info(f"Using credentials from: {creds_path}")
            logger.info(f"Credential type: {type(credentials)}")
            
            # Get the Drive service
            service = get_drive_service()
            
            # Test with a simple API call
            about = service.about().get(fields="user,storageQuota").execute()
            
            # Return detailed information
            return jsonify({
                "success": True,
                "credentials_file": creds_path,
                "credentials_type": str(type(credentials)),
                "drive_folder_id": GOOGLE_DRIVE_FOLDER_ID,
                "user": about.get("user", {}),
                "quota": about.get("storageQuota", {})
            })
        except Exception as e:
            logger.error(f"Drive test failed: {str(e)}", exc_info=True)
            return jsonify({
                "success": False,
                "error": str(e),
                "credentials_file": creds_path,
                "drive_folder_id": GOOGLE_DRIVE_FOLDER_ID
            }), 500

    @app.route("/verify_credentials")
    def verify_credentials():
        """Verify Google Drive credentials configuration."""
        try:
            # Use the global credentials variable instead of trying to get from app.config
            creds_file = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
            
            # Check if file exists
            file_exists = os.path.exists(creds_path)
            
            # Get info about credentials object
            creds_type = str(type(credentials))
            creds_str = str(credentials)
            
            return jsonify({
                "success": True,
                "credentials_file_path": creds_path,
                "credentials_file_exists": file_exists,
                "credentials_type": creds_type,
                "credentials_loaded": bool(credentials),
                "credentials_preview": creds_str[:50] + "..." if len(creds_str) > 50 else creds_str,
                "environment_variable_set": bool(creds_file),
                "drive_folder_id": GOOGLE_DRIVE_FOLDER_ID
            })
        except Exception as e:
            logger.error(f"Credential verification failed: {str(e)}", exc_info=True)
            return jsonify({"error": f"Credentials verification failed: {str(e)}"}), 500

    @app.route("/api/status")
    def api_status():
        """Show API status including mock mode"""
        return jsonify({
            "status": "ok",
            "mock_mode": USE_MOCK_DATA,
            "env": app.config.get("FLASK_ENV", "production"),
            "apis": {
                "google_books": bool(GOOGLE_BOOKS_API_KEY),
                "google_drive": bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS")),
                "openai": bool(OPENAI_API_KEY)
            }
        })

    @app.route('/debug_openlibrary')
    def debug_openlibrary():
        """Debug endpoint for OpenLibrary search functionality."""
        try:
            # Check if httpx is installed
            import httpx
            httpx_version = httpx.__version__
            
            # Check environment variable
            mock_setting = os.environ.get("USE_MOCK_DATA", "false").lower()
            
            # Test the actual function with a simple query
            query = request.args.get('query', 'python programming')
            start_time = datetime.now()
            result = fetch_books_from_openlibrary(query)
            duration = (datetime.now() - start_time).total_seconds()
            
            return jsonify({
                "success": True,
                "diagnostics": {
                    "httpx_version": httpx_version,
                    "USE_MOCK_DATA": mock_setting,
                    "query": query,
                    "response_time_seconds": duration
                },
                "books_found": len(result),
                "data": result
            })
        except ImportError as e:
            return jsonify({
                "success": False,
                "error": f"Import error: {str(e)}",
                "fix": "Try installing httpx with: pip install httpx"
            })
        except Exception as e:
            import traceback
            return jsonify({
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc()
            })

    @app.route("/search_openlibrary")
    def search_openlibrary():
        """Search for books using OpenLibrary API."""
        try:
            query = request.args.get("query", "")
            if not query or len(query.strip()) == 0:
                return jsonify({"error": "Query parameter is required"}), 400
            
            # Log the search request
            logger.info(f"Searching OpenLibrary for: {query}")
            
            # Call the OpenLibrary search function
            books = fetch_books_from_openlibrary(query)
            
            # Upload results to Google Drive - ADD THIS LINE
            drive_link = upload_search_results_to_drive(books, query)
            
            # Return results
            return jsonify({
                "success": True,
                "source": "openlibrary",
                "query": query,
                "books": books,
                "count": len(books),
                "drive_link": drive_link  # ADD THIS LINE
            })
        except Exception as e:
            logger.error(f"Error in OpenLibrary search: {str(e)}", exc_info=True)
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route("/list_results")
    def list_results():
        """List saved search results."""
        try:
            # Fix: Use app.config to get RESULTS_DIR
            results_dir = app.config['RESULTS_DIR']
            if not os.path.exists(results_dir):
                logger.warning(f"Results directory does not exist: {results_dir}")
                return jsonify({
                    "error": "Results directory does not exist",
                    "directory": results_dir
                }), 404

            # List all CSV files in the results directory
            result_files = [f for f in os.listdir(results_dir) if f.endswith('.csv')]
            return jsonify({
                "files": result_files,
                "count": len(result_files),
                "directory": results_dir
            })
        except Exception as e:
            logger.exception(f"Error listing results: {str(e)}")
            return jsonify({"error": "An unexpected error occurred while listing results"}), 500

    @app.route("/get_file")
    def get_file():
        filename = request.args.get("filename")
        if not filename:
            return jsonify({"error": "Filename parameter is required"}), 400

        results_dir = app.config['RESULTS_DIR']
        logger.info(f"Looking for file {filename} in directory {results_dir}")

        try:
            # Validate filename
            if not re.match(r'^[a-zA-Z0-9_.-]+$', filename):
                filename = secure_filename(filename)
                if not filename:
                    return jsonify({"error": "Invalid filename format"}), 400
            
            filepath = os.path.join(results_dir, filename)
            
            # Check if file exists
            if not os.path.exists(filepath):
                logger.error(f"File not found: {filepath}")
                return jsonify({"error": "File not found"}), 404
            
            # Prevent directory traversal
            if os.path.commonpath([os.path.abspath(filepath), os.path.abspath(results_dir)]) != os.path.abspath(results_dir):
                logger.error(f"Security issue: Attempted to access file outside results directory")
                return jsonify({"error": "Security error"}), 403

            # Log file size
            file_size = os.path.getsize(filepath)
            logger.info(f"Serving file {filepath} with size {file_size} bytes")
        
            # Read file in binary mode
            with open(filepath, 'rb') as f:
                response = make_response(f.read())
                response.headers['Content-Type'] = 'text/csv'
                response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
                return response

        except Exception as e:
            logger.exception(f"Error serving file {filename}: {e}")
            return jsonify({"error": f"Error serving file: {str(e)}"}), 500

    # Add this to your setup_routes function
    @app.route('/socket.io/', defaults={'path': ''})
    @app.route('/socket.io/<path:path>')
    def socket_io_handler(path):
        """Handle socket.io requests gracefully since we're not using socket.io."""
        return jsonify({"error": "Socket.IO not enabled in this version"}), 400

    @app.route("/test_google_books_api")
    def test_google_books_api():
        """Test the Google Books API directly."""
        try:
            import requests
            from urllib.parse import quote
            
            # Get API key with quote handling
            api_key = get_api_key("GOOGLE_BOOKS_API_KEY")
            
            # Simple test query
            query = "python programming"
            encoded_query = quote(query)
            url = f"https://www.googleapis.com/books/v1/volumes?q={encoded_query}&key={api_key}"
            
            # Log request details
            logger.info(f"Testing Google Books API with key length: {len(api_key)}")
            logger.info(f"Request URL: {url}")
            
            # Make request
            response = requests.get(url, timeout=10)
            status_code = response.status_code
            
            # Check response
            if (status_code == 200):
                data = response.json()
                items = data.get("items", [])
                return jsonify({
                    "success": True,
                    "status_code": status_code,
                    "items_count": len(items),
                    "first_item_title": items[0]["volumeInfo"]["title"] if items else None
                })
            else:
                error_text = response.text
                return jsonify({
                    "success": False,
                    "status_code": status_code,
                    "error": error_text
                }), 500
                
        except Exception as e:
            logger.error(f"Error testing Google Books API: {str(e)}", exc_info=True)
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route("/batch_search")
    def batch_search():
        """Process a batch of search terms from a CSV file."""
        try:
            # Get parameters
            csv_file = request.args.get("file", "search_terms.csv")
            source = request.args.get("source", "both").lower()  # google, openlibrary, or both
            
            # Validate source parameter
            if source not in ["google", "openlibrary", "both"]:
                return jsonify({"error": "Invalid source parameter. Use 'google', 'openlibrary', or 'both'."}), 400
            
            # Path to the CSV file containing search terms
            csv_path = os.path.join(os.getcwd(), csv_file)
            
            # Check if file exists
            if not os.path.exists(csv_path):
                return jsonify({"error": f"CSV file not found: {csv_path}"}), 404
            
            # Read search terms from CSV
            search_terms = []
            with open(csv_path, 'r', encoding='utf-8') as file:
                reader = csv.reader(file)
                for row in reader:
                    if row and len(row) > 0 and row[0].strip():
                        search_terms.append(row[0].strip())
            
            if not search_terms:
                return jsonify({"error": "No valid search terms found in CSV file"}), 400
            
            # Process each search term
            results = []
            for term in search_terms:
                result = {"term": term, "google": None, "openlibrary": None}
                
                # Perform Google Books search if requested
                if source in ["google", "both"]:
                    try:
                        books = fetch_books_from_google(term)
                        drive_link = upload_search_results_to_drive(books, term)
                        result["google"] = {
                            "success": True,
                            "books_count": len(books),
                            "drive_link": drive_link
                        }
                    except Exception as e:
                        logger.error(f"Error in Google search for term '{term}': {str(e)}")
                        result["google"] = {
                            "success": False,
                            "error": str(e)
                        }
                
                # Perform OpenLibrary search if requested
                if source in ["openlibrary", "both"]:
                    try:
                        books = fetch_books_from_openlibrary(term)
                        drive_link = upload_search_results_to_drive(books, term)
                        result["openlibrary"] = {
                            "success": True,
                            "books_count": len(books),
                            "drive_link": drive_link
                        }
                    except Exception as e:
                        logger.error(f"Error in OpenLibrary search for term '{term}': {str(e)}")
                        result["openlibrary"] = {
                            "success": False,
                            "error": str(e)
                        }
                
                results.append(result)
                # Add a small delay to avoid rate limiting
                time.sleep(1)
            
            return jsonify({
                "success": True,
                "total_terms": len(search_terms),
                "results": results
            })
                
        except Exception as e:
            logger.error(f"Error in batch search: {str(e)}", exc_info=True)
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route("/extract_text")
    def extract_text_route():
        """Extract full text from books in the results directory."""
        try:
            # Get parameters
            file_limit = int(request.args.get("file_limit", 5))
            book_limit = int(request.args.get("book_limit", 20))
            
            # Use the specific results directory with your CSV files
            results_dir = "/Users/bmcmanus/Documents/my_docs/portfolio/ill-co-p3/results/"
            
            # Get Google Drive folder ID for storing text files
            drive_folder_id = os.environ.get("GOOGLE_FOLDER_ID", "1bSffGGwtrnmn8wCXkE0T0Be36oKSLeNA")
            
            logger.info(f"Starting text extraction from {results_dir} with limits: {file_limit} files, {book_limit} books")
            logger.info(f"Using Google Drive folder ID: {drive_folder_id}")
            
            # Import and use the extract_full_text function
            from text_extraction import extract_full_text
            results = extract_full_text(
                results_dir=results_dir,
                file_limit=file_limit,
                book_limit=book_limit,
                drive_folder_id=drive_folder_id
            )
            
            # Return results
            return jsonify({
                "success": True,
                "books_processed": results.get("books_processed", 0),
                "books_with_full_text": results.get("books_with_full_text", 0),
                "summary_by_source": results.get("summary_by_source", {}),
                "results_file": results.get("results_file", ""),
                "drive_link": results.get("drive_link", "")
            })
            
        except Exception as e:
            logger.error(f"Error in extract_text_route: {str(e)}", exc_info=True)
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

# Add this function for fallback mock data

def get_mock_books(query, source="unknown"):
    """Return mock book data for testing when external APIs are unavailable."""
    return [
        {
            "title": f"{source.title()} Book About {query.title()}",
            "authors": ["API Connection Error"],
            "description": f"This is mock data because the {source} API connection failed. Try again later."
        },
        {
            "title": f"Another {source.title()} Book About {query.title()}",
            "authors": ["API Connection Error"],
            "description": "Mock data for testing purposes."
        }
    ]

# Define extract_book_info function first so it can be used later
def extract_book_info(item):
    """Extract book information from Google Books API response item."""
    volume_info = item.get("volumeInfo", {})
    
    # Extract ISBN information
    industry_identifiers = volume_info.get("industryIdentifiers", [])
    isbn_10 = next((id_info.get("identifier") for id_info in industry_identifiers 
                   if id_info.get("type") == "ISBN_10"), None)
    isbn_13 = next((id_info.get("identifier") for id_info in industry_identifiers 
                   if id_info.get("type") == "ISBN_13"), None)
    
    return {
        "title": volume_info.get("title", "Unknown Title"),
        "authors": volume_info.get("authors", ["Unknown Author"]),
        "description": volume_info.get("description"),
        "isbn": isbn_13 or isbn_10,  # Prefer ISBN-13 if available
        "isbn_10": isbn_10,
        "isbn_13": isbn_13,
        "publisher": volume_info.get("publisher"),
        "published_date": volume_info.get("publishedDate"),
        "categories": volume_info.get("categories", []),
        "page_count": volume_info.get("pageCount"),
        "language": volume_info.get("language")
    }

def get_api_key(key_name):
    """Get API key from environment and strip any surrounding quotes."""
    value = os.environ.get(key_name, "").strip()
    # Remove surrounding quotes if present
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        value = value[1:-1]
    return value

# Define fetch_books_from_google function
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
def fetch_books_from_google(query):
    """Fetch books from Google Books API with improved retry logic."""
    if not query or not isinstance(query, str) or len(query.strip()) == 0:
        raise ValueError("Query parameter must be a non-empty string.")

    try:
        from urllib.parse import quote
        import requests
        
        # Get API key directly from environment - don't remove quotes
        api_key = os.environ.get("GOOGLE_BOOKS_API_KEY", "").strip()
        if not api_key:
            logger.error("Google Books API key is missing")
            raise BookAPIError("API key is required for Google Books API")
            
        encoded_query = quote(query)
        url = f"https://www.googleapis.com/books/v1/volumes?q={encoded_query}&key={api_key}"
        logger.info(f"[Google Books] Request URL: {url} (API key length: {len(api_key)})")
        
        # Add custom headers to help with DNS resolution
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json'
        }
        
        # Use a longer timeout and custom headers
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if "items" not in data:
            logger.warning(f"Google Books API returned no items for query: {query}")
            return []
            
        books = [extract_book_info(item) for item in data.get("items", [])]
        logger.info(f"Found {len(books)} books in Google Books for query: {query}")
        return books
        
    except requests.RequestException as e:
        logger.error(f"Error fetching books from Google: {str(e)}")
        raise BookAPIError(f"Failed to fetch books: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in fetch_books_from_google: {str(e)}", exc_info=True)
        raise BookAPIError(f"Unexpected error: {str(e)}")

# Log application details
logger.info(f"Application root: {os.path.dirname(__file__)}")
logger.info(f"Running on Heroku: {bool(os.getenv('HEROKU'))}")

from flask import current_app
# Replace the get_drive_service function with this simplified version
def get_drive_service():
    """Returns an authenticated Google Drive service object."""
    try:
        # Simply use the credentials loaded at module level
        global credentials
        
        # Use the right scope for Drive API
        scoped_credentials = credentials.with_scopes(["https://www.googleapis.com/auth/drive.file"])
        
        # Build and return the service
        service = build('drive', 'v3', credentials=scoped_credentials)
        logger.info("Successfully created Google Drive service")
        return service
    except Exception as e:
        logger.error(f"Failed to create Drive service: {str(e)}", exc_info=True)
        raise GoogleDriveError(f"Drive service creation failed: {str(e)}")

# Define custom exceptions
class GoogleDriveError(Exception):
    """Custom exception for Google Drive operations"""
    pass

class BookAPIError(Exception):
    """Custom exception for Book API operations"""
    pass

# Define upload_to_google_drive function
# Ensure GOOGLE_DRIVE_FOLDER_ID is defined
GOOGLE_DRIVE_FOLDER_ID = os.environ.get("GOOGLE_DRIVE_FOLDER_ID", "your-default-folder-id")

def upload_to_google_drive(file_path, file_name):
    """Uploads a file to Google Drive with enhanced logging."""
    if not os.path.exists(file_path):
        logger.error(f"File not found at path: {file_path}")
        raise GoogleDriveError(f"File not found: {file_path}")

    logger.info(f"Starting upload process for file: {file_name}")
    logger.info(f"File path: {file_path}")
    logger.info(f"File size: {os.path.getsize(file_path)} bytes")

    try:
        logger.info("Getting Drive service...")
        service = get_drive_service()
        
        logger.info("Creating file metadata with parent folder...")
        file_metadata = {
            'name': file_name,  # ADD THIS LINE - sets the file name
            'parents': [GOOGLE_DRIVE_FOLDER_ID]
        }
        
        logger.info("Creating MediaFileUpload object...")
        media = MediaFileUpload(file_path, resumable=True)
        
        logger.info("Executing file creation...")
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        file_id = file.get('id')

        if not file_id:
            logger.error("No file ID received after upload")
            raise GoogleDriveError("Failed to get file ID after upload")

        logger.info(f"File uploaded successfully with ID: {file_id}")

        # Make the file publicly accessible
        @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
        def set_file_permissions():
            logger.info(f"Setting permissions for file ID: {file_id}")
            
            # Make file public
            public_permission = service.permissions().create(
                fileId=file_id,
                body={
                    "role": "reader",  # Changed from writer to reader: This allows anyone with the link to view the file, which is safer than granting edit permissions to the public.
                    "type": "anyone"
                }
            ).execute()
            logger.info(f"Public permission result: {public_permission}")

            # Add specific user permission
            user_permission = service.permissions().create(
                fileId=file_id,
                body={
                    "role": "writer",
                    "type": "user",
                    "emailAddress": os.environ.get("DRIVE_NOTIFICATION_EMAIL", "iwasonamountian@gmail.com")
                },
                sendNotificationEmail=False
            ).execute()
            logger.info(f"User permission result: {user_permission}")

        try:
            set_file_permissions()
            share_link = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
            logger.info(f"File shared successfully. Link: {share_link}")
            return share_link
        except Exception as e:
            logger.error(f"Error setting file permissions: {str(e)}", exc_info=True)
            # Return the link even if permission setting fails
            return f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"

    except Exception as e:
        logger.error(f"Error in upload_to_google_drive: {str(e)}", exc_info=True)
        return None

# Fix: A new function to handle both saving to CSV and uploading to Drive
def upload_search_results_to_drive(books, query):
    """Saves books to a temporary CSV file and uploads to Google Drive."""
    if not books:
        logger.warning("No books found for the given query.")
        return None

    temp_file = None
    try:
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp:
            temp_file = temp.name
        
        # Sanitize query to remove special characters
        sanitized_query = re.sub(r'[^\w\s-]', '', query).strip().replace(" ", "_")
        
        # Add design principles keywords
        design_principles = "contrast_design_principles"
        
        # Generate a sequential number (using timestamp for uniqueness)
        sequence_number = int(datetime.now().timestamp()) % 1000  # Last 3 digits of timestamp
        
        # New file naming convention
        file_name = f'{sanitized_query}-{design_principles}-{sequence_number}.csv'
        
        # Write data to temp file
        with open(temp_file, "w", newline="", encoding="utf-8") as file:
            # Add ISBN fields to the CSV
            fieldnames = ["title", "authors", "description", "isbn", "isbn_10", "isbn_13", "publisher", "published_date"]
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            for book in books:
                book_row = {field: book.get(field, "") for field in fieldnames}
                if isinstance(book_row.get('authors'), list):
                    book_row['authors'] = ', '.join(book_row['authors'])
                if isinstance(book_row.get('publisher'), list):
                    book_row['publisher'] = ', '.join(book_row['publisher'])
                writer.writerow(book_row)
        
        # Upload to Google Drive
        return upload_to_google_drive(temp_file, file_name)
        
    except Exception as e:
        logger.error(f"Error in upload_search_results_to_drive: {e}", exc_info=True)
        return None
    finally:
        if temp_file and os.path.exists(temp_file):
            try:
                os.unlink(temp_file)
            except Exception as e:
                logger.warning(f"Failed to delete temporary file {temp_file}: {e}", exc_info=True)


def validate_port(port_str):
    """
    Validate the given port string to ensure it is a numeric value within the valid port range (1-65535).

    Args:
        port_str (str): The port number as a string.

    Returns:
        int: The validated port number as an integer.
    """
    try:
        port = int(port_str)
        if port < 1 or port > 65535:
            raise ValueError(f"Port {port} is out of valid range (1-65535)")
        return port
    except ValueError:
        raise ValueError(f"Invalid port number: {port_str}. Must be an integer between 1-65535.")

# Note: extract_book_info and get_api_key functions are already defined earlier in the file

# This function is already defined in the setup_routes function
# No need to redefine it here

# Add this to the bottom of your app.py file

# Application entry point
if __name__ == "__main__":
    # Create Flask app
    app = create_app()
    
    # Get port from environment or use default
    port = validate_port(os.environ.get("PORT", "5000"))
    
    # Log startup info
    logger.info(f"Starting server on port {port} in debug mode")
    
    # Run the app
    app.run(host="0.0.0.0", port=port, debug=True)
