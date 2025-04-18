import streamlit as st

st.set_page_config(page_title="Ill-Co Tagging", layout="wide", initial_sidebar_state="expanded")

# Configure the page first, before any other Streamlit commands
# dataset_interface.py 
# IMPORTANT: set_page_config must be the FIRST Streamlit command

# Now proceed with other imports
import os
import json
import random
import time
import openai
from learning_app.utils.config import load_environment, get_openai_api_key

# Import constants from the constants file
try:
    from learning_app.utils.constants import ELEMENT_OPTIONS, PRINCIPLE_OPTIONS
except (ModuleNotFoundError, ImportError, SyntaxError) as e:
    # Log the error and halt execution
    st.error(f"❌ Critical error: Could not import constants module due to: {e}. Please ensure the module is available and error-free.")
    st.stop()

# Define a constant at the top of your file
IS_DEV = False  # Set to False for production

# Load .env from absolute path FIRST - before any firebase imports
# Ensure environment is loaded
load_environment()

# Print environment variables for debugging (remove in production)
print(f"FIREBASE_ADMIN_CREDENTIAL_PATH: {os.getenv('FIREBASE_ADMIN_CREDENTIAL_PATH')}")
print(f"FIREBASE_DATABASE_URL: {os.getenv('FIREBASE_DATABASE_URL')}")

# NOW import Firebase-related modules after environment is loaded
from learning_app.utils.firebase_service import save_tag_to_firebase as save_tags_to_firebase, get_user_tags
from learning_app.utils.firebase_service import get_all_tag_counts, get_user_tag_count
# Print environment variables for debugging in development mode only
# NOW import Firebase-related modules after environment is loaded
from learning_app.utils.firebase_service import (
    save_tag_to_firebase as save_tags_to_firebase, 
    get_user_tags,
    get_all_tag_counts, 
    get_user_tag_count,
    create_user,
    login_user
)
# Add after your imports but before sidebar code
def create_account(email, password, display_name):
    """Centralized account creation function with validation"""
    # Basic validation
    if not email or "@" not in email or "." not in email:
        st.error("Please enter a valid email address")
        return None
        
    if not password or len(password) < 6:
        st.error("Password must be at least 6 characters")
        return None
        
    if not display_name:
        st.warning("Using email username as display name")
        display_name = email.split('@')[0]
    
    try:
        # Show a status message
        with st.spinner("Creating account..."):
            # Add debugging to see what's happening
            user_info = create_user(email, password, display_name)
            
            if user_info:
                st.success("✅ Account created successfully!")
                
                if user_info.get("email_sent", False):
                    st.info("📩 A verification email has been sent to your email address.")
                else:
                    st.warning("⚠️ We couldn't send a verification email automatically.")
                
                # Log the user in automatically
                st.session_state.user = user_info
                st.session_state.page = "tagging"
                if "image_index" not in st.session_state:
                    st.session_state.image_index = 0
                
                # Return success
                return user_info
            else:
                st.error("Could not create account. Check your password (min 6 characters) or try a different email.")
                return None
    except Exception as e:
        # Catch any uncaught errors
        st.error(f"Error during account creation: {str(e)}")
        return None

def enable_dev_mode(email=None, display_name=None):
    """Enable developer mode with a mock user"""
    if not email:
        email = "dev@example.com"
    if not display_name:
        display_name = email.split('@')[0]
        
    dev_user = {
        "uid": f"dev-{hash(email or 'default')}",
        "email": email,
        "display_name": display_name,
        "is_dev_mode": True  # Flag to identify dev mode users
    }
    st.session_state.user = dev_user
    st.session_state.page = "tagging"
    if "image_index" not in st.session_state:
        st.session_state.image_index = 0
    st.success("🧪 Developer mode enabled")
    return dev_user

