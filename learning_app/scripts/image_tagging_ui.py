import streamlit as st
from datetime import datetime
import os
import json
import pandas as pd
import csv
import traceback
import logging

# Import constants from the constants file instead of dataset_interface2
try:
    from learning_app.scripts.constants import ELEMENT_OPTIONS, PRINCIPLE_OPTIONS
except ImportError:
    # Fallback if import fails
    logging.warning("Failed to import ELEMENT_OPTIONS and PRINCIPLE_OPTIONS from constants. Using fallback values.")
    ELEMENT_OPTIONS = [
        "Line", "Shape", "Form", "Color", "Value", "Space", "Texture"
    ]
    PRINCIPLE_OPTIONS = [
        "Balance", "Emphasis", "Movement", "Pattern & Repetition", 
        "Rhythm", "Proportion", "Variety", "Unity"
    ]

# Toggle to show extra dev info or test buttons
IS_DEV = False

# --- Data management functions ---
def load_export_data():
    """Load tagging export data from CSV and JSON files"""
    export_dir = "learning_app/output/pairs"
    csv_path = os.path.join(export_dir, "tagged_results_export.csv")
    json_path = os.path.join(export_dir, "tagged_results_export.json")

    try:
        # Ensure directory exists
        os.makedirs(export_dir, exist_ok=True)
        
        # Handle CSV data
        if os.path.exists(csv_path):
            with open(csv_path, "r") as f:
                csv_data = f.read()
        else:
            # Create empty CSV if file doesn't exist
            csv_data = "image_id,text,rejected,flagged,tagger,tags\n"
            with open(csv_path, "w") as f:
                f.write(csv_data)
        
        # Handle JSON data
        if os.path.exists(json_path):
            with open(json_path, "r") as f:
                json_data = json.load(f)
        else:
            # Create empty JSON if file doesn't exist
            json_data = []
            with open(json_path, "w") as f:
                json.dump(json_data, f)
        
        return csv_data, json.dumps(json_data)
                
    except Exception as e:
        print(f"Error in load_export_data: {str(e)}")
        print("Traceback:")
        traceback.print_exc()
        return "", "[]"

def export_failures():
    """Generate a CSV of failures (rejected or flagged items)"""
    input_path = "learning_app/output/pairs/tagged_results_export.json"
    output_path = "learning_app/output/pairs/tagged_results_failures.csv"

    if not os.path.exists(input_path):
        # Create an empty CSV with headers if input file doesn't exist
        pd.DataFrame(columns=["image_id", "text", "rejected", "flagged", "tagger", "tags"]).to_csv(output_path, index=False)
        return

    try:
        with open(input_path, "r") as f:
            data = json.load(f)

        # Convert data to list if it's not already
        if not isinstance(data, list):
            if isinstance(data, dict):
                # If it's a dictionary, convert its values to a list
                data = list(data.values())
            else:
                # If it's neither a list nor a dict, make an empty list
                data = []
        
        # Initialize failure_rows list
        failure_rows = []
        
        # Loop through all items in the data
        for item in data:
            # Skip items that aren't dictionaries (like simple strings)
            if not isinstance(item, dict):
                logging.warning(f"Skipping non-dictionary item: {item}")
                continue
                
            # Now safely access dictionary attributes
            if item.get("rejected") or item.get("flagged"):
                failure_rows.append({
                    "image_id": item.get("image_id", "unknown"),
                    "text": item.get("text", ""),
                    "rejected": item.get("rejected", False),
                    "flagged": item.get("flagged", False),
                    "tagger": item.get("tagger", ""),
                    "tags": json.dumps(item.get("tags", {}))
                })

        if failure_rows:
            df = pd.DataFrame(failure_rows)
            df.to_csv(output_path, index=False)
        else:
            # Create an empty CSV with headers if no failures
            pd.DataFrame(columns=["image_id", "text", "rejected", "flagged", "tagger", "tags"]).to_csv(output_path, index=False)
            
    except Exception as e:
        logging.error(f"Error exporting failures: {str(e)}")
        # Create an empty CSV with headers if there's an error
        pd.DataFrame(columns=["image_id", "text", "rejected", "flagged", "tagger", "tags"]).to_csv(output_path, index=False)

