📁 Project Root
├── dataset_interface2.py              # Main Streamlit tagging UI
├── file_tree.txt                      # Output from tree script
├── generate_file_tree.py              # Python script to generate file tree
├── requirements.txt                   # Python dependencies
├── ill-co-p3.2.code-workspace         # VSCode workspace
├── copilot_interface/                 # (Future) Adobe Illustrator Co-Pilot
│   ├── app.py
│   ├── README.md
│   ├── templates/, scripts/, utils/, tests/
├── learning_app/                      # Core tagging + training project
│   ├── data/                          # Source content (images, books, html)
│   ├── output/                        # All exports (tagged, enriched, gpt, urls)
│   ├── scripts/                       # Extraction + enrichment scripts
│   ├── search_terms/                 # CSV search inputs
│   ├── styles/, templates/, utils/   # UI layout, helpers, styling
│   ├── utility_scripts/              # Misc helpers (merge, convert, export)
│   ├── queries/                      # Archived queries or API payloads
│   ├── README.md, instructions.md
├── venv/                              # Virtual environment (✅ add to .gitignore)
├── .streamlit/secrets.toml            # Streamlit credentials (✅ don't commit!)
├── .gitignore                         # Ignores venv, pycache, etc.
