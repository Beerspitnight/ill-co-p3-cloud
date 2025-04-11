# Ill-Co-P3.2: Visual Design Tagging Tool

## 🧠 Project Summary
This project builds a dataset to fine-tune an AI model on visual design principles. Users tag image-text examples via a Streamlit interface. The project integrates Firebase for authentication, image hosting, and tagging data storage.

## 🚀 Features
- Firebase login (email/password) with email verification
- Tagging UI for image-text pairs
- Auto-save tags to Firebase Realtime DB
- Downloadable exports (JSON, CSV)
- GPT-assisted label suggestions (optional)
- Sidebar with hoverable reference examples

## 📁 Project Structure
```
ill-co-p3.2/
├── learning_app/
│   ├── data/                  # HTML and image inputs
│   ├── output/                # Enriched metadata, tag results
│   │   ├── books_enriched/    
│   │   ├── pairs/             # image_urls.json, combined_pairs.json, etc.
│   ├── scripts/               # All utility scripts
│   ├── styles/                # CSS styling
│   ├── utils/                 # GPT prompts, Firebase helpers
├── secrets/                  # ✅ Only location for secrets
│   ├── secrets.toml           # All credentials
│   ├── ill-co-p3-learns-firebase-adminsdk.json
├── dataset_interface2.py     # Streamlit UI app
├── README.md                 # You're reading it
```

## 🔐 Credentials
All secrets are loaded from:
```
/Users/bmcmanus/Documents/my_docs/portfolio/secrets/
```
Do **not** use `.env` or duplicate secrets in `.streamlit/`.

Python scripts load credentials like this:
```python
import toml
SECRETS_PATH = "/Users/bmcmanus/Documents/my_docs/portfolio/secrets/secrets.toml"
secrets = toml.load(SECRETS_PATH)

firebase_creds = secrets["FIREBASE"]
openai_key = secrets["OPENAI"]["OPENAI_API_KEY"]
google_books_key = secrets["GOOGLE"]["GOOGLE_BOOKS_API_KEY"]
```

## 🛠️ Running the App
1. Activate your virtual environment
2. Run the tagging app:
```bash
streamlit run dataset_interface2.py
```

## ✅ Script Status Overview
See `✅ Summary of All Scripts & Their Roles.docx` for details. Highlights:
- `extract_images.py`, `match_text_image.py` — ✅ Locked
- `export_firebase_tags.py` — ✅ Working
- `bulk_enrich_books.py` — 🔲 To be implemented
- `dataset_interface2.py` — ✅ Ready for tagging

## 🗃️ Outputs
- Tagged results:
  - `output/pairs/tagged_results.json`
  - `output/pairs/tagged_results.csv`
- GPT-labeled samples:
  - `output/pairs/gpt_images_labeled_sample/gpt_images_labeled_sample.json`

## 🧾 Version Control
- Locked scripts are marked with `# 🔒 LOCKED - DO NOT MODIFY`
- Backups live in `output/pairs/backups/`
- Exports are timestamped to avoid overwriting

## 🧰 Tools & Utilities

### 🔍 LibraryCloud API Test Interface

A simple local HTML interface to test your book search endpoints using Google Books and OpenLibrary.

- File: `learning_app/templates/api_s_index.html`
- Use: Load in a browser or wrap in a Flask route
- Features:
  - Search Google Books API
  - Search OpenLibrary API
  - View saved result list

To view locally, open in browser or visit `/dev/api` (if Flask route enabled).
---
**Pathfinder Project** | Built for visual design training | Powered by GPT + Firebase