def init_exports():
    """Initialize exports at startup"""
    export_failures()

# --- Tag caching system ---
tag_cache = []

def flush_tag_cache():
    """Flush the in-memory tag cache to the files."""
    global tag_cache
    if not tag_cache:
        return

    try:
        export_dir = "learning_app/output/pairs"
        os.makedirs(export_dir, exist_ok=True)

        # Update JSON file
        json_path = os.path.join(export_dir, "tagged_results_export.json")
        try:
            with open(json_path, "r") as f:
                existing_data = json.load(f)
                if not isinstance(existing_data, list):
                    existing_data = []
        except (FileNotFoundError, json.JSONDecodeError):
            existing_data = []

        # Merge cache into existing data
        for tag_data in tag_cache:
            updated = False
            for i, item in enumerate(existing_data):
                if item.get("image_id") == tag_data["image_id"]:
                    existing_data[i] = tag_data
                    updated = True
                    break
            if not updated:
                existing_data.append(tag_data)

        # Save updated data
        with open(json_path, "w") as f:
            json.dump(existing_data, f, indent=2)

        # Update CSV file
        csv_path = os.path.join(export_dir, "tagged_results_export.csv")
        df = pd.DataFrame(existing_data)
        df.to_csv(csv_path, index=False)

        # Clear the cache
        tag_cache = []
    except Exception as e:
        print(f"Error flushing tag cache: {str(e)}")

def save_current_tags(image_item, tags, user_email, user_info=None):
    """Save the current image tags to the in-memory cache."""
    global tag_cache
    try:
        image_id = image_item.get("id", image_item.get("image_id", str(hash(image_item.get("image", "")))))
        uid = user_info.get("uid", f"email-{hash(user_email)}") if user_info else f"email-{hash(user_email)}"
        display_name = user_info.get("display_name", user_email.split('@')[0]) if user_info else user_email.split('@')[0]

        tag_data = {
            "image_id": image_id,
            "text": image_item.get("text", ""),
            "image_url": image_item.get("image", ""),
            "tags": tags,
            "tagger": user_email,
            "uid": uid,
            "display_name": display_name,
            "timestamp": pd.Timestamp.now().isoformat()
        }

        # Add to cache
        tag_cache.append(tag_data)

        # Optionally flush cache if it exceeds a certain size
        if len(tag_cache) >= 10:  # Adjust the batch size as needed
            flush_tag_cache()
        return True
    except Exception as e:
        print(f"Error saving tags: {str(e)}")
        return False

# --- Error handling for offensive content ---
def try_mark_as_offensive(item, email):
    """Safely mark an image as offensive with error handling"""
    try:
        mark_as_offensive(item, email)
    except Exception as e:
        import traceback
        error_message = f"Error marking image as offensive: {e}"
        print(error_message)
        traceback.print_exc()
        st.error(error_message)

def mark_as_offensive(item, user_email):
    """Mark an image as offensive and log it for removal"""
    try:
        # Create offensive images directory if it doesn't exist
        output_dir = "learning_app/output/offensive_images"
        os.makedirs(output_dir, exist_ok=True)
        
        # Create or append to offensive images log
        log_path = os.path.join(output_dir, "offensive_images.csv")
        
        # Prepare data
        timestamp = datetime.now().isoformat()
        image_id = item.get("id", item.get("image_id", str(hash(item.get("image", "")))))
        item_data = {
            "timestamp": timestamp,
            "image_id": image_id,
            "image_url": item.get("image", ""),
            "text": item.get("text", ""),
            "flagged_by": user_email
        }
        
        # Append directly to the CSV file
        file_exists = os.path.exists(log_path)
        with open(log_path, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["timestamp", "image_id", "image_url", "text", "flagged_by"])
            if not file_exists:
                writer.writeheader()  # Write header only if file doesn't exist
            writer.writerow(item_data)
        
        # Also save to a JSON file for backup
        json_path = os.path.join(output_dir, "offensive_images.json")
        try:
            with open(json_path, "r") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = []
        data.append(item_data)
        
        with open(json_path, "w") as f:
            json.dump(data, f, indent=2)
            
        # Update the image item with offensive flag in firebase if available
        item_with_flag = {**item, "offensive": True}
        
        # Call appropriate save function - using flag_image instead of save_tags_to_firebase
        try:
            flag_image(item_with_flag, user_email, flag_type="rejected")
        except Exception as e:
            print(f"Error flagging image in Firebase: {str(e)}")
            # Continue execution even if Firebase update fails
        
        return True
    except Exception as e:
        print(f"Error marking image as offensive: {str(e)}")
        return False

