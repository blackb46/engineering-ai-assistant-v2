"""
drive_loader.py
===============
City of Brentwood Engineering AI Assistant - V2
Google Drive database loader for the Streamlit application.

PURPOSE:
    The ChromaDB vector database lives on Google Drive (built by build_corpus.py
    in Google Colab). The Streamlit app runs on Streamlit Cloud, which has no
    persistent storage between restarts. Every time the app starts up, this
    module downloads the ChromaDB folder from Drive into Streamlit's temporary
    filesystem so the RAG engine can query it.

WHY THIS APPROACH:
    ┌─────────────────────┐      build_corpus.py       ┌──────────────────────┐
    │  Google Colab       │  ──────────────────────►   │  Google Drive        │
    │  (your laptop/lab)  │   writes ChromaDB files    │  vector_database/    │
    └─────────────────────┘                            └──────────┬───────────┘
                                                                   │
                                                    drive_loader.py │ downloads at startup
                                                                   ▼
                                                       ┌──────────────────────┐
                                                       │  Streamlit Cloud     │
                                                       │  /tmp/brentwood_db/  │
                                                       │  (RAG engine reads)  │
                                                       └──────────────────────┘

WHEN IT RUNS:
    Once per app startup, before the RAG engine initializes.
    Uses Streamlit's @st.cache_resource so it only runs once per
    server session, not once per user browser tab.

WHAT IT DOWNLOADS:
    The entire contents of:
        Google Drive: Brentwood_Engineering_AI_V2/vector_database/
    To local path:
        /tmp/brentwood_v2_db/   (or configurable via DRIVE_LOADER_LOCAL_PATH)

GOOGLE AUTH:
    Uses the same gcp_service_account credentials already in Streamlit secrets
    for the Google Sheets integration. No new credentials needed.
    The service account needs Drive read access (already granted).

REQUIRED STREAMLIT SECRETS:
    [gcp_service_account]       ← already present from V1
    type = "service_account"
    project_id = "..."
    private_key_id = "..."
    private_key = "..."
    client_email = "..."
    ... (all service account fields)

    DRIVE_DB_FOLDER_ID = "..."  ← NEW: Google Drive folder ID for vector_database/
                                   Get this from the Drive URL of the folder.

HOW TO GET THE FOLDER ID:
    1. Open Google Drive
    2. Navigate to: Brentwood_Engineering_AI_V2/vector_database/
    3. Look at the browser URL:
       https://drive.google.com/drive/folders/1ABC123DEF456...
    4. The string after /folders/ is the folder ID
    5. Add it to Streamlit secrets as: DRIVE_DB_FOLDER_ID = "1ABC123DEF456..."

AUTHOR:  City of Brentwood Engineering Department AI Assistant Project
VERSION: 2.0
"""

import os
import io
import time
import shutil
import datetime
from pathlib import Path

import streamlit as st


# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

# Where ChromaDB files are stored locally on Streamlit Cloud's temp filesystem.
# /tmp is always writable on Streamlit Cloud. The folder is created if missing.
LOCAL_DB_PATH = "/tmp/brentwood_v2_db"

# Minimum file age before re-downloading on restart.
# If the local database was downloaded less than this many hours ago
# (e.g. during a hot reload), skip the download to save time.
# 0 = always re-download on startup (safest — always fresh data)
# 12 = skip re-download if DB was downloaded within 12 hours
CACHE_HOURS = 0

# Expected ChromaDB files — used to verify download completeness.
# ChromaDB creates these files in its data directory.
EXPECTED_DB_FILES = [
    "chroma.sqlite3",  # main metadata and index database
]

# Google Drive API scopes needed
DRIVE_SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/spreadsheets",  # already in V1 secrets
]


# ─────────────────────────────────────────────────────────────────────────────
# GOOGLE DRIVE AUTH
# ─────────────────────────────────────────────────────────────────────────────

def _get_drive_service():
    """
    Build a Google Drive API service client using the service account
    credentials already stored in Streamlit secrets.

    This reuses the exact same auth pattern as google_sheets.py so no
    new credentials are needed.

    RETURNS:
        Google Drive service object (googleapiclient.discovery.Resource)

    RAISES:
        KeyError:   if gcp_service_account is missing from secrets
        Exception:  if credentials are invalid or Drive API is unreachable
    """
    # These imports are deferred to keep startup fast when Drive isn't needed
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=DRIVE_SCOPES,
    )

    service = build("drive", "v3", credentials=credentials, cache_discovery=False)
    return service


