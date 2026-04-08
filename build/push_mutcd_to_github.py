# ============================================================================
# MUTCD CORPUS PUSH TO GITHUB
# ============================================================================
# Run this cell in Google Colab AFTER rebuilding the MUTCD corpus.
#
# WHAT THIS CELL DOES:
#   1. Copies the MUTCD ChromaDB from Google Drive into the GitHub repo
#   2. Commits the database files with a timestamped message
#   3. Pushes to GitHub — Streamlit Cloud auto-deploys within ~60 seconds
#
# WHEN TO RUN:
#   - First-time setup (after running 02_build_ingest.ipynb)
#   - After re-indexing the MUTCD corpus (re-run 02_build_ingest.ipynb first)
#
# PRE-REQUISITES:
#   - Google Drive must be mounted at /content/drive
#   - GitHub Personal Access Token must be set (see GITHUB_TOKEN below)
#   - You must have write access to the repo
#
# GITHUB TOKEN:
#   Create a token at: github.com -> Settings -> Developer settings ->
#   Personal access tokens -> Tokens (classic) -> Generate new token
#   Scopes needed: repo (full)
#   Store it as a Colab secret named GITHUB_TOKEN (the lock icon in the
#   left sidebar of Colab), OR paste it directly into the variable below.
#
# FIRST-TIME SETUP NOTE:
#   The first time you run this cell, it clones the full repo (~300-500 MB
#   depending on the EPM vector database size). Subsequent runs re-use the
#   cloned repo and only push the changed MUTCD database files.
# ============================================================================

import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

# ── CONFIGURATION — edit these three values ──────────────────────────────────

# Your GitHub username
GITHUB_USERNAME = "blackb46"

# Your GitHub repo name
GITHUB_REPO = "engineering-ai-assistant-v2"

# GitHub Personal Access Token
# Option A (recommended): store as Colab secret named GITHUB_TOKEN
#   from google.colab import userdata
#   GITHUB_TOKEN = userdata.get('GITHUB_TOKEN')
# Option B: paste directly (less secure — never commit this to GitHub)
#   GITHUB_TOKEN = "ghp_your_token_here"
try:
    from google.colab import userdata
    GITHUB_TOKEN = userdata.get("GITHUB_TOKEN")
except Exception:
    GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

# Path to your MUTCD ChromaDB on Google Drive
# This is the folder containing chroma.sqlite3 and the segment subdirectories
DRIVE_CHROMADB_PATH = "/content/drive/MyDrive/MUTCD_RAG/chromadb"

# Destination folder name in the GitHub repo (do not change)
REPO_DB_FOLDER = "vector_database_mutcd"

# Git commit author (will appear in GitHub commit history)
GIT_AUTHOR_NAME  = "Kevin Blackburn"
GIT_AUTHOR_EMAIL = "kblackburn@brentwoodtn.gov"

# ── VALIDATION ────────────────────────────────────────────────────────────────

print("=" * 65)
print("MUTCD CORPUS PUSH TO GITHUB")
print("=" * 65)

# Check Drive is mounted
if not Path("/content/drive/MyDrive").exists():
    print("ERROR: Google Drive is not mounted.")
    print("Run: from google.colab import drive; drive.mount('/content/drive')")
    raise SystemExit(1)

# Check ChromaDB source exists
source_path = Path(DRIVE_CHROMADB_PATH)
if not source_path.exists():
    print(f"ERROR: MUTCD ChromaDB not found at:\n  {DRIVE_CHROMADB_PATH}")
    print("Run 02_build_ingest.ipynb first to build the corpus.")
    raise SystemExit(1)

# Check chroma.sqlite3 exists inside the source path
sqlite_file = source_path / "chroma.sqlite3"
if not sqlite_file.exists():
    print(f"ERROR: chroma.sqlite3 not found in {DRIVE_CHROMADB_PATH}")
    print("The ChromaDB may not have been built correctly.")
    raise SystemExit(1)

# Check GitHub token
if not GITHUB_TOKEN:
    print("ERROR: GITHUB_TOKEN is not set.")
    print("Add it as a Colab secret (lock icon in left sidebar)")
    print("or set GITHUB_TOKEN = 'ghp_...' in the CONFIGURATION section.")
    raise SystemExit(1)