def flag_image(image_item, user_email, flag_type="flagged"):
    """Flag or reject an image"""
    try:
        # Prepare data for saving
        image_id = image_item.get("id", image_item.get("image_id", str(hash(image_item.get("image", "")))))
        
        tag_data = {
            "image_id": image_id,
            "text": image_item.get("text", ""),
            "image_url": image_item.get("image", ""),
            "tags": {},
            "tagger": user_email,
            "timestamp": pd.Timestamp.now().isoformat(),
            "flagged": flag_type == "flagged",
            "rejected": flag_type == "rejected"
        }
        
        # Define the export directory and json path
        export_dir = "learning_app/output/pairs"
        json_path = os.path.join(export_dir, "tagged_results_export.json")
        
        # Load existing data
        try:
            with open(json_path, "r") as f:
                existing_data = json.load(f)
                # Ensure the data is a list
                if not isinstance(existing_data, list):
                    existing_data = []
        except (FileNotFoundError, json.JSONDecodeError):
            existing_data = []
        
        # Check if this image already exists in the data
        updated = False
        for i, item in enumerate(existing_data):
            if isinstance(item, dict) and item.get("image_id") == image_id:
                existing_data[i] = tag_data
                updated = True
                break
                
        if not updated:
            existing_data.append(tag_data)
            
        # Save updated data
        with open(json_path, "w") as f:
            json.dump(existing_data, f, indent=2)
            
        # Update failures export
        export_failures()
        
        return True
    except Exception as e:
        print(f"Error flagging image: {str(e)}")
        return False

# --- UI component rendering ---
def render_download_ui(session_id=None):
    """Render download buttons with unique keys based on session_id"""
    st.sidebar.markdown("## 📥 Download Your Exports")
    
    # Generate a unique suffix for keys
    key_suffix = f"_{session_id}" if session_id else f"_{int(datetime.now().timestamp())}"
    
    # Get timestamp for filenames
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    csv_data, json_data = load_export_data()
    
    st.sidebar.download_button(
        label="⬇️ Download CSV Export",
        data=csv_data,
        file_name=f"tagged_results_export_{timestamp}.csv",
        mime="text/csv",
        key=f"download_csv_button{key_suffix}"
    )
    
    st.sidebar.download_button(
        label="⬇️ Download JSON Export",
        data=json_data,
        file_name=f"tagged_results_export_{timestamp}.json",
        mime="application/json",
        key=f"download_json_button{key_suffix}"
    )
    
    failures_path = "learning_app/output/pairs/tagged_results_failures.csv"
    if os.path.exists(failures_path):
        with open(failures_path, "r") as f:
            failure_csv = f.read()
        
        st.sidebar.download_button(
            label="⚠️ Download Failures Only (CSV)",
            data=failure_csv,
            file_name=f"tagged_results_failures_{timestamp}.csv",
            mime="text/csv",
            key=f"download_failures_button{key_suffix}"
        )