# === Data Loading Function ===
@st.cache_data(ttl=3600)  # Cache for 1 hour max
def load_image_pairs():
    # Use the absolute path to the file
    base_dir = os.path.dirname(__file__)
    SAMPLE_PATH = "learning_app/output/pairs/combined_pairs_sampled_for_gpt.json"
    file_path = os.path.join(base_dir, SAMPLE_PATH)
    
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
        print(f"✅ Successfully loaded {len(data)} image pairs from {file_path}")
        
        return data
    except FileNotFoundError:
        # Try alternate locations if the primary location fails
        alternate_paths = [
            "combined_pairs_sampled_for_gpt.json",  # Current directory
            os.path.join(base_dir, "combined_pairs_sampled_for_gpt.json"),  # Project root
            os.path.join(base_dir, "learning_app", "data", "combined_pairs_sampled_for_gpt.json"),  # data directory
        ]
        
        for alt_path in alternate_paths:
            try:
                with open(alt_path, "r") as f:
                    data = json.load(f)
                print(f"✅ Successfully loaded {len(data)} image pairs from alternate path: {alt_path}")
                random.shuffle(data)
                return data
            except FileNotFoundError:
                continue
                
        # If we get here, no file was found - use a sample dataset
        print("❌ Could not find combined_pairs.json in any expected location")
        sample_data = [
            {
                "text": "Sample image description 1",
                "image": "https://via.placeholder.com/600x400.png?text=Sample+Image+1",
                "label": "unknown"
            },
            {
                "text": "Sample image description 2",
                "image": "https://via.placeholder.com/600x400.png?text=Sample+Image+2", 
                "label": "unknown"
            },
            {
                "text": "Sample image description 3",
                "image": "https://via.placeholder.com/600x400.png?text=Sample+Image+3",
                "label": "unknown"
            }
        ]
        st.warning("⚠️ Using sample data - combined_pairs.json not found")
        return sample_data

def validate_image_data(data_list):
    """Clean and validate image data before using it"""
    # Removed misleading print statement
    valid_data = []
    for item in data_list:
        # Ensure required fields exist
        if not item.get("image"):
            # Add a placeholder image URL if missing
            item["image"] = "https://placehold.co/600x400/gray/white?text=No+Image"
        
        # Ensure text/caption exists
        if not item.get("text") and not item.get("caption"):
            item["text"] = "No caption available"
            
        valid_data.append(item)
    
    return valid_data

