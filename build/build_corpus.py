"""
build_corpus.py
===============
City of Brentwood Engineering AI Assistant - V2
Corpus builder — runs in Google Colab to populate ChromaDB.

PURPOSE:
    This script reads all 26 municipal documents from Google Drive,
    chunks them using section_chunker.py, embeds each chunk into a
    vector, and stores everything in ChromaDB on Google Drive.

    The resulting ChromaDB database is what the Streamlit app queries
    when an engineer asks a question. This script does NOT need to run
    every time the app starts — only when documents change.

WHEN TO RUN THIS SCRIPT:
    ┌─────────────────────────────────────────┬──────────────────┐
    │ Situation                               │ Run needed?      │
    ├─────────────────────────────────────────┼──────────────────┤
    │ First-time setup                        │ YES — full build │
    │ Municipal Code chapter amended          │ YES — one doc    │
    │ Engineering Policy Manual updated       │ YES — one doc    │
    │ Engineer asks a question                │ NO               │
    │ Streamlit app redeployed                │ NO               │
    │ New feature added to app                │ NO               │
    └─────────────────────────────────────────┴──────────────────┘

HOW TO RUN IN GOOGLE COLAB:
    Full build (all 26 documents):
        BUILD_MODE = "full"

    Single document update (e.g. after Ch. 56 is amended):
        BUILD_MODE = "update"
        UPDATE_DOC_ID = "ch56"

    See the BUILD CONFIGURATION section below.

GOOGLE DRIVE FOLDER STRUCTURE EXPECTED:
    MyDrive/
    └── Brentwood_Engineering_AI_V2/
        ├── source_documents/
        │   ├── engineering_manual/
        │   │   └── Engineering_Policy_Manual.docx
        │   └── municipal_code/
        │       ├── APPENDIX_A___SUBDIVISION_REGULATIONS.docx
        │       ├── Chapter_56___STORMWATER_MANAGEMENT...docx
        │       ├── Chapter_78___ZONING.docx
        │       └── ... (all 25 Municipal Code files)
        ├── vector_database/        ← ChromaDB writes here
        ├── exports/                ← build logs written here
        └── app_config/             ← document_registry.json (optional)

OUTPUT:
    A ChromaDB persistent database at:
    MyDrive/Brentwood_Engineering_AI_V2/vector_database/

    The Streamlit app downloads this database at startup via drive_loader.py.

AUTHOR:  City of Brentwood Engineering Department AI Assistant Project
VERSION: 2.0
"""

# ─────────────────────────────────────────────────────────────────────────────
# ★ BUILD CONFIGURATION — EDIT THIS SECTION BEFORE RUNNING ★
# ─────────────────────────────────────────────────────────────────────────────

# BUILD_MODE controls what gets rebuilt:
#   "full"   — Delete existing database, rebuild all 26 documents from scratch.
#              Use this for first-time setup or after major changes.
#   "update" — Rebuild only the document specified in UPDATE_DOC_ID.
#              All other documents remain untouched in the database.
#              Use this after a single chapter is amended.
BUILD_MODE = "full"

# UPDATE_DOC_ID: Only used when BUILD_MODE = "update"
# Set this to the doc_id of the document that was amended.
# Valid values: see DOCUMENT REGISTRY section below for all doc_ids.
# Examples: "ch56", "ch78", "appendix_a", "epm"
UPDATE_DOC_ID = "ch56"

# GOOGLE DRIVE BASE PATH
# This is the root folder for all V2 files on Google Drive.
# Change this if you moved the folder.
DRIVE_BASE = "/content/drive/MyDrive/Brentwood_Engineering_AI_V2"

# CHROMADB COLLECTION NAME
# All chunks from all documents go into one collection.
# The metadata fields (doc_id, content_type, etc.) allow filtered queries.
COLLECTION_NAME = "brentwood_engineering_v2"

# EMBEDDING MODEL
# all-MiniLM-L6-v2: fast, good quality, 384-dimensional vectors.
# Do NOT change this after a full build — changing models requires full rebuild
# because old and new vectors are not compatible.
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# BATCH SIZE for ChromaDB insertions
# Larger batches are faster but use more RAM.
# 100 is safe for Colab's default memory allocation.
BATCH_SIZE = 100

