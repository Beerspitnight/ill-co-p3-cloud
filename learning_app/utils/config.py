import os
import toml

# Define development mode flag
IS_DEV = os.getenv('DEVELOPMENT_MODE', 'False').lower() in ('true', '1', 't')

def load_environment():
    """Load environment variables from .env file or secrets"""
    try:
        # First try the standard streamlit secrets
        import streamlit as st
        
        # Check if we're running in Streamlit Cloud (secrets available directly)
        if hasattr(st, 'secrets') and 'FIREBASE' in st.secrets:
            print("✅ Using Streamlit Cloud secrets")
            # Set environment variables from Streamlit secrets
            os.environ['FIREBASE_ADMIN_CREDENTIAL_PATH'] = st.secrets.get('FIREBASE_ADMIN_CREDENTIAL_PATH', '')
            os.environ['FIREBASE_DATABASE_URL'] = st.secrets.get('FIREBASE', {}).get('DATABASE_URL', '')
            os.environ['OPENAI_API_KEY'] = st.secrets.get('OPENAI', {}).get('OPENAI_API_KEY', '')
            
            # When in Streamlit Cloud, create a temp credentials file from the JSON string in secrets
            if 'FIREBASE_CREDENTIALS_JSON' in st.secrets:
                import tempfile
                import json
                
                # Create a temporary file for the Firebase credentials
                fd, path = tempfile.mkstemp(suffix='.json')
                with os.fdopen(fd, 'w') as f:
                    json.dump(st.secrets['FIREBASE_CREDENTIALS_JSON'], f)
                
                # Set the path to the temp file
                os.environ['FIREBASE_ADMIN_CREDENTIAL_PATH'] = path
                print(f"✅ Created temporary Firebase credentials file at {path}")
            
            return True
            
        # If not in Streamlit Cloud or missing secrets, try local files
        print("⚠️ Streamlit secrets not found or incomplete, trying local files")
        
        # Try multiple possible locations for the secrets.toml file
        possible_paths = [
            os.path.join(os.path.dirname(__file__), '..', '..', '..', 'secrets', 'secrets.toml'),  # Portfolio/secrets
            os.path.join(os.path.dirname(__file__), '..', '..', 'secrets.toml'),  # Project root
            os.path.expanduser('~/Documents/my_docs/portfolio/secrets/secrets.toml'),  # Absolute path
            '.streamlit/secrets.toml'  # Standard Streamlit location
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                print(f"✅ Found secrets.toml at {path}")
                # Parse the TOML file manually
                with open(path, 'r') as f:
                    import toml
                    secrets_data = toml.load(f)
                
                # Set environment variables from the parsed secrets
                if 'FIREBASE' in secrets_data:
                    os.environ['FIREBASE_DATABASE_URL'] = secrets_data['FIREBASE'].get('DATABASE_URL', '')
                if 'FIREBASE_ADMIN_CREDENTIAL_PATH' in secrets_data:
                    os.environ['FIREBASE_ADMIN_CREDENTIAL_PATH'] = secrets_data['FIREBASE_ADMIN_CREDENTIAL_PATH']
                if 'OPENAI' in secrets_data and 'OPENAI_API_KEY' in secrets_data['OPENAI']:
                    os.environ['OPENAI_API_KEY'] = secrets_data['OPENAI']['OPENAI_API_KEY']
                
                return True
        
        # If not in dev mode and no credentials found, log an error
        print("❌ Could not find secrets.toml in any expected location")
        return False
        
    except Exception as e:
        print(f"⚠️ Error loading environment: {e}")
        return False

# Load environment on module import
environment_loaded = load_environment()

def get_firebase_credentials():
    """Get the Firebase credentials dictionary from Streamlit secrets or local file"""
    try:
        # First try Streamlit secrets
        import streamlit as st
        if hasattr(st, 'secrets') and 'FIREBASE' in st.secrets:
            print("✅ Using Firebase credentials from Streamlit secrets")
            return st.secrets['FIREBASE']
        
        # Fall back to local file if needed
        print("⚠️ Streamlit secrets not found, trying local files")
        # Try multiple possible locations for the secrets.toml file
        possible_paths = [
            os.path.join(os.path.dirname(__file__), '..', '..', '..', 'secrets', 'secrets.toml'),
            os.path.join(os.path.dirname(__file__), '..', '..', 'secrets.toml'),
            '.streamlit/secrets.toml'
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                print(f"✅ Found secrets.toml at {path}")
                secrets = toml.load(path)
                return secrets["FIREBASE"]
                
        print("⚠️ No Firebase credentials found")
        return {}
    except Exception as e:
        print(f"⚠️ Error loading Firebase credentials: {e}")
        return {}

def get_firebase_database_url():
    """Get the Firebase database URL from environment variables"""
    return os.getenv("FIREBASE_DATABASE_URL", 
                     "https://ill-co-p3-learns-default-rtdb.firebaseio.com")

def get_openai_api_key():
    """Get the OpenAI API key from environment variables"""
    return os.getenv("OPENAI_API_KEY")

def get_google_books_api_key():
    """Get the Google Books API key from environment variables"""
    return os.getenv("GOOGLE_BOOKS_API_KEY")