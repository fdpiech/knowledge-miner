# Knowledge Corpus Manager

A local Python web application that indexes, searches, and consolidates files from a OneDrive-synced knowledge corpus. Built for meeting transcripts, summaries, and supporting documents in formats like `.md`, `.docx`, `.xlsx`, `.pdf`, `.vsdx`, `.txt`, and `.csv`.

Runs entirely on your desktop with no cloud or AI dependencies.

## What It Does

- **Indexes** your corpus directory, tracking file metadata and detecting changes via SHA-256 hashing
- **Browse** the corpus as a collapsible directory tree in the browser
- **Search** by filename, file type, corpus section, date range, path, and file size -- with sortable, paginated results
- **Consolidate** search results into exportable files (Markdown, JSON, or plain text) for feeding into other tools or LLMs
- **CLI** for indexing, searching, and exporting directly from the terminal

## Prerequisites

- Python 3.11 or later

## Setup

### 1. Clone and install dependencies

```bash
git clone <repo-url> knowledge-miner
cd knowledge-miner
python -m venv .venv
```

Activate the virtual environment:

```bash
# macOS / Linux
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Windows (cmd)
.venv\Scripts\activate.bat
```

Install packages:

```bash
pip install -r requirements.txt
```

### 2. Configure your corpus path

**Option A -- environment variable (recommended for quick start):**

```bash
# macOS / Linux
export KCM_CORPUS_ROOT="/path/to/your/knowledge/corpus"

# Windows (PowerShell)
$env:KCM_CORPUS_ROOT = "C:\Users\you\OneDrive\KnowledgeCorpus"
```

**Option B -- edit `config.yaml`:**

Open `config.yaml` in the project root and set `corpus.root_path`:

```yaml
corpus:
  root_path: "C:/Users/you/OneDrive/KnowledgeCorpus"
```

### 3. Create the database

```bash
python setup_db.py
```

This creates the SQLite database at `~/.kcm/corpus.db` (configurable in `config.yaml` or via `KCM_DATABASE_PATH`).

### 4. Index your corpus

```bash
python cli.py index
```

You'll see output like:

```
Running full index of: C:/Users/you/OneDrive/KnowledgeCorpus

Index complete:
  new: 847
  updated: 0
  unchanged: 0
  deleted: 0
  total: 847
```

### 5. Start the web UI

```bash
python run.py
```

Open [http://localhost:5000](http://localhost:5000) in your browser.

## Usage

### Web UI

| Page | URL | What it does |
|------|-----|-------------|
| Dashboard | `/` | Corpus stats, file type/section breakdowns, recent files, quick actions |
| Browse | `/browse/` | Collapsible directory tree with lazy-loaded subdirectories |
| Search | `/search/` | Multi-filter search with live results, select files for export |
| Exports | `/consolidate/history` | Download history of past consolidation jobs |
| Admin | `/admin/` | Trigger full or incremental reindex |

### CLI Commands

```bash
# Full index (adds new, updates changed, removes deleted)
python cli.py index

# Incremental index (only new and changed files, faster)
python cli.py index --incremental

# Show index statistics
python cli.py stats

# Search from terminal
python cli.py search --name "budget" --ext ".xlsx" --after "2024-01-01"

# Export to file
python cli.py consolidate --name "Q4 Review" --section "norm_summaries" --format markdown
```

## Configuration

All settings live in `config.yaml`. Environment variables override the config file:

| Env Variable | Config Key | Default |
|---|---|---|
| `KCM_CORPUS_ROOT` | `corpus.root_path` | *(none -- must be set)* |
| `KCM_DATABASE_PATH` | `database.path` | `~/.kcm/corpus.db` |
| `KCM_PORT` | `server.port` | `5000` |

The indexer skips hidden files/directories and common noise (`~$*` temp files, `Thumbs.db`, `.DS_Store`). You can customize skip patterns and supported extensions in `config.yaml` under the `indexer` section.

## Project Structure

```
knowledge-miner/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── config.py            # Config loader (YAML + env vars)
│   ├── models.py            # SQLAlchemy models (files, tags, consolidation_jobs)
│   ├── indexer.py           # File system walker and metadata extractor
│   ├── search.py            # Search query builder with filtering/pagination
│   ├── consolidator.py      # Export engine (markdown, JSON, text)
│   ├── routes/              # Flask blueprints
│   │   ├── main.py          # Dashboard
│   │   ├── browse.py        # Directory tree browser
│   │   ├── search.py        # Search interface
│   │   ├── consolidate.py   # Export/consolidation endpoints
│   │   └── admin.py         # Index management
│   ├── templates/           # Jinja2 HTML templates
│   └── static/              # CSS and JS
├── cli.py                   # Click CLI (index, stats, search, consolidate)
├── run.py                   # App entry point
├── setup_db.py              # Database initialization
├── config.yaml              # Configuration file
└── requirements.txt         # Python dependencies
```

## Tech Stack

- **Backend:** Flask + SQLAlchemy + SQLite
- **Frontend:** Bootstrap 5 + htmx (CDN, no build step)
- **CLI:** Click
- **Database:** SQLite (stored at `~/.kcm/corpus.db`)
