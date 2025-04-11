# 🔐 auth.py
import firebase_admin
from firebase_admin import auth, credentials
import os
import streamlit as st
import smtplib
from email.message import EmailMessage
from learning_app.utils.config import get_firebase_credentials

# Add the CREDENTIALS dictionary to validate simple logins
CREDENTIALS = {
    "demo": "demo123",
    "artuser": "art123",
    "admin": "admin123",
    "test": "test123",
    "bmcmanus": "123"  # This was in your example earlier
}

# Only initialize once
if not firebase_admin._apps:
    try:
        # Get Firebase credentials directly from the config module
        cred_dict = get_firebase_credentials()
        
        if not cred_dict:
            raise ValueError("Missing Firebase credentials")
            
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
        print("✅ Firebase Auth initialized")
    except Exception as e:
        print(f"⚠️ Firebase admin initialization error: {e}")

def verify_firebase_login(email, password):
    """Verify login credentials with Firebase Auth"""
    try:
        # Since this is server-side, we need to use Firebase Admin SDK
        # First check if the user exists
        user = auth.get_user_by_email(email)
        # If user exists but not verified, return None with special code
        if not user.email_verified:
            print(f"⚠️ Email not verified for {email}")
            return None
        
        # We can't check the password with Admin SDK directly
        # In a production app, this would use Firebase Auth REST API
        # or a client-side authentication flow
        
        # For demo purposes, return a mock token
        return {
            "idToken": "mock-firebase-token",
            "email": email,
            "displayName": user.display_name or email.split("@")[0]
        }
    except Exception as e:
        print(f"Firebase auth error: {e}")
        return None

def login_user(email, password):
    """Universal login function that handles both simple and Firebase logins"""
    # First check if it's a simple username/password (for demo users)
    username = email.split('@')[0] if '@' in email else email
    
    if username in CREDENTIALS and CREDENTIALS[username] == password:
        return {
            "display_name": username.capitalize(),
            "email": f"{username}@example.com",
            "uid": f"local-{username}",  # Added a UID for local users
            "auth_type": "simple"
        }
    
    # Otherwise try Firebase
    try:
        # First check if user exists in Firebase
        try:
            user = auth.get_user_by_email(email)
            uid = user.uid
            display_name = user.display_name or email.split('@')[0]
            
            # For demo purposes, assume password is correct (since we can't verify with Admin SDK)
            # In production, you'd use Firebase Auth REST API
            return {
                "display_name": display_name,
                "email": email,
                "uid": uid,  # Important: Include the UID
                "auth_type": "firebase"
            }
        except Exception as e:
            print(f"Firebase auth error: {e}")
            return None
    except Exception as e:
        print(f"Login error: {e}")
        return None
        
    return None

def create_user(email, password, display_name):
    """Create a new user in Firebase and send verification email"""
    try:
        # Create the user in Firebase
        user = auth.create_user(
            email=email,
            password=password,
            display_name=display_name,
            email_verified=False
        )
        
        # Send verification email
        email_sent = send_verification_email(email)
        
        # Return the user details and email status
        return {
            "uid": user.uid,
            "email": user.email,
            "display_name": display_name,
            "verified": False,
            "email_sent": email_sent
        }
    except Exception as e:
        print(f"❌ Account creation error: {e}")
        return False

def send_verification_email(recipient_email):
    """
    Sends an email verification link to the given email using Gmail SMTP.
    Assumes Firebase Admin SDK is initialized and .env contains Gmail credentials.
    """

    # Step 1: Generate Firebase verification link
    try:
        verify_link = auth.generate_email_verification_link(recipient_email)
    except Exception as e:
        print(f"❌ Failed to generate verification link: {e}")
        return False

    # Step 2: Send it via Gmail
    try:
        EMAIL_ADDRESS = os.getenv("GMAIL_USER")  # your Gmail address
        EMAIL_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")  # 16-char app password

        msg = EmailMessage()
        msg['Subject'] = "Verify Your Ill-Co-P3 Account"
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = recipient_email
        msg.set_content(f"""
Hi there!

Thank you for creating an account with Ill-Co-P3.

Please verify your email address by clicking the link below:
{verify_link}

If you did not request this, you can ignore this message.

– The Ill-Co-P3 Team
        """.strip())

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)

        print(f"✅ Verification email sent to {recipient_email}")
        return True

    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False

# Add additional auth helper functions for streamlit integration
def is_logged_in():
    """Check if user is logged in based on session state"""
    return st.session_state.get("user") is not None

def login_form():
    """Display login form"""
    st.title("Login Required")
    st.write("Please log in to access the tagging interface.")
    
    with st.form("login_form"):
        email = st.text_input("Email or Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            user = login_user(email, password)
            if user:
                st.session_state["user"] = user
                return True
            st.error("Invalid credentials")
    return False

def logout_button():
    """Display logout button"""
    if st.button("Logout", key="logout_btn"):
        st.session_state.pop("user", None)
        st.session_state.pop("image_index", None)
        st.rerun()
