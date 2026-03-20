# Expense Tracker App

## What is this

A local Python-based expense tracking system that:
- connects to Google Sheets for storing and reading expenses,
- connects to SimpleFin (via `SIMPLEFIN_URL`) for import of banking data,
- applies categorization rules to each transaction,
- supports retraining and audit operations.

The code is intentionally split into small modules to keep responsibilities clear.

## What it does

- `expense_tracker.py`: Google Sheets CRUD + sync logic
- `simplefin_integration.py`: orchestrates the workflow (env load, track, categorize, auditable output)
- `categorizer_system.py`: rule-based categorization engine for expense descriptions
- `retrain_model.py`: refresh/rebuild category model from sheet data
- `audit.py`: audit and reporting over stored transactions

## Prerequisites

1. Python 3.10+ installed
2. `pip` dependencies:
   - `google-auth`
   - `google-auth-oauthlib`
   - `google-api-python-client`
   - `python-dotenv`
   - `requests`

3. Local config:
   - `.env` (do not commit):
     - `SIMPLEFIN_URL` (full SimpleFin access URL)
     - `SPREADSHEET_ID` (Google Sheets ID)
   - `credentials.json` (Google OAuth client secret file, keep local)

## Setup

```bash
git clone https://github.com/<your-user>/<your-repo>.git
cd Expense\ Tracker\ App
python -m pip install --upgrade pip
python -m pip install google-auth google-auth-oauthlib google-api-python-client python-dotenv requests
# create .env with your values
# place credentials.json in this folder
```

## Run

```bash
python simplefin_integration.py
```

For targeted actions:

```bash
python audit.py
python retrain_model.py
python categorizer_system.py
```

## Security notes

- Keep `credentials.json`, `token.pickle`, `.env` off repository.
- If any secret is accidentally pushed, rotate and remove from history immediately.

## Why this repo is useful

- Works as a lightweight analytics pipeline for small business expense data.
- Easy to inspect and modify categorization rules.
- Can be adapted to additional data providers and spreadsheet templates.

## Logic and implementation details

### Data flow

1. `simplefin_integration.py` starts the process:
   - reads `.env` values using `python-dotenv`
   - pulls `SIMPLEFIN_URL` and `SPREADSHEET_ID`
   - instantiates `ExpenseTracker`
2. `expense_tracker.py` handles Google Sheets access:
   - authenticates using `credentials.json` and `token.pickle`
   - reads existing expense rows into memory
   - writes updates/insertions back to the worksheet
3. `categorizer_system.py` assigns categories:
   - each transaction description runs through ordered rule blocks
   - rules match keywords for travel, hotels, production, etc.
   - fallback category uses learned or default value
4. `retrain_model.py` uses sheet data to rebuild category term mapping:
   - data from the sheet is parsed and aggregated
   - fresh category labels and keyword triggers are generated
   - persistence is done in local model file (not in repository)
5. `audit.py` implements checks and summaries:
   - validates expected fields and balance totals
   - reports mismatches and potential duplicate entries

### Development history

- Initial phase: direct Google Sheets read/write (`expense_tracker.py`).
- Added external bank feed integration from SimpleFin (`simplefin_integration.py`).
- Introduced normalization and rule-based categorization (`categorizer_system.py`).
- Added retraining path using live spreadsheet data (`retrain_model.py`).
- Added audit layer to catch data quality issues (`audit.py`).

### Design decisions

- Keep sensitive credentials local via `.gitignore`.
- Keep modules independent for easier testing and replacement.
- Rule-based categorization is explicit and debuggable; path to ML if needed.
- No config in code; `SPREADSHEET_ID` and URLs are externalized.

## Project structure

- `expense_tracker.py` - Google Sheets implementation and CRUD.
- `simplefin_integration.py` - orchestrator and mediator between feed and sheet.
- `categorizer_system.py` - transaction classification rules.
- `retrain_model.py` - category model rebuild logic.
- `audit.py` - sanity checks and outputs for bookkeeping.