def render_tagging_ui(image_data, user_info, current_index=0):
    """Render the main image tagging interface"""
    # Run initialization tasks
    init_exports()
    
    # Display app header and logo
    st.markdown("""
    <div style="
        display: flex;
        justify-content: center;
        align-items: center;
        padding: 20px;
    ">
        <img src="logo.png" width="150" onerror="this.onerror=null; this.src='https://raw.githubusercontent.com/Beerspitnight/ill-co-p3-cloud/048332999fbee394df358cace117351217ddd14c/assets/logo.png';this.style.padding='10px';" style="
            border-radius: 12px;
            box-shadow: 0 0 20px rgba(0, 255, 255, 0.4);
            background-color: #111;
            padding: 10px;
        "/>
    </div>
    """, unsafe_allow_html=True)
    
    # Apply custom styling for UI elements
    st.markdown("""
    <style>
        /* Make buttons larger and more prominent */
        .stButton > button {
            font-size: 48px;
            padding: 1.25rem 2.5rem;
            height: auto;
            min-height: 80px;
        }
        
        /* Target the specific buttons directly */
        button[kind="secondary"] {
            font-size: 48px;
            font-weight: bold;
            padding: 1.25rem 2.5rem;
        }
        
        /* Save button styling */
        button[data-label="Save Tags"] {
            background-color: #4CAF50;
            color: white;
            font-weight: bold;
            min-height: 100px;
        }
        
        /* Navigation buttons */
        button[data-label="Previous"], button[data-label="Next"] {
            font-weight: bold;
            min-height: 90px;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Basic validation
    if not isinstance(image_data, list):
        st.error("Expected a list of images but received a single item or wrong type")
        return
        
    if not image_data or current_index >= len(image_data):
        st.error("No images available or index out of range")
        return
    
    # Get current item
    current_item = image_data[current_index]
    
    # Set current image data in session state for proper flagging visualization
    st.session_state.current_image_data = current_item
    
    # Display progress
    progress_text = f"Image {current_index + 1} of {len(image_data)}"
    st.progress((current_index + 1) / len(image_data))
    st.markdown(f"#### {progress_text}")
    
    # Create columns for layout
    col1, col2 = st.columns([0.6, 0.4])

    # Initialize form variables
    primary_element = ELEMENT_OPTIONS[0]
    secondary_element = "None"
    primary_principle = PRINCIPLE_OPTIONS[0]
    secondary_principle = "None"
    quality = "Medium"
    issues = []
    irrelevant = False
    notes = ""
    
    # Define save_state function
    def save_state():
        # Collect tag data
        save_tags = {
            "primary_element": primary_element,
            "secondary_element": secondary_element,
            "primary_principle": primary_principle,
            "secondary_principle": secondary_principle,
            "quality": quality,
            "issues": issues,
            "irrelevant": irrelevant,
            "notes": notes
        }
        
        # Save to Firebase
        try:
            from learning_app.utils.firebase_service import save_tag_to_firebase
            
            # Generate image ID
            if "image_filename" in current_item:
                image_id = current_item["image_filename"]
            elif "image" in current_item and current_item["image"]:
                url_parts = current_item["image"].split("/")
                image_id = url_parts[-1].replace(".", "_")
            else:
                image_id = str(hash(current_item.get("text", "") + str(current_index)))
            
            # Ensure user_info contains an email key
            user_email = user_info.get("email", "unknown_user@example.com")
            
            # Prepare data for Firebase
            firebase_data = {
                "text": current_item.get("text", ""),
                "image_url": current_item.get("image", ""),
                "tags": save_tags,
                "tagger": user_email,
                "timestamp": pd.Timestamp.now().isoformat()
            }
            
            # Save to Firebase
            save_tag_to_firebase(image_id, firebase_data)
            st.toast("Tags saved", icon="✅")
        except Exception as e:
            logging.error(f"Firebase save failed: {e}")
            st.error("Failed to save tags to Firebase. Please try again later or contact support.")
            import traceback
            error_message = f"Firebase save failed: {e}"
            print(error_message)
            traceback.print_exc()
            st.error(f"An error occurred while saving to Firebase: {error_message}")
        
        # Save to local storage
        return save_current_tags(current_item, save_tags, user_info["email"], user_info)
    
    # Render UI components
    with col1:
        # Display the image
        image_url = current_item.get("image", current_item.get("image_url", ""))
        if image_url:
            st.image(image_url, use_container_width=True)
        else:
            st.warning("No image available")
            
        # Display the text
        text = current_item.get("text", current_item.get("caption", "No caption available"))
        st.markdown(f"**Caption:** {text}")
        
        # Add Next/Previous buttons under the image
        prev_col, next_col = st.columns(2)
        with prev_col:
            prev_disabled = current_index <= 0
            if st.button("⬅️ Previous", use_container_width=True, disabled=prev_disabled):
                save_state()
                st.session_state.image_index = current_index - 1
                st.rerun()
                
        with next_col:
            next_disabled = current_index >= len(image_data) - 1
            if st.button("➡️ Next", use_container_width=True, disabled=next_disabled):
                save_state()
                st.session_state.image_index = current_index + 1
                st.rerun()
    
    # Right column for tagging options
    with col2:
        left_col, right_col = st.columns([1, 1])
        
        # Right column - Art Elements and Principles
        with right_col:
            st.markdown("### Elements of Art & Design")
            primary_element = st.selectbox(
                "Primary Element", 
                options=ELEMENT_OPTIONS,
                key=f"primary_element_{current_index}",
                on_change=save_state
            )
            
            secondary_element = st.selectbox(
                "Secondary Element", 
                options=["None"] + ELEMENT_OPTIONS,
                key=f"secondary_element_{current_index}",
                on_change=save_state
            )
        
            st.markdown("### Principles of Art & Design")
            primary_principle = st.selectbox(
                "Primary Principle", 
                options=PRINCIPLE_OPTIONS,
                key=f"primary_principle_{current_index}",
                on_change=save_state
            )
            
            secondary_principle = st.selectbox(
                "Secondary Principle", 
                options=["None"] + PRINCIPLE_OPTIONS,
                key=f"secondary_principle_{current_index}",
                on_change=save_state
            )
        
        # Left column - Quality and Issues
        with left_col:
            st.markdown("### Image Quality")
            quality = st.radio(
                "Quality Rating", 
                ["High", "Medium", "Low"], 
                key=f"quality_{current_index}",
                on_change=save_state
            )
            
            st.markdown("### Issues")
            issues = []
            
            # Issue checkboxes
            blurry = st.checkbox("Blurry", key=f"issue_blurry_{current_index}", on_change=save_state)
            if blurry:
                issues.append("blurry")
                
            watermark = st.checkbox("Watermark", key=f"issue_watermark_{current_index}", on_change=save_state)
            if watermark:
                issues.append("watermark")
                
            text_overlay = st.checkbox("Text Overlay", key=f"issue_text_{current_index}", on_change=save_state)
            if text_overlay:
                issues.append("text_overlay")
                
            # Irrelevant image checkbox
            st.markdown("")
            irrelevant = st.checkbox(
                "🚫 Image Irrelevant/Missing", 
                key=f"irrelevant_{current_index}", 
                help="Check if the image is missing or not relevant to the caption",
                on_change=save_state
            )
            if irrelevant:
                issues.append("irrelevant")
                
            # Offensive content button
            st.markdown("")
            if st.button(
                "⚠️ Mark as Offensive", 
                key=f"offensive_{current_index}", 
                on_click=lambda: try_mark_as_offensive(current_item, user_info["email"])
            ):
                st.warning("Image marked as offensive and will be removed from circulation")
                # Move to next image if available
                if current_index < len(image_data) - 1:
                    st.session_state.image_index = current_index + 1
                    st.rerun()
        
        # Notes section
        st.markdown("### Notes")
        notes = st.text_area("Additional Notes", key=f"notes_{current_index}", height=100, on_change=save_state)
        
        # Action buttons for saving
        st.markdown("---")
        if st.button("💾 Save Tags", use_container_width=True):
            save_state()
            st.success("Tags saved successfully!")

    # Set up autosave functionality
    if "last_autosave_index" not in st.session_state or "last_autosave_time" not in st.session_state:
        st.session_state.last_autosave_index = current_index
        st.session_state.last_autosave_time = datetime.now()
        st.session_state.last_autosave_hash = None

    # Prepare current state for comparison
    current_state = {
        "primary_element": primary_element,
        "secondary_element": secondary_element,
        "primary_principle": primary_principle,
        "secondary_principle": secondary_principle,
        "quality": quality,
        "issues": issues,
        "irrelevant": irrelevant,
        "notes": notes,
    }
    current_state_hash = hash(json.dumps(current_state, sort_keys=True))

    if "last_autosave_hash" not in st.session_state:
        st.session_state.last_autosave_hash = current_state_hash

    # Autosave if changes detected and more than 30 seconds passed
    if (
        (datetime.now() - st.session_state.last_autosave_time).seconds > 30
        and current_state_hash != st.session_state.last_autosave_hash
    ):
        save_state()
        st.session_state.last_autosave_time = datetime.now()
        st.session_state.last_autosave_hash = current_state_hash
        st.toast("Changes autosaved", icon="✅")