# Use custom CSS to make the sidebar wider and style the login form
st.markdown("""
    <style>
    /* Make the sidebar wider */
    [data-testid="stSidebar"] {
        min-width: 450px !important;
        width: 450px !important;
    }
    
    /* Style the login container */
    .login-container {
        max-width: 400px;
        margin: 0 auto;
        padding: 20px;
        border-radius: 10px;
        background-color: #f5f5f5;
    }
    
    /* Style form inputs */
    div[data-testid="stTextInput"] input {
        max-width: 350px;
    }
    
    /* Center text */
    .centered-text {
        text-align: center;
        margin-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# === Firebase Setup ===
# Firebase services are already imported above
print("✅ Firebase services imported")
# No need to explicitly initialize if the module does it on import
print("✅ Firebase services imported")

# === OpenAI Setup ===
try:
    # Try to use the environment variable we set in config.py
    api_key = get_openai_api_key()
    if api_key:
        client = openai.OpenAI(api_key=api_key)
        print("✅ Using environment variable for OpenAI API key")
    else:
        try:
            # Fall back to Streamlit secrets if needed
            api_key = st.secrets["OPENAI"]["OPENAI_API_KEY"]
            client = openai.OpenAI(api_key=api_key)
            print("✅ Using Streamlit secrets for OpenAI API key")
        except KeyError:
            raise ValueError("❌ OpenAI API key is missing or invalid. Please check your environment configuration and Streamlit secrets.")
except Exception as e:
    st.error(f"❌ OpenAI API key not found: {e}")
    st.stop()

# === Initialize session state ===
if "user" not in st.session_state:
    st.session_state.user = None
if "page" not in st.session_state:
    st.session_state.page = "login"
if "image_index" not in st.session_state:
    st.session_state.image_index = 0
if "auth_mode" not in st.session_state:
    st.session_state.auth_mode = "Login"

# Add the logo at the top of the main UI
st.markdown("""
<div style="
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 20px;
">
    <img src="logo1.png" width="150" 
    onerror="this.onerror=null; this.src='assets/logo1.png'; this.style.padding='10px';" style="
        border-radius: 12px;
        box-shadow: 0 0 20px rgba(0, 255, 255, 0.4);
        background-color: #111;
        padding: 10px;
    "/>
</div>
""", unsafe_allow_html=True)

# === Sidebar with Create Account only ===
with st.sidebar:
    if "user" not in st.session_state or not st.session_state.user:
        # Only show account creation in sidebar
        st.title("✨ Create New Account")
        st.markdown("New to the platform? Create your account here to get started.")
        
        st.markdown("## ✨ Create New Account")
        st.markdown("""
        > 🧠 **Why Tag?**  
        > Help us train a visual design model by labeling images with the elements and principles of design.  
        > Go head-to-head with the algorithm — can your human intuition out-tag machine logic?  
        >This is a pet project, and my real go at programing anything.  
        >   Let's see what we can make of these elctrons! 🔮            
        >   I appreciate your 🐓ing.
                    -🍺SpitNight
        """)

        # Email / password / display name fields
        email = st.text_input("Email address", key="sidebar_email")
        password = st.text_input("Password (min 6 chars)", type="password", key="sidebar_password")
        display_name = st.text_input("Your name", key="sidebar_name")

        if st.button("Create Account", use_container_width=True):
            user_info = create_account(email, password, display_name)
            if user_info:  # If account creation was successful
                st.rerun()  # Refresh the page

    else:
        # For logged-in users, show user info and logout option
        st.title(f"👋 Welcome, {st.session_state.user.get('display_name', 'User')}")
        st.markdown(f"Logged in as: **{st.session_state.user.get('email', '')}**")
        
        if st.button("Logout", use_container_width=True):
            st.session_state.user = None
            st.session_state.page = "login"
            st.rerun()
        
        # Add a separator
        st.markdown("---")
        
        # Continue with other sidebar elements for logged-in users if needed

# === Render Art Elements Sidebar with Hover References ===
def render_art_elements_sidebar():
    """Render the art elements and principles sidebar content with hover functionality"""
    
    st.sidebar.title("📚 Elements & Principles: Quick Reference")
    qr_urls_path = os.getenv("QR_URLS_PATH", "learning_app/output/reference_qr_image_urls.json")
    try:
        # === Load image URL map ===
        qr_urls_path = "learning_app/output/reference_qr_image_urls.json"
        if os.path.exists(qr_urls_path):
            with open(qr_urls_path) as f:
                qr_urls = json.load(f)
        else:
            # Create a sample JSON structure if file doesn't exist
            qr_urls = {
                "elements/shape": "https://via.placeholder.com/300x200?text=Shape",
                "elements/line": "https://via.placeholder.com/300x200?text=Line",
                "elements/form": "https://via.placeholder.com/300x200?text=Form",
                "elements/color": "https://via.placeholder.com/300x200?text=Color",
                "elements/value": "https://via.placeholder.com/300x200?text=Value",
                "elements/space": "https://via.placeholder.com/300x200?text=Space",
                "elements/texture": "https://via.placeholder.com/300x200?text=Texture",
                "principles/balance": "https://via.placeholder.com/300x200?text=Balance",
                "principles/emphasis": "https://via.placeholder.com/300x200?text=Emphasis",
                "principles/movement": "https://via.placeholder.com/300x200?text=Movement",
                "principles/pattern_repetition": "https://via.placeholder.com/300x200?text=Pattern+Repetition",
                "principles/rhythm": "https://via.placeholder.com/300x200?text=Rhythm",
                "principles/proportion": "https://via.placeholder.com/300x200?text=Proportion",
                "principles/variety": "https://via.placeholder.com/300x200?text=Variety",
                "principles/unity": "https://via.placeholder.com/300x200?text=Unity"
            }
            os.makedirs(os.path.dirname(qr_urls_path), exist_ok=True)
            # Save the sample structure for future use
            with open(qr_urls_path, "w") as f:
                json.dump(qr_urls, f, indent=2)
            st.sidebar.info("Created sample reference image URLs - replace with actual images")
        
        # === Organize by Section ===
        ref_data = {"Elements": {}, "Principles": {}}
        for key, url in qr_urls.items():
            section, term = key.split("/")
            label = term.replace("_", " ").title()
            ref_data[section.capitalize()][label] = url
        
        # === Inject CSS for Hover Previews ===
        st.sidebar.markdown("""
        <style>
        .hover-wrapper {
            position: relative;
            margin-bottom: 10px;
        }
        .hover-term {
            font-weight: bold;
            color: #3399ff;
            cursor: pointer;
        }
        .hover-preview {
            display: none;
            position: absolute;
            z-index: 100;
            top: 1.5em;
            left: 0;
            background: #1e1e1e;
            padding: 8px;
            border: 1px solid #444;
            box-shadow: 0px 4px 10px rgba(0,0,0,0.4);
            border-radius: 6px;
        }
        .hover-wrapper:hover .hover-preview {
            display: block;
        }
        .hover-caption {
            font-size: 13px;
            color: #ccc;
        }
        .hover-preview img {
            max-width: 280px;
            border-radius: 4px;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # === Display Sidebar Quick Reference ===
        st.sidebar.markdown("### 🎨 Quick Reference")
        for section, items in ref_data.items():
            st.sidebar.markdown(f"**{section}**")
            for label, url in items.items():
                st.sidebar.markdown(
                    f"""
                    <div class="hover-wrapper">
                        <span class="hover-term">{label}</span>
                        <div class="hover-preview">
                            <img src="{url}" /><br>
                            <span class="hover-caption">Source: <a href="https://guides.lib.berkeley.edu/design" target="_blank">Berkeley Library</a></span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        
        # Add a small credit at the bottom
        st.sidebar.caption("© Art Education Resources | Berkeley Library")
        
    except Exception as e:
        st.sidebar.error(f"Error loading reference materials: {str(e)}")
        st.sidebar.info("Please make sure your reference_qr_image_urls.json file is properly formatted")

# === Main App Flow with Authentication ===
if st.session_state.page == "login":
    if st.session_state.auth_mode == "Login":
        # Center login form with container
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown('<div class="login-container">', unsafe_allow_html=True)
            st.markdown("## 🔐 Login")
            st.markdown('<p class="centered-text">Look left to get an account</p>', unsafe_allow_html=True)
            st.write("🚦Already have an account? Login here:")
            
            login_email = st.text_input("Email", key="login_email")
            login_password = st.text_input("Password", type="password", key="login_password")
            
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("Login", use_container_width=True):
                    try:
                        user = login_user(login_email, login_password)
                        if user:
                            st.session_state.user = user
                            st.session_state.page = "tagging"
                            # Initialize image index in session state
                            if "image_index" not in st.session_state:
                                st.session_state.image_index = 0
                            st.rerun()
                        else:
                            st.error("Invalid login credentials. Please try again.")
                    except Exception as e:
                        st.error(f"An error occurred during login: {str(e)}")
                    
            st.markdown('</div>', unsafe_allow_html=True)
    
    elif st.session_state.auth_mode == "Create Account":
        # Also center the create account form
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown('<div class="login-container">', unsafe_allow_html=True)
            st.title("Create New Account")
            new_email = st.text_input("New Email")
            new_password = st.text_input("New Password", type="password")
            display_name = st.text_input("Your Display Name")
            if st.button("Create Account", use_container_width=True):
                user_info = create_account(new_email, new_password, display_name)
                if user_info:  # If account creation was successful
                    st.rerun()  # Refresh the page
            st.markdown('</div>', unsafe_allow_html=True)

    
# === Tagging UI ===
elif st.session_state.page == "tagging":
    st.title("Image Tagging Platform")
    
    # Show welcome and logout option
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.success(f"Welcome {st.session_state.user.get('display_name', st.session_state.user.get('email', 'User'))}")
    
    # Add counters in the header
    with col2:
        # Add user tag counter
        user_id = st.session_state.user.get("uid")
        if user_id:
            user_tag_count = get_user_tag_count(user_id)
            st.metric("My Tags", user_tag_count)
    
    with col3:
        # Add total tags counter
        total_tag_count = get_all_tag_counts()
        st.metric("Total Tags", total_tag_count)
    
    with col2:
        if st.button("Logout"):
            st.session_state.user = None
            st.session_state.page = "login"
            st.rerun()
    
    # After confirming the user is logged in
    if "user" in st.session_state:
        user = st.session_state.user
        
        # Display instructions in an expander
        with st.expander("ℹ️ Tagging Instructions", expanded=True):
            st.markdown("""
            **Welcome to the Ill-Co-P3 Tagging Tool**

            Please tag each image-text pair using the design principles and elements you've learned. If you're unsure, trust your first impressions — this is a collaborative, crowdsourced dataset.

            ---
            ### 🖼 What if there's *no caption*?
            Some images may not include descriptive text. In that case:
            - Focus only on the **visual design**
            - Use the image itself to decide which principles or elements are present

            ---
            ### 🧩 What if I only recognize **one** design principle or element?
            That's perfectly fine!
            - You can **leave secondary tags blank**
            - Only tag what you're confident about

            ---
            ### 🧠 What if I think there are **three or more** principles or elements?
            Please choose the **most dominant** or obvious ones:
            - Select the **primary** principle/element that stands out most
            - (Optional) Add a **secondary** if another is clearly present

            We're capturing high-confidence tags for training — less is more.

            ---
            ### 🚫 When should I **reject** an image or mark it **offensive**?
            - **Reject** an image if:
              - It's low quality, blurred, or broken
              - The content is too abstract or unclear to interpret
              - It appears to be a duplicate
            - **Flag as offensive** only if:
              - The image contains nudity, violence, hate speech, or inappropriate material

            ---
            📌 **Remember:** Your tags are **saved automatically**.  
            📥 You can download your work anytime using the download buttons in the sidebar.  
            🔍 Need help? Refer to the **Quick Reference** in the sidebar for visual examples.
            """)
            
    # Cache the shuffled data to avoid unnecessary computation
    def get_shuffled_data(data):
        random.seed(int(time.time()))
    # Load image data first
    image_data = validate_image_data(load_image_pairs())
    
    # Define the shuffle function
    @st.cache_data(ttl=3600)
    def get_shuffled_data(data):
        import time
        import random
        random.seed(int(time.time()))
        random.shuffle(data)
        return data
    
        st.error("❌ No image data available. Please check your dataset or file paths. "
                 "Ensure the file exists at the specified location and is properly formatted. "
                 "Refer to the [documentation](https://example.com/docs) for more details.")
    image_data = get_shuffled_data(image_data)
    random.shuffle(image_data)
    
    idx = st.session_state.image_index

    if 0 <= idx < len(image_data):
        # Pass the ENTIRE image_data list, not just one item
        render_tagging_ui(image_data, st.session_state.user, idx)
    else:
        st.success("🎉 You've tagged all the images!")
    # === Sidebar Info with Art Elements Reference ===
    render_art_elements_sidebar()
    
    # Also add the download UI to the sidebar
    from learning_app.utils.ui_components import render_download_ui, render_tagging_ui
    render_download_ui()
    # Also add the download UI to the sidebar
    render_download_ui()
