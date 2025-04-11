# Ill-Co-P3 Tagging UI - README

## Overview
This module of the Ill-Co-P3 project implements a visual tagging interface built with Streamlit. It allows users to review image-caption pairs and apply design principle tags both manually and with AI assistance (via GPT-4-turbo with vision).

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


