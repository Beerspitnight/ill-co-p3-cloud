import os
import toml

# Define the path to the secrets file
SECRETS_PATH = "/Users/bmcmanus/Documents/my_docs/portfolio/secrets/secrets.toml"

def load_environment():
    """Load environment variables from the secrets TOML file"""
    try:
        # Load secrets from TOML file
        secrets = toml.load(SECRETS_PATH)
        
        # Set environment variables from secrets
        os.environ["FIREBASE_ADMIN_CREDENTIAL_PATH"] = SECRETS_PATH  # We'll extract Firebase creds directly
        
        # Set OpenAI API key
        os.environ["OPENAI_API_KEY"] = secrets["OPENAI"]["OPENAI_API_KEY"]
        
        # Set Google Books API key
        os.environ["GOOGLE_BOOKS_API_KEY"] = secrets["GOOGLE"]["GOOGLE_BOOKS_API_KEY"]
        
        # Set Firebase database URL (using a default if not in secrets)
        os.environ["FIREBASE_DATABASE_URL"] = secrets.get("FIREBASE_CONFIG", {}).get(
            "databaseURL", "https://ill-co-p3-learns-default-rtdb.firebaseio.com"
        )
        
        print("✅ Environment loaded from secrets.toml")
        return True
    except Exception as e:
        print(f"⚠️ Error loading environment: {e}")
        return False

# Load environment on module import
environment_loaded = load_environment()

def get_firebase_credentials():
    """Get the Firebase credentials dictionary from the TOML file"""
    try:
        secrets = toml.load(SECRETS_PATH)
        return secrets["FIREBASE"]
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