# 🧠 Ill-Co-P3: HTML Scrape to Training Material Pipeline

This document explains the process of converting scraped HTML tutorials or articles into usable training material for tagging and model fine-tuning.

---

## 🌐 Step 1: Crawl and Scrape Websites

**Script:** `crawl_and_scrape.py`  
**Input:** List of seed URLs or allowed domains  
**Output:** Raw HTML files  
📁 `learning_app/output/html_scrapes/*.html`

---

## 🖼️ Step 2: Extract Image + Caption Pairs

**Script:** `extract_image_captions_from_html.py`  
**Logic:**
- Finds all `<img>` tags
- Extracts captions from:
  - `alt` text
  - `<figcaption>` (if inside `<figure>`)
  - Nearby `<p>` siblings or parents

📁 `learning_app/output/pairs/html_image_caption_pairs.json`

---

## 🔀 Step 3: Merge into Dataset for Tagging

**Script:** `merge_html_into_combined_pairs.py`  
**Action:**
- Skips duplicates using `image_filename` or `image_src`
- Appends new entries with `source: "html_scrape"`

📁 `learning_app/output/pairs/combined_pairs.json`

---

## 🧾 Optional: Tag and Export

- Use `dataset_interface2.py` to tag scraped image-caption pairs
- Use `export_firebase_tags.py` to sync tagged data from Firebase

📁 `tagged_results_export.json` / `tagged_results_export.csv`

---

## 📊 Mermaid Flowchart

Paste this into a `.md` file in VS Code with Mermaid support:

```mermaid
graph TD
  A[Crawl Website] --> B[crawl_and_scrape.py]
  B --> C[HTML Files in html_scrapes/]
  C --> D[extract_image_captions_from_html.py]
  D --> E[html_image_caption_pairs.json]
  E --> F[merge_html_into_combined_pairs.py]
  F --> G[combined_pairs.json]
  G --> H[dataset_interface2.py Tagging UI]
  H --> I[Tagged Results in Firebase + Exports]
