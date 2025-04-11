import openai
import streamlit as st
import os
from pathlib import Path

# Load the prompt template using absolute paths
try:
    # First attempt - using pathlib to get the correct path
    base_dir = Path(__file__).resolve().parents[2]  # Go up to project root
    prompt_path = base_dir / "learning_app" / "utils" / "ai_prompts" / "gpt_tagging_prompt.txt"
    
    # Second attempt - try the direct path if the first fails
    if not prompt_path.exists():
        prompt_path = Path("/Users/bmcmanus/Documents/my_docs/portfolio/ill-co-p3.2/learning_app/utils/ai_prompts/gpt_tagging_prompt.txt")
    
    # Read the file if it exists
    if prompt_path.exists():
        with open(prompt_path, "r") as f:
            BASE_PROMPT = f.read()
        print(f"✅ Loaded GPT prompt from {prompt_path}")
    else:
        # Fallback prompt if file doesn't exist
        BASE_PROMPT = "Please analyze this image and suggest art elements and principles that apply."
        print(f"⚠️ Could not find prompt file at {prompt_path}, using default prompt")
        
except Exception as e:
    print(f"⚠️ Error loading GPT prompt: {e}")
    BASE_PROMPT = "Please analyze this image and suggest art elements and principles that apply."

# Load OpenAI API key from various sources
try:
    # First, try direct access to Streamlit secrets
    openai.api_key = st.secrets["OPENAI_API_KEY"]
    print("✅ Using Streamlit secrets for OpenAI API key")
except (KeyError, FileNotFoundError):
    try:
        # Then, try nested secrets structure
        openai.api_key = st.secrets["OPENAI"]["api_key"]
        print("✅ Using nested Streamlit secrets for OpenAI API key")
    except (KeyError, FileNotFoundError):
        # Finally, fall back to .env file
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("❌ OpenAI API key not found. Please set OPENAI_API_KEY in your environment or Streamlit secrets.")
        else:
            openai.api_key = api_key
            print("⚠️ Using local .env file for OpenAI API key")

# Update the generate_tag_suggestion function to use the new OpenAI API syntax
def generate_tag_suggestion(caption: str, image_url: str = None) -> str:
    """Generate tagging suggestions using GPT-4 based on image caption and url"""
    # Allow the function to work with just a prompt if that's all that's provided
    if image_url and caption:
        user_context = f"\n\nImage Caption: {caption}\nImage URL: {image_url}"
        full_prompt = BASE_PROMPT + user_context
    else:
        # If a single string is passed (for backward compatibility)
        full_prompt = caption
    
    try:
        # Updated to use the new OpenAI API syntax
        response = openai.chat.completions.create(  # Changed from openai.ChatCompletion.create
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You're an expert art teacher helping with tagging visual elements."},
                {"role": "user", "content": full_prompt}
            ],
            temperature=0.7
        )
        
        # Updated to access the response content correctly
        result = response.choices[0].message.content
        return result
    except Exception as e:
        error_msg = f"Error generating suggestion: {str(e)}"
        print(f"❌ {error_msg}")
        return error_msg