print(f"Source ChromaDB: {DRIVE_CHROMADB_PATH}")
print(f"Target repo:     {GITHUB_USERNAME}/{GITHUB_REPO}")
print(f"Target folder:   {REPO_DB_FOLDER}/")
print()

# ── REPO SETUP ────────────────────────────────────────────────────────────────

# Colab working directory for the cloned repo
COLAB_REPO_PATH = Path(f"/content/{GITHUB_REPO}")

def run(cmd, cwd=None, check=True):
    """Run a shell command and print output. Raises on failure if check=True."""
    result = subprocess.run(
        cmd, shell=True, cwd=cwd,
        capture_output=True, text=True
    )
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.returncode != 0:
        if result.stderr.strip():
            print(f"STDERR: {result.stderr.strip()}")
        if check:
            raise RuntimeError(f"Command failed: {cmd}")
    return result

# Build authenticated remote URL (token embedded for push auth)
REMOTE_URL = (
    f"https://{GITHUB_TOKEN}@github.com/{GITHUB_USERNAME}/{GITHUB_REPO}.git"
)

# Configure git identity (required for commit)
run(f'git config --global user.name "{GIT_AUTHOR_NAME}"')
run(f'git config --global user.email "{GIT_AUTHOR_EMAIL}"')

# Clone repo if not already present; otherwise pull latest
if COLAB_REPO_PATH.exists():
    print("Repo already cloned — pulling latest from main...")
    run("git pull origin main", cwd=str(COLAB_REPO_PATH))
else:
    print("Cloning repo (first time — may take 1-2 minutes)...")
    run(f"git clone {REMOTE_URL} {COLAB_REPO_PATH}", cwd="/content")
    print("Clone complete.")

print()

# ── COPY CHROMADB FILES ───────────────────────────────────────────────────────

dest_path = COLAB_REPO_PATH / REPO_DB_FOLDER

# Remove old database entirely before copying fresh files.
# This prevents stale segment files from accumulating across rebuilds.
if dest_path.exists():
    print(f"Removing old {REPO_DB_FOLDER}/ ...")
    shutil.rmtree(dest_path)

print(f"Copying MUTCD ChromaDB from Drive to repo...")
shutil.copytree(str(source_path), str(dest_path))

# Count what was copied for verification
copied_files = list(dest_path.rglob("*"))
copied_file_count = sum(1 for f in copied_files if f.is_file())
sqlite_size_mb = round((dest_path / "chroma.sqlite3").stat().st_size / 1024 / 1024, 1)
print(f"Copied {copied_file_count} files")
print(f"chroma.sqlite3 size: {sqlite_size_mb} MB")
print()

# ── GIT COMMIT AND PUSH ───────────────────────────────────────────────────────

# Set the authenticated remote URL (required every session — Colab resets git config)
run(
    f"git remote set-url origin {REMOTE_URL}",
    cwd=str(COLAB_REPO_PATH)
)

# Stage the MUTCD database folder
run(f"git add {REPO_DB_FOLDER}/", cwd=str(COLAB_REPO_PATH))

# Check if there are any changes to commit
status_result = run(
    "git status --porcelain",
    cwd=str(COLAB_REPO_PATH),
    check=False
)

if not status_result.stdout.strip():
    print("No changes detected — ChromaDB files are already up to date.")
    print("Nothing to push.")
else:
    # Timestamped commit message for easy audit trail
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    commit_msg = f"Update MUTCD ChromaDB ({timestamp})"
    run(f'git commit -m "{commit_msg}"', cwd=str(COLAB_REPO_PATH))
    print()
    print("Pushing to GitHub...")
    run("git push origin main", cwd=str(COLAB_REPO_PATH))
    print()
    print("=" * 65)
    print("PUSH COMPLETE")
    print("=" * 65)
    print(f"Commit: {commit_msg}")
    print()
    print("Streamlit Cloud will auto-deploy in ~60 seconds.")
    print(f"Live app: https://engineering-ai-assistant-brentwood.streamlit.app")
    print()
    print("After deployment, verify the MUTCD Chatbot page loads correctly")
    print("by asking: 'What are the mounting height requirements for a stop sign?'")
