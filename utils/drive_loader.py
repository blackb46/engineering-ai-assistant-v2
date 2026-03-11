"""
drive_loader.py
===============
City of Brentwood Engineering AI Assistant - V2
Database loader for the Streamlit application.

PURPOSE:
    Provides the ChromaDB database path to the Streamlit application.

    In V2, the ChromaDB vector database is committed directly to the GitHub
    repository and read from the local filesystem at Streamlit startup.
    No Google Drive download is required.

    The database lives at:
        vector_database/   (in the root of the repo)

    Streamlit Cloud clones the repo to:
        /mount/src/engineering-ai-assistant-v2/

    So the full path at runtime is:
        /mount/src/engineering-ai-assistant-v2/vector_database/

WHY THIS APPROACH:
    Google Colab builds the database → pushes to GitHub → Streamlit reads directly.
    No Drive API permissions required.

UPDATING THE DATABASE:
    After running build_corpus.py in Google Colab, run the push step in the
    Colab notebook to commit the new database files to GitHub. Reboot the
    Streamlit app to pick up the changes.

AUTHOR:  City of Brentwood Engineering Department AI Assistant Project
VERSION: 2.1 — switched from Google Drive download to GitHub-backed local read
"""

import datetime
from pathlib import Path

import streamlit as st


# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

# Primary path: where Streamlit Cloud clones the repo
STREAMLIT_CLOUD_PATH = "/mount/src/engineering-ai-assistant-v2/vector_database"

# Fallback path: local development
LOCAL_DEV_PATH = str(Path(__file__).parent.parent / "vector_database")

# Expected files that must exist for the database to be considered valid
EXPECTED_DB_FILES = ["chroma.sqlite3"]


# ─────────────────────────────────────────────────────────────────────────────
# DATABASE LOADER
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_resource
def load_database() -> dict:
    """
    Locate the ChromaDB database on the local filesystem.

    Checks the Streamlit Cloud repo path first, then falls back to a
    local development path. No network calls or downloads required.

    RETURNS:
        dict with keys:
            success (bool):         True if database found and valid
            local_path (str):       Path to the ChromaDB directory
            error (str|None):       Error message if success=False
            from_cache (bool):      Always False (no caching layer needed)
            files_downloaded (int): Always 0 (no download)
            size_mb (float):        Total database size in MB
            sync_timestamp (str):   When the database files were last modified
    """

    # Try each candidate path
    db_path = None
    for path in [STREAMLIT_CLOUD_PATH, LOCAL_DEV_PATH]:
        p = Path(path)
        if p.exists() and p.is_dir():
            db_path = p
            break

    if db_path is None:
        return {
            "success":          False,
            "local_path":       STREAMLIT_CLOUD_PATH,
            "error": (
                "Vector database directory not found. "
                "Expected at: vector_database/ in the repository root. "
                "Run build_corpus.py in Google Colab and push the database "
                "to GitHub using the notebook push step."
            ),
            "from_cache":       False,
            "files_downloaded": 0,
            "size_mb":          0,
            "sync_timestamp":   None,
        }

    # Verify expected files exist
    missing_files = [f for f in EXPECTED_DB_FILES if not (db_path / f).exists()]

    if missing_files:
        return {
            "success":          False,
            "local_path":       str(db_path),
            "error": (
                f"Database incomplete. Missing files: {missing_files}. "
                "Run build_corpus.py in Google Colab and push to GitHub."
            ),
            "from_cache":       False,
            "files_downloaded": 0,
            "size_mb":          0,
            "sync_timestamp":   None,
        }

    # Calculate size and last-modified timestamp
    total_bytes = 0
    latest_mtime = 0
    for item in db_path.rglob("*"):
        if item.is_file():
            stat = item.stat()
            total_bytes += stat.st_size
            if stat.st_mtime > latest_mtime:
                latest_mtime = stat.st_mtime

    size_mb = round(total_bytes / (1024 * 1024), 1)
    sync_ts = (
        datetime.datetime.fromtimestamp(latest_mtime).strftime("%Y-%m-%d %H:%M")
        if latest_mtime > 0 else "unknown"
    )

    return {
        "success":          True,
        "local_path":       str(db_path),
        "error":            None,
        "from_cache":       False,
        "files_downloaded": 0,
        "size_mb":          size_mb,
        "sync_timestamp":   sync_ts,
    }


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN STATUS
# ─────────────────────────────────────────────────────────────────────────────

def get_db_status_for_admin() -> dict:
    """Return database status information for the Admin panel."""
    db_info = load_database()
    return {
        "exists":          db_info["success"],
        "last_synced":     db_info.get("sync_timestamp", "unknown"),
        "size_mb":         db_info.get("size_mb", 0),
        "path":            db_info.get("local_path", ""),
        "collection_name": "brentwood_engineering_v2",
    }


# ─────────────────────────────────────────────────────────────────────────────
# FORCE REFRESH
# ─────────────────────────────────────────────────────────────────────────────

def force_refresh() -> bool:
    """
    Clear the cached database info and re-check.
    In GitHub-backed mode there is nothing to re-download.
    """
    load_database.clear()
    db_info = load_database()
    return db_info["success"]