# ─────────────────────────────────────────────────────────────────────────────
# DOCUMENT REGISTRY
# All 26 documents in the Brentwood municipal corpus.
# Each entry describes one DOCX file and how to cite it.
#
# FIELDS:
#   doc_id:          Short unique identifier. Used as the ChromaDB filter key.
#                    Also used as the "delete target" for single-doc updates.
#   filename:        Exact filename as it appears in Google Drive.
#   subfolder:       "engineering_manual" or "municipal_code"
#   doc_type:        "municipal_code" | "appendix" | "engineering_policy"
#                    Controls which section detection pattern is used.
#   title:           Full human-readable title for display in citations.
#   citation_format: Base citation string. section_chunker appends section
#                    number and title to this.
#   relevance_tier:  1 = primary (most queried), 2 = secondary, 3 = supplemental
#                    Used for logging and future tiered search strategies.
# ─────────────────────────────────────────────────────────────────────────────

DOCUMENT_REGISTRY = [

    # ── ENGINEERING POLICY MANUAL ─────────────────────────────────────────
    {
        "doc_id":          "epm",
        "filename":        "Engineering_Policy_Manual.docx",
        "subfolder":       "engineering_manual",
        "doc_type":        "engineering_policy",
        "title":           "City of Brentwood Engineering Dept. Policy Manual",
        "citation_format": "City of Brentwood Engineering Dept. Policy Manual",
        "relevance_tier":  1,
    },

    # ── APPENDIX A — SUBDIVISION REGULATIONS ──────────────────────────────
    {
        "doc_id":          "appendix_a",
        "filename":        "APPENDIX_A___SUBDIVISION_REGULATIONS.docx",
        "subfolder":       "municipal_code",
        "doc_type":        "appendix",
        "title":           "City of Brentwood Subdivision Regulations (Appendix A)",
        "citation_format": "City of Brentwood Subdivision Regulations (Appendix A)",
        "relevance_tier":  1,
    },

    # ── TIER 1 MUNICIPAL CODE — Primary engineering chapters ──────────────
    {
        "doc_id":          "ch56",
        "filename":        "Chapter_56___STORMWATER_MANAGEMENT__EROSION_CONTROL_AND_FLOOD_DAMAGE_PREVENTION.docx",
        "subfolder":       "municipal_code",
        "doc_type":        "municipal_code",
        "title":           "Brentwood Municipal Code, Chapter 56 — Stormwater Management, Erosion Control and Flood Damage Prevention",
        "citation_format": "Brentwood Municipal Code, Chapter 56 — Stormwater Management",
        "relevance_tier":  1,
    },
    {
        "doc_id":          "ch58",
        "filename":        "Chapter_58___STREETS__SIDEWALKS_AND_OTHER_PUBLIC_PLACES.docx",
        "subfolder":       "municipal_code",
        "doc_type":        "municipal_code",
        "title":           "Brentwood Municipal Code, Chapter 58 — Streets, Sidewalks and Other Public Places",
        "citation_format": "Brentwood Municipal Code, Chapter 58 — Streets, Sidewalks and Other Public Places",
        "relevance_tier":  1,
    },
    {
        "doc_id":          "ch78",
        "filename":        "Chapter_78___ZONING.docx",
        "subfolder":       "municipal_code",
        "doc_type":        "municipal_code",
        "title":           "Brentwood Municipal Code, Chapter 78 — Zoning",
        "citation_format": "Brentwood Municipal Code, Chapter 78 — Zoning",
        "relevance_tier":  1,
    },

    # ── TIER 2 MUNICIPAL CODE — Secondary engineering relevance ───────────
    {
        "doc_id":          "ch14",
        "filename":        "Chapter_14___BUILDINGS_AND_BUILDING_REGULATIONS.docx",
        "subfolder":       "municipal_code",
        "doc_type":        "municipal_code",
        "title":           "Brentwood Municipal Code, Chapter 14 — Buildings and Building Regulations",
        "citation_format": "Brentwood Municipal Code, Chapter 14 — Buildings and Building Regulations",
        "relevance_tier":  2,
    },
    {
        "doc_id":          "ch24",
        "filename":        "Chapter_24___EMERGENCY_SERVICES.docx",
        "subfolder":       "municipal_code",
        "doc_type":        "municipal_code",
        "title":           "Brentwood Municipal Code, Chapter 24 — Emergency Services",
        "citation_format": "Brentwood Municipal Code, Chapter 24 — Emergency Services",
        "relevance_tier":  2,
    },
    {
        "doc_id":          "ch26",
        "filename":        "Chapter_26___FIRE_PREVENTION_AND_PROTECTION.docx",
        "subfolder":       "municipal_code",
        "doc_type":        "municipal_code",
        "title":           "Brentwood Municipal Code, Chapter 26 — Fire Prevention and Protection",
        "citation_format": "Brentwood Municipal Code, Chapter 26 — Fire Prevention and Protection",
        "relevance_tier":  2,
    },
    {
        "doc_id":          "ch30",
        "filename":        "Chapter_30___HEALTH_AND_SANITATION.docx",
        "subfolder":       "municipal_code",
        "doc_type":        "municipal_code",
        "title":           "Brentwood Municipal Code, Chapter 30 — Health and Sanitation",
        "citation_format": "Brentwood Municipal Code, Chapter 30 — Health and Sanitation",
        "relevance_tier":  2,
    },
    {
        "doc_id":          "ch50",
        "filename":        "Chapter_50___PLANNING.docx",
        "subfolder":       "municipal_code",
        "doc_type":        "municipal_code",
        "title":           "Brentwood Municipal Code, Chapter 50 — Planning",
        "citation_format": "Brentwood Municipal Code, Chapter 50 — Planning",
        "relevance_tier":  2,
    },
    {
        "doc_id":          "ch66",
        "filename":        "Chapter_66___TRAFFIC_AND_VEHICLES.docx",
        "subfolder":       "municipal_code",
        "doc_type":        "municipal_code",
        "title":           "Brentwood Municipal Code, Chapter 66 — Traffic and Vehicles",
        "citation_format": "Brentwood Municipal Code, Chapter 66 — Traffic and Vehicles",
        "relevance_tier":  2,
    },
    {
        "doc_id":          "ch70",
        "filename":        "Chapter_70___UTILITIES.docx",
        "subfolder":       "municipal_code",
        "doc_type":        "municipal_code",
        "title":           "Brentwood Municipal Code, Chapter 70 — Utilities",
        "citation_format": "Brentwood Municipal Code, Chapter 70 — Utilities",
        "relevance_tier":  2,
    },

    # ── TIER 3 MUNICIPAL CODE — Supplemental chapters ─────────────────────
    {
        "doc_id":          "ch1",
        "filename":        "Chapter_1___GENERAL_PROVISIONS.docx",
        "subfolder":       "municipal_code",
        "doc_type":        "municipal_code",
        "title":           "Brentwood Municipal Code, Chapter 1 — General Provisions",
        "citation_format": "Brentwood Municipal Code, Chapter 1 — General Provisions",
        "relevance_tier":  3,
    },
    {
        "doc_id":          "ch2",
        "filename":        "Chapter_2___ADMINISTRATION.docx",
        "subfolder":       "municipal_code",
        "doc_type":        "municipal_code",
        "title":           "Brentwood Municipal Code, Chapter 2 — Administration",
        "citation_format": "Brentwood Municipal Code, Chapter 2 — Administration",
        "relevance_tier":  3,
    },
    {
        "doc_id":          "ch6",
        "filename":        "Chapter_6___ALCOHOLIC_BEVERAGES.docx",
        "subfolder":       "municipal_code",
        "doc_type":        "municipal_code",
        "title":           "Brentwood Municipal Code, Chapter 6 — Alcoholic Beverages",
        "citation_format": "Brentwood Municipal Code, Chapter 6 — Alcoholic Beverages",
        "relevance_tier":  3,
    },
    {
        "doc_id":          "ch10",
        "filename":        "Chapter_10___ANIMALS.docx",
        "subfolder":       "municipal_code",
        "doc_type":        "municipal_code",
        "title":           "Brentwood Municipal Code, Chapter 10 — Animals",
        "citation_format": "Brentwood Municipal Code, Chapter 10 — Animals",
        "relevance_tier":  3,
    },
    {
        "doc_id":          "ch18",
        "filename":        "Chapter_18___BUSINESSES.docx",
        "subfolder":       "municipal_code",
        "doc_type":        "municipal_code",
        "title":           "Brentwood Municipal Code, Chapter 18 — Businesses",
        "citation_format": "Brentwood Municipal Code, Chapter 18 — Businesses",
        "relevance_tier":  3,
    },
    {
        "doc_id":          "ch20",
        "filename":        "Chapter_20___CABLE_COMMUNICATIONS.docx",
        "subfolder":       "municipal_code",
        "doc_type":        "municipal_code",
        "title":           "Brentwood Municipal Code, Chapter 20 — Cable Communications",
        "citation_format": "Brentwood Municipal Code, Chapter 20 — Cable Communications",
        "relevance_tier":  3,
    },
    {
        "doc_id":          "ch22",
        "filename":        "Chapter_22___COURT.docx",
        "subfolder":       "municipal_code",
        "doc_type":        "municipal_code",
        "title":           "Brentwood Municipal Code, Chapter 22 — Court",
        "citation_format": "Brentwood Municipal Code, Chapter 22 — Court",
        "relevance_tier":  3,
    },
    {
        "doc_id":          "ch34",
        "filename":        "Chapter_34___LAW_ENFORCEMENT.docx",
        "subfolder":       "municipal_code",
        "doc_type":        "municipal_code",
        "title":           "Brentwood Municipal Code, Chapter 34 — Law Enforcement",
        "citation_format": "Brentwood Municipal Code, Chapter 34 — Law Enforcement",
        "relevance_tier":  3,
    },
    {
        "doc_id":          "ch38",
        "filename":        "Chapter_38___LIBRARY.docx",
        "subfolder":       "municipal_code",
        "doc_type":        "municipal_code",
        "title":           "Brentwood Municipal Code, Chapter 38 — Library",
        "citation_format": "Brentwood Municipal Code, Chapter 38 — Library",
        "relevance_tier":  3,
    },
    {
        "doc_id":          "ch42",
        "filename":        "Chapter_42___OFFENSES_AND_MISCELLANEOUS_PROVISIONS.docx",
        "subfolder":       "municipal_code",
        "doc_type":        "municipal_code",
        "title":           "Brentwood Municipal Code, Chapter 42 — Offenses and Miscellaneous Provisions",
        "citation_format": "Brentwood Municipal Code, Chapter 42 — Offenses and Miscellaneous Provisions",
        "relevance_tier":  3,
    },
    {
        "doc_id":          "ch46",
        "filename":        "Chapter_46___PARKS_AND_RECREATION.docx",
        "subfolder":       "municipal_code",
        "doc_type":        "municipal_code",
        "title":           "Brentwood Municipal Code, Chapter 46 — Parks and Recreation",
        "citation_format": "Brentwood Municipal Code, Chapter 46 — Parks and Recreation",
        "relevance_tier":  3,
    },
    {
        "doc_id":          "ch54",
        "filename":        "Chapter_54___SOLID_WASTE.docx",
        "subfolder":       "municipal_code",
        "doc_type":        "municipal_code",
        "title":           "Brentwood Municipal Code, Chapter 54 — Solid Waste",
        "citation_format": "Brentwood Municipal Code, Chapter 54 — Solid Waste",
        "relevance_tier":  3,
    },
    {
        "doc_id":          "ch62",
        "filename":        "Chapter_62___TAXATION.docx",
        "subfolder":       "municipal_code",
        "doc_type":        "municipal_code",
        "title":           "Brentwood Municipal Code, Chapter 62 — Taxation",
        "citation_format": "Brentwood Municipal Code, Chapter 62 — Taxation",
        "relevance_tier":  3,
    },
    {
        "doc_id":          "ch74",
        "filename":        "Chapter_74___VEHICLES_FOR_HIRE.docx",
        "subfolder":       "municipal_code",
        "doc_type":        "municipal_code",
        "title":           "Brentwood Municipal Code, Chapter 74 — Vehicles for Hire",
        "citation_format": "Brentwood Municipal Code, Chapter 74 — Vehicles for Hire",
        "relevance_tier":  3,
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# IMPORTS — install these in Colab first:
#   !pip install chromadb sentence-transformers python-docx
# ─────────────────────────────────────────────────────────────────────────────

import os
import sys
import json
import time
import datetime
from pathlib import Path

# Add the build/ and utils/ directories to Python path so we can import
# section_chunker (in build/) and any utils we need
sys.path.insert(0, str(Path(__file__).parent))          # build/ dir
sys.path.insert(0, str(Path(__file__).parent.parent))   # repo root

from section_chunker import chunk_document

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction


# ─────────────────────────────────────────────────────────────────────────────
# PATH SETUP
# ─────────────────────────────────────────────────────────────────────────────

PATHS = {
    "engineering_manual": Path(DRIVE_BASE) / "source_documents" / "engineering_manual",
    "municipal_code":     Path(DRIVE_BASE) / "source_documents" / "municipal_code",
    "vector_database":    Path(DRIVE_BASE) / "vector_database",
    "exports":            Path(DRIVE_BASE) / "exports",
}


# ─────────────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def log(message: str, level: str = "INFO"):
    """
    Print a timestamped log message.
    In Colab, this shows up in the cell output in real time.
    """
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    prefix = {"INFO": "  ", "OK": "✅", "WARN": "⚠️ ", "ERR": "❌", "HEAD": "──"}.get(level, "  ")
    print(f"[{timestamp}] {prefix} {message}")


def verify_drive_structure():
    """
    Check that all expected Google Drive folders exist before starting.
    Gives a clear error message if something is missing.
    """
    log("Verifying Google Drive folder structure...", "HEAD")
    all_ok = True

    for name, path in PATHS.items():
        if path.exists():
            log(f"{name}: {path}", "OK")
        else:
            log(f"{name} NOT FOUND: {path}", "ERR")
            all_ok = False

    if not all_ok:
        raise FileNotFoundError(
            "\n\nOne or more required folders are missing from Google Drive.\n"
            "Please create the folder structure as described in the build guide:\n"
            f"  {DRIVE_BASE}/\n"
            "    source_documents/engineering_manual/\n"
            "    source_documents/municipal_code/\n"
            "    vector_database/\n"
            "    exports/\n"
        )

    log("All required folders found.", "OK")


def get_document_path(entry: dict) -> Path:
    """Return the full filesystem path for a document registry entry."""
    subfolder_path = PATHS[entry["subfolder"]]
    return subfolder_path / entry["filename"]


def verify_documents(doc_ids: list = None):
    """
    Check that all (or specified) documents exist on Drive before building.
    Logs missing files without stopping — lets you build a partial corpus
    if some files haven't been uploaded yet.

    ARGS:
        doc_ids: List of doc_ids to check. None = check all 26.

    RETURNS:
        List of registry entries for documents that exist and are ready to process.
    """
    log("Verifying document files...", "HEAD")
    ready = []
    missing = []

    targets = DOCUMENT_REGISTRY if doc_ids is None else [
        entry for entry in DOCUMENT_REGISTRY if entry["doc_id"] in doc_ids
    ]

    for entry in targets:
        path = get_document_path(entry)
        if path.exists():
            size_kb = path.stat().st_size // 1024
            log(f"{entry['doc_id']:12s} ({size_kb:5d} KB)  {entry['filename'][:50]}", "OK")
            ready.append(entry)
        else:
            log(f"{entry['doc_id']:12s} MISSING: {path}", "WARN")
            missing.append(entry["doc_id"])

    log(f"Ready: {len(ready)} / {len(targets)} documents", "INFO")
    if missing:
        log(f"Missing: {missing}", "WARN")
        log("Missing documents will be skipped. Add them to Drive and re-run.", "WARN")

    return ready


def initialize_chromadb():
    """
    Connect to (or create) the ChromaDB persistent database on Google Drive.

    ChromaDB stores its data as files in the vector_database/ folder.
    Each time Colab opens, we reconnect to the same files.
    The data persists between sessions as long as Google Drive is mounted.

    RETURNS:
        (client, collection) — the ChromaDB client and collection objects.
    """
    log("Initializing ChromaDB...", "HEAD")

    db_path = str(PATHS["vector_database"])
    log(f"Database path: {db_path}")

    # Create the embedding function — this is what converts text to vectors.
    # SentenceTransformer downloads the model the first time (~90MB).
    # Subsequent calls use the cached version.
    log(f"Loading embedding model: {EMBEDDING_MODEL}")
    embedding_fn = SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL
    )
    log("Embedding model loaded.", "OK")

    # Connect to ChromaDB
    client = chromadb.PersistentClient(path=db_path)

    # Get or create the collection
    # get_or_create_collection: safe to call whether or not the collection exists
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_fn,
        metadata={
            "description": "City of Brentwood municipal engineering corpus",
            "embedding_model": EMBEDDING_MODEL,
            "created_by": "build_corpus.py",
            "version": "2.0",
        }
    )

    existing_count = collection.count()
    log(f"Collection '{COLLECTION_NAME}': {existing_count} existing chunks", "OK")

    return client, collection


