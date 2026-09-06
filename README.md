# VISTA Module 1

Digital Intake & Entity Extraction Engine for Vendor Intelligence Screening & Trust Assessment.

## Features

- Multiple PDF, DOCX, and TXT uploads
- Native PDF extraction with `pdfplumber` and scanned PDF OCR with `easyocr`
- Gemini extraction when `GEMINI_API_KEY` is configured, with deterministic local fallback
- Consolidated and deduplicated vendor profiles
- Editable Streamlit validation tables
- Normalized SQLite persistence for vendors, directors, shareholders, UBOs, and related parties
- Search by vendor name or registration number

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

Open the URL printed by Streamlit. The sidebar contains Document Upload, Validation, and Vendor Repository.

For Gemini mode, configure the API key before launching:

```powershell
$env:GEMINI_API_KEY = "your-key"
```

Without the key, the app uses the included local extractor. This is useful for development and offline demos, but production use should configure the approved AI endpoint and add review/audit controls.

## Database

The database is created at `database/vista.db` on first use. The schema is in `database/schema.sql`. Each save creates a vendor record and its associated entity records. SQLite foreign keys cascade entity cleanup when a vendor is removed.

## Sample data

`sample_data/sample_vendor.txt` can be uploaded to verify the full workflow.

## Project structure

- `app.py`: landing page and Streamlit configuration
- `pages/`: upload, validation, and repository screens
- `services/`: extraction, AI, profile-building, and database services
- `repositories/`: repository adapters for each entity family
- `models/`: typed domain dataclasses
- `database/`: schema and generated SQLite database