# ─────────────────────────────────────────────────────────────────────────────
# FILE DOWNLOAD HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _list_folder_contents(service, folder_id: str) -> list:
    """
    List all files and subfolders directly inside a Google Drive folder.

    ARGS:
        service:   Google Drive API service object
        folder_id: Drive folder ID (from the URL)

    RETURNS:
        List of dicts, each with keys: id, name, mimeType
    """
    query = f"'{folder_id}' in parents and trashed = false"
    results = service.files().list(
        q=query,
        fields="files(id, name, mimeType)",
        pageSize=200,
    ).execute()
    return results.get("files", [])


def _download_file(service, file_id: str, local_path: Path):
    """
    Download a single file from Google Drive to a local path.

    Uses the Drive API's media download (not export — these are binary files,
    not Google Docs). Streams in chunks to handle large files without
    loading everything into memory at once.

    ARGS:
        service:    Google Drive API service object
        file_id:    Drive file ID
        local_path: Where to save the file locally
    """
    from googleapiclient.http import MediaIoBaseDownload

    request = service.files().get_media(fileId=file_id)

    local_path.parent.mkdir(parents=True, exist_ok=True)

    with io.FileIO(str(local_path), "wb") as fh:
        downloader = MediaIoBaseDownload(fh, request, chunksize=10 * 1024 * 1024)
        done = False
        while not done:
            status, done = downloader.next_chunk()


def _download_folder_recursive(
    service,
    folder_id: str,
    local_dir: Path,
    depth: int = 0,
    progress_callback=None,
):
    """
    Recursively download all files in a Google Drive folder.

    ChromaDB stores its data in a flat folder (no subfolders), but this
    function handles subfolders anyway for robustness.

    ARGS:
        service:           Drive API service object
        folder_id:         Drive folder ID to download from
        local_dir:         Local directory to save files into
        depth:             Current recursion depth (for logging indentation)
        progress_callback: Optional function(filename) called as each file downloads

    RETURNS:
        (file_count, total_bytes) — number of files and total bytes downloaded
    """
    local_dir.mkdir(parents=True, exist_ok=True)
    FOLDER_MIME = "application/vnd.google-apps.folder"

    items = _list_folder_contents(service, folder_id)
    file_count = 0
    total_bytes = 0
    indent = "  " * depth

    for item in items:
        item_name = item["name"]
        item_id = item["id"]
        item_type = item["mimeType"]

        if item_type == FOLDER_MIME:
            # Recurse into subfolder
            sub_dir = local_dir / item_name
            sub_count, sub_bytes = _download_folder_recursive(
                service, item_id, sub_dir, depth + 1, progress_callback
            )
            file_count += sub_count
            total_bytes += sub_bytes

        else:
            # Download the file
            local_file = local_dir / item_name
            _download_file(service, item_id, local_file)

            file_size = local_file.stat().st_size
            total_bytes += file_size
            file_count += 1

            if progress_callback:
                progress_callback(item_name, file_size)

    return file_count, total_bytes


# ─────────────────────────────────────────────────────────────────────────────
# CACHE VALIDITY CHECK
# ─────────────────────────────────────────────────────────────────────────────

def _local_db_is_valid() -> bool:
    """
    Check whether a valid local database already exists and is recent enough
    to skip re-downloading.

    A database is considered valid when:
    1. The local directory exists
    2. The expected ChromaDB files are present
    3. The files are newer than CACHE_HOURS (if CACHE_HOURS > 0)

    RETURNS:
        True if a valid cached database exists, False otherwise.
    """
    if CACHE_HOURS == 0:
        return False  # Always re-download when cache is disabled

    db_path = Path(LOCAL_DB_PATH)
    if not db_path.exists():
        return False

    # Check that required files are present
    for expected_file in EXPECTED_DB_FILES:
        if not (db_path / expected_file).exists():
            return False

    # Check age of the sqlite3 file (most recently written by ChromaDB)
    sqlite_file = db_path / "chroma.sqlite3"
    if not sqlite_file.exists():
        return False

    age_seconds = time.time() - sqlite_file.stat().st_mtime
    age_hours = age_seconds / 3600

    return age_hours < CACHE_HOURS


