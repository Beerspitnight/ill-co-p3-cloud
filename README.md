# Ill-Co-P3 Tagging UI - README

## Overview - The Project and the 🫏 2 Come.
This module of the Ill-Co-P3 project delivers a human-in-the-loop visual tagging platform built with Streamlit, powered by a Firebase backend, and structured for collaborative dataset generation and AI benchmarking.

🖼️ What It Does (Front-End)
Displays image + caption pairs loaded from Firebase Storage

Allows users to manually tag each image using dropdowns:

Primary & Secondary Design Elements

Primary & Secondary Design Principles

Supports:

Image rejection toggle for low-quality/offensive content

Free-text notes for taggers

Auto-save after every action — no Submit button required

Filter to show only untagged images

Real-time user and global tag counters

Downloadable CSV and JSON exports

Quick-reference sidebar with labeled visual examples (Elements + Principles)

🔧 What’s Under the Hood (Back-End)
Firebase Realtime Database for storing per-user tags

Firebase Storage for hosting all images

Streamlit Authenticator for secure login (email/password)

config.py loads all secrets from a private secrets.toml file (not pushed to GitHub)

Auto-save is implemented with:

save_tag_to_firebase() and get_user_tags() logic

Full tag history stored in: /tags/{image_id}/{user_id}/ in Firebase DB

Timestamped exports available via sidebar buttons

Directory structure is clean, modular, and version-controlled

🧠 The Ass End of It
Alongside the human tagging workflow, our AI assistant — powered by GPT-4 Turbo with vision — is doing the same job: analyzing image-caption pairs and predicting likely design principles and elements. These AI-generated tags are collected offline, out of view, for baseline comparison.

To henceforth and beyond, let it be DECLARED that the assistant shall be know as: AI Ass. Shortened to save tokens.  

AI Ass
or, if one prefers,
The Ass of AI

Either shall suffice.



---

## Features
- Display images hosted on Firebase from `combined_pairs.json`
- Dropdown menus for selecting visual principles and elements
- GPT-4-turbo integration to suggest tags based on image + caption
- Checkbox to flag inappropriate images or reject unusable samples
- Stores results in `tagged_results.json` for further review or training

---

## Folder Structure

```
learning_app/
├── scripts/
│   ├── image_tagging_ui.py              # Main Streamlit UI logic
│   └── suggest_labels_gpt.py            # GPT-4 image+caption classification
│
├── utils/
│   └── ai_prompts/
│       └── gpt_tagging_prompt.txt       # GPT prompt (multi-line JSON output)
│
├── output/
│   └── pairs/
│       ├── combined_pairs.json          # Input file: image-caption-Firebase URL pairs
│       ├── image_urls.json              # Firebase filename-to-URL map
│       ├── tagged_results.json          # Output: saved human+GPT tagging results
│       └── tagged_results.csv           # Output: optional CSV export for analysis
```

---

## Tag Entry Format
Each tagged image entry includes:
```json
{
  "image_filename": "page_023_img_01.png",
  "text": "...",
  "primary_principle": "Balance",
  "secondary_principle": "Emphasis",
  "primary_element": "Shape",
  "secondary_element": "Color",
  "gpt_suggestion": {
    "primary_principle": "Contrast",
    "secondary_principle": null,
    "primary_element": "Line",
    "secondary_element": null,
    "rationale": "The stark visual separation suggests contrast and line."
  },
  "rejected": false,
  "flagged": false,
  "tagger_notes": "..."
}
```

---

## Dependencies
- Streamlit
- OpenAI Python SDK
- Python 3.9+

Install requirements:
```bash
pip install openai streamlit
```

Environment config:
```
OPENAI_API_KEY=sk-xxxxx
```

---

## Usage
To launch the interface locally:
```bash
streamlit run dataset_interface2.py
```

The interface will:
- Load `combined_pairs.json`
- Display one image-caption pair at a time
- Allow human tagging + AI suggestion
- Save all results in `tagged_results.json`

---


