import os
import json
import firebase_admin
from firebase_admin import credentials, db, storage, firestore
import streamlit as st
from datetime import datetime
from learning_app.utils.config import get_firebase_credentials, get_firebase_database_url

# Initialize Firebase Admin SDK
if not firebase_admin._apps:
    try:
        # Get Firebase credentials directly from the config module
        cred_dict = get_firebase_credentials()
        db_url = get_firebase_database_url()
        
        if not cred_dict:
            raise ValueError("Missing Firebase credentials")
            
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred, {
            "databaseURL": db_url
        })
        print("✅ Firebase Admin SDK initialized")
    except Exception as e:
        print(f"❌ Failed to initialize Firebase: {e}")

# === SAVE TAG TO FIREBASE ===
def save_tag_to_firebase(image_id, tag_data):
    try:
        user = st.session_state.get("user", {})
        uid = user.get("uid")
        display_name = user.get("display_name")

        if not uid:
            print("No UID found in session — aborting tag save.")
            return

        # Clean the image_id to ensure it's valid for Firebase
        # Replace any special characters that Firebase doesn't allow in paths
        clean_image_id = image_id.replace(".", "_").replace("/", "_").replace("#", "_").replace("$", "_")
        
        # Inject UID and display name into tag data
        tag_entry = {
            "uid": uid,
            "display_name": display_name,
            "timestamp": datetime.utcnow().isoformat(),
            **tag_data
        }

        # Save under /tags/{image_id}/{uid} - using the cleaned image_id
        ref = db.reference(f"tags/{clean_image_id}/{uid}")
        ref.set(tag_entry)
        print(f"✅ Tag saved for {clean_image_id} by {display_name} ({uid})")

    except Exception as e:
        print(f"❌ Failed to save tag: {e}")

def save_tag_to_firebase(image_id, data):
    """Save tag data to Firebase with user identification"""
    try:
        # Ensure uid and display_name are present
        if 'tagger' in data and 'uid' not in data:
            # Add uid if missing but we have email
            data['uid'] = data.get('uid', f"email-{hash(data['tagger'])}")
            
        if 'tagger' in data and 'display_name' not in data:
            # Extract display name from email if missing
            email = data['tagger']
            data['display_name'] = email.split('@')[0]
            
        # Clean image_id for Firebase (remove special characters)
        clean_id = ''.join(c if c.isalnum() or c in '-_' else '_' for c in str(image_id))
        
        # Save to Firebase
        db = firestore.client()
        db.collection('image_tags').document(clean_id).set(data, merge=True)
        return True
    except Exception as e:
        print(f"❌ Firebase save error: {str(e)}")
        return False


# === GET ALL TAGS FOR ONE IMAGE ===
def get_tags_for_image(image_id):
    try:
        ref = db.reference(f"tags/{image_id}")
        return ref.get() or {}
    except Exception as e:
        print(f"❌ Failed to fetch tags for image {image_id}: {e}")
        return {}


# === GET TAGS FOR CURRENT USER ===
def get_user_tags(uid):
    try:
        ref = db.reference("tags")
        all_tags = ref.get() or {}

        user_tags = {}
        for image_id, tag_entries in all_tags.items():
            if uid in tag_entries:
                user_tags[image_id] = tag_entries[uid]

        return user_tags

    except Exception as e:
        print(f"❌ Failed to fetch user tags: {e}")
        return {}

def get_all_tags():
    """
    Retrieve all tags from Firebase (across all users and images).
    Structure:
    {
        image_id_1: {
            user_id_1: { ...tag_data... },
            user_id_2: { ...tag_data... },
        },
        image_id_2: {
            ...
        }
    }
    """
    ref = db.reference("tags")
    return ref.get() or {}

# === OPTIONAL: Upload a file to Firebase Storage ===
def upload_file_to_firebase_storage(local_file_path, remote_filename):
    try:
        bucket = storage.bucket()
        blob = bucket.blob(f"images/{remote_filename}")
        blob.upload_from_filename(local_file_path)
        blob.make_public()
        return blob.public_url
    except Exception as e:
        print(f"❌ Failed to upload file: {e}")
        return None

def get_user_tag_count(uid):
    """
    Count the total number of images tagged by a specific user
    
    Parameters:
    - uid: User ID to count tags for
    
    Returns:
    - Integer count of images tagged by this user
    """
    try:
        ref = db.reference("tags")
        all_tags = ref.get() or {}
        
        # Count images where this user has tags
        count = 0
        for image_id, tag_entries in all_tags.items():
            if uid in tag_entries:
                count += 1
                
        return count
    except Exception as e:
        print(f"❌ Failed to count user tags: {e}")
        return 0

def get_all_tag_counts():
    """
    Count the total number of unique images that have been tagged by any user
    
    Returns:
    - Integer count of total tagged images
    """
    try:
        ref = db.reference("tags")
        all_tags = ref.get() or {}
        
        # The number of tagged images is the length of the dictionary
        return len(all_tags)
    except Exception as e:
        print(f"❌ Failed to count all tags: {e}")
        return 0