def _get_local_db_stats() -> dict:
    """
    Return basic stats about the local database for status display.
    Used by the admin panel to show when the DB was last synced.
    """
    db_path = Path(LOCAL_DB_PATH)
    if not db_path.exists():
        return {"exists": False}

    sqlite_file = db_path / "chroma.sqlite3"
    if not sqlite_file.exists():
        return {"exists": False}

    mtime = sqlite_file.stat().st_mtime
    size_mb = sum(
        f.stat().st_size for f in db_path.rglob("*") if f.is_file()
    ) / (1024 * 1024)

    return {
        "exists": True,
        "last_synced": datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S"),
        "size_mb": round(size_mb, 1),
        "path": LOCAL_DB_PATH,
    }


# ─────────────────────────────────────────────────────────────────────────────
# MAIN LOADER — CALLED AT APP STARTUP
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_resource(show_spinner=False)
def load_database() -> dict:
    """
    Download the ChromaDB database from Google Drive and return its local path.

    This is decorated with @st.cache_resource so it runs ONCE per Streamlit
    server session, not once per user or browser tab. If 20 engineers have
    the app open simultaneously, the download only happens once.

    HOW TO CALL IN THE APP:
        from utils.drive_loader import load_database

        db_info = load_database()
        if db_info["success"]:
            db_path = db_info["local_path"]
            # pass db_path to RAG engine
        else:
            st.error(db_info["error"])

    RETURNS:
        dict with keys:
            success (bool):       True if database is ready
            local_path (str):     Path to local ChromaDB directory
            error (str|None):     Error message if success=False
            from_cache (bool):    True if existing local copy was reused
            files_downloaded (int): Number of files downloaded (0 if cached)
            size_mb (float):      Total database size in MB
            sync_timestamp (str): When the download completed
    """
    start_time = time.time()

    # ── Check if a valid local copy already exists ─────────────────────────
    if _local_db_is_valid():
        stats = _get_local_db_stats()
        return {
            "success":          True,
            "local_path":       LOCAL_DB_PATH,
            "error":            None,
            "from_cache":       True,
            "files_downloaded": 0,
            "size_mb":          stats.get("size_mb", 0),
            "sync_timestamp":   stats.get("last_synced", "unknown"),
            "elapsed_seconds":  round(time.time() - start_time, 1),
        }

    # ── Get the Drive folder ID from secrets ───────────────────────────────
    try:
        folder_id = st.secrets["DRIVE_DB_FOLDER_ID"]
    except KeyError:
        return {
            "success":   False,
            "local_path": LOCAL_DB_PATH,
            "error": (
                "DRIVE_DB_FOLDER_ID not found in Streamlit secrets. "
                "Add it to your secrets: DRIVE_DB_FOLDER_ID = \"your-folder-id\". "
                "Get the ID from the Google Drive URL of your vector_database/ folder."
            ),
            "from_cache":       False,
            "files_downloaded": 0,
            "size_mb":          0,
            "sync_timestamp":   None,
            "elapsed_seconds":  round(time.time() - start_time, 1),
        }

    # ── Build Drive API client ─────────────────────────────────────────────
    try:
        service = _get_drive_service()
    except KeyError:
        return {
            "success":   False,
            "local_path": LOCAL_DB_PATH,
            "error": (
                "gcp_service_account credentials not found in Streamlit secrets. "
                "These should already be present from your V1 setup."
            ),
            "from_cache":       False,
            "files_downloaded": 0,
            "size_mb":          0,
            "sync_timestamp":   None,
            "elapsed_seconds":  round(time.time() - start_time, 1),
        }
    except Exception as e:
        return {
            "success":   False,
            "local_path": LOCAL_DB_PATH,
            "error":     f"Google Drive authentication failed: {str(e)}",
            "from_cache":       False,
            "files_downloaded": 0,
            "size_mb":          0,
            "sync_timestamp":   None,
            "elapsed_seconds":  round(time.time() - start_time, 1),
        }

    # ── Clear old local database ───────────────────────────────────────────
    local_path = Path(LOCAL_DB_PATH)
    if local_path.exists():
        shutil.rmtree(str(local_path))
    local_path.mkdir(parents=True, exist_ok=True)

    # ── Download files ─────────────────────────────────────────────────────
    try:
        file_count, total_bytes = _download_folder_recursive(
            service=service,
            folder_id=folder_id,
            local_dir=local_path,
        )

    except Exception as e:
        return {
            "success":   False,
            "local_path": LOCAL_DB_PATH,
            "error":     f"Download failed: {str(e)}",
            "from_cache":       False,
            "files_downloaded": 0,
            "size_mb":          0,
            "sync_timestamp":   None,
            "elapsed_seconds":  round(time.time() - start_time, 1),
        }

    # ── Verify download completeness ───────────────────────────────────────
    missing_files = [
        f for f in EXPECTED_DB_FILES
        if not (local_path / f).exists()
    ]

    if missing_files:
        return {
            "success":   False,
            "local_path": LOCAL_DB_PATH,
            "error": (
                f"Database download incomplete. Missing files: {missing_files}. "
                "The corpus may not have been built yet. "
                "Run build_corpus.py in Google Colab first."
            ),
            "from_cache":       False,
            "files_downloaded": file_count,
            "size_mb":          round(total_bytes / (1024 * 1024), 1),
            "sync_timestamp":   None,
            "elapsed_seconds":  round(time.time() - start_time, 1),
        }

    # ── Success ────────────────────────────────────────────────────────────
    elapsed = round(time.time() - start_time, 1)
    size_mb = round(total_bytes / (1024 * 1024), 1)
    sync_ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return {
        "success":          True,
        "local_path":       LOCAL_DB_PATH,
        "error":            None,
        "from_cache":       False,
        "files_downloaded": file_count,
        "size_mb":          size_mb,
        "sync_timestamp":   sync_ts,
        "elapsed_seconds":  elapsed,
    }