def delete_document_chunks(collection, doc_id: str):
    """
    Remove all chunks belonging to a specific document from ChromaDB.

    This is the key operation for single-document updates.
    After deletion, only that document's chunks are gone —
    everything else remains intact.

    ARGS:
        collection: ChromaDB collection object
        doc_id:     e.g. "ch56" — must match the doc_id in chunk metadata
    """
    log(f"Deleting existing chunks for doc_id='{doc_id}'...")

    # Count first so we can report how many were removed
    before = collection.count()

    # ChromaDB where clause: delete all records where metadata.doc_id == doc_id
    collection.delete(where={"doc_id": doc_id})

    after = collection.count()
    removed = before - after
    log(f"Removed {removed} chunks for '{doc_id}'. Collection now has {after} chunks.", "OK")


def insert_chunks_batch(collection, chunks: list):
    """
    Insert a list of Chunk objects into ChromaDB in batches.

    WHY BATCHING:
        ChromaDB and sentence-transformers both perform better with
        batch operations. Also prevents Colab memory spikes from
        trying to embed thousands of chunks at once.

    ARGS:
        collection: ChromaDB collection object
        chunks:     List of Chunk objects from section_chunker
    """
    if not chunks:
        log("No chunks to insert — skipping.", "WARN")
        return

    total = len(chunks)
    inserted = 0

    for i in range(0, total, BATCH_SIZE):
        batch = chunks[i : i + BATCH_SIZE]

        ids        = [c.chunk_id   for c in batch]
        documents  = [c.text       for c in batch]
        metadatas  = [c.metadata   for c in batch]

        # ChromaDB requires all metadata values to be str, int, float, or bool.
        # Sanitize: convert any None values to empty string.
        metadatas = [
            {k: (v if v is not None else "") for k, v in m.items()}
            for m in metadatas
        ]

        collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )

        inserted += len(batch)
        pct = (inserted / total) * 100
        log(f"  Inserted {inserted}/{total} chunks ({pct:.0f}%)")

    log(f"All {total} chunks inserted successfully.", "OK")


def save_build_log(log_entries: list, mode: str, doc_ids_built: list):
    """
    Save a JSON build log to the exports/ folder on Google Drive.

    The log records:
    - When the build ran
    - Which documents were processed
    - How many chunks each produced
    - Any errors encountered

    This gives you a paper trail for when you updated what.
    Useful when auditing "which version of Ch. 56 is in the database?"
    """
    log_path = PATHS["exports"] / f"build_log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    log_data = {
        "build_timestamp": datetime.datetime.now().isoformat(),
        "build_mode": mode,
        "documents_processed": doc_ids_built,
        "collection_name": COLLECTION_NAME,
        "embedding_model": EMBEDDING_MODEL,
        "entries": log_entries,
    }

    with open(log_path, "w") as f:
        json.dump(log_data, f, indent=2)

    log(f"Build log saved: {log_path}", "OK")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN BUILD FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def build_corpus():
    """
    Main build function. Called at the bottom of this script.

    FULL BUILD flow:
        1. Verify Drive structure
        2. Verify all 26 document files exist
        3. Connect to ChromaDB
        4. Delete entire collection (fresh start)
        5. For each document: chunk → embed → insert
        6. Verify final chunk count
        7. Save build log

    UPDATE BUILD flow:
        1. Verify Drive structure
        2. Verify the one target document exists
        3. Connect to ChromaDB
        4. Delete only that document's chunks
        5. Chunk → embed → insert the new version
        6. Verify chunk count
        7. Save build log
    """

    build_start = time.time()
    log("=" * 60, "HEAD")
    log(f"CITY OF BRENTWOOD ENGINEERING AI — CORPUS BUILDER V2")
    log(f"Mode: {BUILD_MODE.upper()}")
    log(f"Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("=" * 60, "HEAD")

    # ── Step 1: Verify Drive structure ────────────────────────────────────
    verify_drive_structure()

    # ── Step 2: Determine which documents to process ──────────────────────
    if BUILD_MODE == "full":
        log("\nFULL BUILD — all documents will be processed", "HEAD")
        docs_to_process = verify_documents()

    elif BUILD_MODE == "update":
        log(f"\nUPDATE BUILD — rebuilding doc_id='{UPDATE_DOC_ID}' only", "HEAD")

        # Validate that UPDATE_DOC_ID is in the registry
        valid_ids = [e["doc_id"] for e in DOCUMENT_REGISTRY]
        if UPDATE_DOC_ID not in valid_ids:
            raise ValueError(
                f"UPDATE_DOC_ID='{UPDATE_DOC_ID}' not found in registry.\n"
                f"Valid doc_ids: {valid_ids}"
            )
        docs_to_process = verify_documents(doc_ids=[UPDATE_DOC_ID])

        if not docs_to_process:
            raise FileNotFoundError(
                f"Document file for '{UPDATE_DOC_ID}' not found on Drive.\n"
                "Please upload the new version before running the update."
            )
    else:
        raise ValueError(f"Invalid BUILD_MODE='{BUILD_MODE}'. Must be 'full' or 'update'.")

    if not docs_to_process:
        log("No documents to process. Exiting.", "WARN")
        return

    # ── Step 3: Connect to ChromaDB ───────────────────────────────────────
    client, collection = initialize_chromadb()

    # ── Step 4: Clear existing data ───────────────────────────────────────
    if BUILD_MODE == "full":
        log("\nClearing entire collection for fresh build...", "HEAD")
        # Delete and recreate the collection for a completely clean slate
        try:
            client.delete_collection(COLLECTION_NAME)
            log(f"Deleted collection '{COLLECTION_NAME}'.", "OK")
        except Exception:
            log("Collection didn't exist yet — starting fresh.", "INFO")

        # Re-initialize after deletion
        client, collection = initialize_chromadb()

    elif BUILD_MODE == "update":
        log(f"\nRemoving old chunks for '{UPDATE_DOC_ID}'...", "HEAD")
        delete_document_chunks(collection, UPDATE_DOC_ID)

    # ── Step 5: Process each document ─────────────────────────────────────
    log("\nProcessing documents...", "HEAD")
    build_log_entries = []
    total_chunks_inserted = 0

    for i, entry in enumerate(docs_to_process, 1):
        doc_start = time.time()
        doc_path = get_document_path(entry)

        log(f"\n[{i}/{len(docs_to_process)}] {entry['doc_id']} — {entry['filename'][:55]}")

        try:
            # Chunk the document
            log(f"  Chunking ({entry['doc_type']})...")
            chunks = chunk_document(
                filepath=str(doc_path),
                doc_id=entry["doc_id"],
                doc_title=entry["title"],
                doc_type=entry["doc_type"],
                citation_format=entry["citation_format"],
            )
            log(f"  {len(chunks)} chunks produced.")

            if not chunks:
                log(f"  WARNING: No chunks produced for {entry['doc_id']}!", "WARN")
                build_log_entries.append({
                    "doc_id": entry["doc_id"],
                    "filename": entry["filename"],
                    "status": "warning_no_chunks",
                    "chunks": 0,
                    "error": None,
                })
                continue

            # Insert into ChromaDB
            log(f"  Embedding and inserting into ChromaDB...")
            insert_chunks_batch(collection, chunks)

            elapsed = time.time() - doc_start
            total_chunks_inserted += len(chunks)

            log(f"  Done in {elapsed:.1f}s — {len(chunks)} chunks added.", "OK")

            build_log_entries.append({
                "doc_id":    entry["doc_id"],
                "filename":  entry["filename"],
                "doc_type":  entry["doc_type"],
                "tier":      entry["relevance_tier"],
                "status":    "success",
                "chunks":    len(chunks),
                "elapsed_s": round(elapsed, 1),
                "error":     None,
            })

        except FileNotFoundError as e:
            log(f"  File not found: {e}", "ERR")
            build_log_entries.append({
                "doc_id": entry["doc_id"], "filename": entry["filename"],
                "status": "error_file_not_found", "chunks": 0, "error": str(e),
            })

        except Exception as e:
            log(f"  Unexpected error: {e}", "ERR")
            import traceback
            traceback.print_exc()
            build_log_entries.append({
                "doc_id": entry["doc_id"], "filename": entry["filename"],
                "status": "error", "chunks": 0, "error": str(e),
            })

    # ── Step 6: Final verification ────────────────────────────────────────
    log("\nFinal verification...", "HEAD")
    final_count = collection.count()
    log(f"Total chunks in collection: {final_count}", "OK")

    # Quick sanity check: run a test query to confirm search works
    log("Running test query: 'riparian buffer minimum width'")
    test_results = collection.query(
        query_texts=["riparian buffer minimum width"],
        n_results=3,
        include=["metadatas", "documents", "distances"],
    )

    if test_results["ids"][0]:
        log("Test query returned results:", "OK")
        for j, (doc_id_meta, dist) in enumerate(
            zip(test_results["metadatas"][0], test_results["distances"][0])
        ):
            citation = doc_id_meta.get("source_citation", "no citation")[:70]
            log(f"  {j+1}. [score: {1-dist:.3f}] {citation}")
    else:
        log("Test query returned no results — check if chunks were inserted.", "ERR")

    # ── Step 7: Build summary ─────────────────────────────────────────────
    total_elapsed = time.time() - build_start
    doc_ids_built = [e["doc_id"] for e in build_log_entries if e["status"] == "success"]
    errors = [e for e in build_log_entries if "error" in e["status"]]

    log("\n" + "=" * 60, "HEAD")
    log("BUILD COMPLETE")
    log("=" * 60, "HEAD")
    log(f"Mode:              {BUILD_MODE}")
    log(f"Documents built:   {len(doc_ids_built)} / {len(docs_to_process)}")
    log(f"Chunks inserted:   {total_chunks_inserted}")
    log(f"Total in DB:       {final_count}")
    log(f"Errors:            {len(errors)}")
    log(f"Total time:        {total_elapsed:.0f}s ({total_elapsed/60:.1f} min)")

    if errors:
        log("\nDocuments with errors:", "WARN")
        for e in errors:
            log(f"  {e['doc_id']}: {e['error'][:80]}", "WARN")

    # Per-document summary table
    log("\nDocument summary:")
    log(f"  {'doc_id':12s} {'chunks':>6s}  {'time':>6s}  {'status'}")
    log(f"  {'-'*12} {'-'*6}  {'-'*6}  {'-'*10}")
    for entry in build_log_entries:
        chunks_str = str(entry.get("chunks", 0))
        time_str = f"{entry.get('elapsed_s', 0):.1f}s" if entry.get("elapsed_s") else "—"
        log(f"  {entry['doc_id']:12s} {chunks_str:>6s}  {time_str:>6s}  {entry['status']}")

    # Save build log
    save_build_log(build_log_entries, BUILD_MODE, doc_ids_built)

    log("\n✅ Corpus builder finished. The Streamlit app can now be deployed.", "OK")
    log(f"   Database location: {PATHS['vector_database']}")


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # When you run this script directly in Colab (or from terminal),
    # this block executes the build.
    #
    # In Colab, run this cell:
    #   !python build/build_corpus.py
    #
    # Or import and call directly:
    #   from build.build_corpus import build_corpus
    #   build_corpus()

    build_corpus()