# ─────────────────────────────────────────────────────────────────────────────
# STARTUP STATUS DISPLAY — called by app.py
# ─────────────────────────────────────────────────────────────────────────────

def show_loading_status():
    """
    Display a loading indicator while the database downloads, then
    show a success or error status.

    USAGE IN app.py:
        from utils.drive_loader import show_loading_status, load_database

        db_info = show_loading_status()
        if not db_info["success"]:
            st.stop()   # halt the app if database couldn't load
    """
    with st.spinner("Loading municipal engineering database from Google Drive..."):
        db_info = load_database()

    if db_info["success"]:
        if db_info["from_cache"]:
            st.success(
                f"✅ Database ready (cached — {db_info['size_mb']} MB)",
                icon="✅"
            )
        else:
            st.success(
                f"✅ Database synced from Google Drive — "
                f"{db_info['files_downloaded']} files, "
                f"{db_info['size_mb']} MB, "
                f"{db_info['elapsed_seconds']}s",
                icon="✅"
            )
    else:
        st.error(
            f"❌ Database load failed: {db_info['error']}",
            icon="❌"
        )

    return db_info


def get_db_status_for_admin() -> dict:
    """
    Return database status information for the Admin panel.

    Does NOT re-trigger the download — just reports current state.
    Shows engineers when the database was last synced from Drive
    (i.e., when corpus was last rebuilt in Colab).

    RETURNS:
        dict with: exists, last_synced, size_mb, path, collection_name
    """
    stats = _get_local_db_stats()
    stats["collection_name"] = "brentwood_engineering_v2"
    return stats


# ─────────────────────────────────────────────────────────────────────────────
# MANUAL REFRESH — for admin use
# ─────────────────────────────────────────────────────────────────────────────

def force_refresh():
    """
    Force a fresh download from Google Drive, bypassing any cache.

    Used by the Admin panel's "Refresh Database" button — lets an
    administrator trigger a sync immediately after a corpus rebuild
    without waiting for the app to restart.

    USAGE:
        from utils.drive_loader import force_refresh
        success = force_refresh()

    RETURNS:
        True if refresh succeeded, False if it failed.
    """
    # Clear the Streamlit cache so load_database() runs fresh next call
    load_database.clear()

    # Delete local copy to force re-download
    local_path = Path(LOCAL_DB_PATH)
    if local_path.exists():
        shutil.rmtree(str(local_path))

    # Re-run the download
    db_info = load_database()
    return db_info["success"]
