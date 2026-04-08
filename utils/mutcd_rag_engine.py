"""
mutcd_rag_engine.py
===================
City of Brentwood Engineering AI Assistant - V2
RAG engine for MUTCD 11th Edition queries.

PURPOSE:
    This module is a completely separate RAG engine for the MUTCD Chatbot page.
    It is intentionally isolated from rag_engine.py so that any changes to the
    EPM/Code engine cannot break the MUTCD engine, and vice versa.

    When an engineer asks a question about the MUTCD:
    1. EMBEDS the question using Voyage AI voyage-3 (same model used to build
       the MUTCD corpus in Colab — embeddings must match)
    2. SEARCHES the mutcd_full ChromaDB collection for the most relevant sections
    3. BUILDS a structured prompt with retrieved MUTCD section text
    4. CALLS Claude to generate a grounded answer with section citations
    5. RETURNS a structured result dict compatible with the QA Mode display helpers

CITATION FORMAT:
    MUTCD citations reference the part, chapter, and section:
        "MUTCD 11th Edition, Part 2B — Regulatory Signs,
         Section 2B.03 — Stop Sign"

    Each chunk in the MUTCD corpus has one-chunk-per-section, so
    citations are clean and unambiguous.

COLLECTION DETAILS (built in Colab, April 2026):
    Collection name:  mutcd_full
    Embedding model:  voyage-3 (Voyage AI API)
    Chunks:           953 sections (one chunk per section)
    Source:           MUTCD 11th Edition (FHWA)
    ChromaDB path:    vector_database_mutcd/ (in repo root)

WHAT THIS MODULE DOES NOT DO:
    - It never fabricates information
    - It never answers from Claude's training knowledge about the MUTCD
    - It never cites sections it did not retrieve
    - It does not use the EPM knowledge graph (MUTCD has no exceptions index)

AUTHOR:  City of Brentwood Engineering Department AI Assistant Project
VERSION: 1.0 — initial MUTCD integration
"""

import time
from pathlib import Path
from typing import Optional

import streamlit as st

# ChromaDB — suppress Streamlit 1.43+ file watcher crash on torch.classes.
# Must run before chromadb import.
try:
    import torch
    torch.classes.__path__ = []
except Exception:
    pass

import chromadb


# -----------------------------------------------------------------------------
# CONFIGURATION
# These must match exactly what the Colab ingest notebook used when building
# the corpus. Changing any of these requires a full corpus rebuild in Colab.
# -----------------------------------------------------------------------------

# Claude model for answer generation. Must match Anthropic's model string.
CLAUDE_MODEL = "claude-sonnet-4-5-20250929"

# ChromaDB collection name — set in 02_build_ingest.ipynb.
COLLECTION_NAME = "mutcd_full"

# Embedding model name — Voyage AI API model.
# The Voyage API is called at query time to embed the user's question.
# This MUST match the model used during corpus ingest (voyage-3).
VOYAGE_MODEL = "voyage-3"

# How many MUTCD sections to retrieve per query.
# The MUTCD has one chunk per section, so 8 sections gives good coverage
# without overwhelming Claude's context window.
TOP_K_CHUNKS = 8

# Minimum similarity score to include a retrieved section.
# MUTCD sections are large (one full section per chunk), so a slightly
# higher threshold than the EPM engine is appropriate.
SIMILARITY_THRESHOLD = 0.30

# Maximum tokens Claude may use in its answer.
MAX_ANSWER_TOKENS = 1500

# Temperature — always 0.0 for regulatory/technical work.
TEMPERATURE = 0.0

# Path to the MUTCD ChromaDB directory, relative to the repo root.
# This folder is committed to GitHub alongside vector_database/ (EPM).
MUTCD_DB_FOLDER = "vector_database_mutcd"

# Streamlit Cloud repo root path (where Streamlit clones the GitHub repo)
STREAMLIT_CLOUD_DB_PATH = f"/mount/src/engineering-ai-assistant-v2/{MUTCD_DB_FOLDER}"

# Local fallback path for development
LOCAL_DB_PATH = str(Path(__file__).parent.parent / MUTCD_DB_FOLDER)


# -----------------------------------------------------------------------------
# MUTCD RAG ENGINE CLASS
# -----------------------------------------------------------------------------

class MUTCDRAGEngine:
    """
    RAG engine for the MUTCD 11th Edition chatbot page.

    Uses Voyage AI voyage-3 embeddings (API-based, matches the corpus build)
    and ChromaDB's mutcd_full collection (one chunk per MUTCD section).

    LIFECYCLE:
        engine = MUTCDRAGEngine()
        if engine.is_ready():
            result = engine.query("What are the requirements for a stop sign?")
            print(result['answer'])

    Stored in Streamlit session state via get_mutcd_rag_engine() cache wrapper.
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the MUTCD RAG engine.

        ARGS:
            db_path: Path to the MUTCD ChromaDB directory.
                     If None, auto-detects Streamlit Cloud vs local path.
        """
        self.db_path        = db_path
        self.chroma_client  = None
        self.collection     = None
        self.claude_client  = None
        self.voyage_client  = None
        self.is_initialized = False
        self._init_error    = None

        try:
            self._initialize()
        except Exception as e:
            self._init_error = str(e)
            print(f"MUTCDRAGEngine initialization failed: {e}")

    # ── Initialization ─────────────────────────────────────────────────────

    def _initialize(self):
        """Connect to ChromaDB, Voyage AI, and Claude. Called once in __init__."""
        self._connect_chromadb()
        self._connect_voyage()
        self._connect_claude()
        self.is_initialized = True

    def _connect_chromadb(self):
        """
        Connect to the MUTCD ChromaDB database.

        The database lives in vector_database_mutcd/ in the repo root.
        Streamlit Cloud reads it from the cloned repo directory.
        Local development reads it from the same relative path.

        IMPORTANT: We do NOT pass an embedding_function to ChromaDB here.
        Voyage AI is called separately in _embed_query() before each search,
        and we pass the embedding vector directly to collection.query().
        This is necessary because ChromaDB's built-in embedding functions
        don't support the Voyage AI API.
        """
        # Determine database path — Streamlit Cloud first, local fallback
        if self.db_path:
            db_directory = self.db_path
        elif Path(STREAMLIT_CLOUD_DB_PATH).exists():
            db_directory = STREAMLIT_CLOUD_DB_PATH
        else:
            db_directory = LOCAL_DB_PATH

        db_path_obj = Path(db_directory)
        if not db_path_obj.exists():
            raise FileNotFoundError(
                f"MUTCD ChromaDB directory not found at '{db_directory}'. "
                "Push the vector_database_mutcd/ folder to GitHub. "
                "See the Colab push notebook for instructions."
            )

        # Connect to ChromaDB — no embedding function needed here
        # (we pass embeddings manually at query time via _embed_query)
        self.chroma_client = chromadb.PersistentClient(path=str(db_path_obj))

        # Load the MUTCD collection
        try:
            # Get collection WITHOUT embedding function.
            # We will compute embeddings ourselves using Voyage AI.
            self.collection = self.chroma_client.get_collection(
                name=COLLECTION_NAME,
            )
            count = self.collection.count()
            print(f"MUTCD ChromaDB connected: '{COLLECTION_NAME}' — {count:,} sections")
        except Exception as e:
            raise RuntimeError(
                f"Collection '{COLLECTION_NAME}' not found in MUTCD ChromaDB. "
                f"Has 02_build_ingest.ipynb been run and pushed to GitHub? "
                f"Error: {e}"
            )

    def _connect_voyage(self):
        """
        Initialize the Voyage AI client using the API key from Streamlit secrets.

        The Voyage AI key must be added to .streamlit/secrets.toml as:
            VOYAGE_API_KEY = "pa-..."
        """
        try:
            import voyageai
        except ImportError:
            raise ImportError(
                "voyageai package not installed. "
                "Add 'voyageai' to requirements.txt and redeploy."
            )

        try:
            api_key = st.secrets.get("VOYAGE_API_KEY")
        except Exception:
            import os
            api_key = os.environ.get("VOYAGE_API_KEY")

        if not api_key:
            raise ValueError(
                "VOYAGE_API_KEY not found in Streamlit secrets. "
                "Add it to .streamlit/secrets.toml: VOYAGE_API_KEY = 'pa-...'"
            )

        self.voyage_client = voyageai.Client(api_key=api_key)
        print("Voyage AI client connected")

    def _connect_claude(self):
        """
        Initialize the Anthropic Claude client using the existing API key.
        Re-uses the same CLAUDE_API_KEY already in Streamlit secrets.
        """
        import anthropic

        try:
            api_key = st.secrets.get("CLAUDE_API_KEY")
        except Exception:
            import os
            api_key = os.environ.get("CLAUDE_API_KEY")

        if not api_key:
            raise ValueError(
                "CLAUDE_API_KEY not found in Streamlit secrets. "
                "This key is shared with the Municipal Code chatbot."
            )

        self.claude_client = anthropic.Anthropic(api_key=api_key)
        print("Claude API client connected (MUTCD engine)")

    # ── Public API ──────────────────────────────────────────────────────────

    def is_ready(self) -> bool:
        """Return True if the engine is fully initialized and ready to query."""
        return (
            self.is_initialized
            and self.collection is not None
            and self.claude_client is not None
            and self.voyage_client is not None
        )

    def get_init_error(self) -> Optional[str]:
        """Return the initialization error message, or None if init succeeded."""
        return self._init_error

    def get_collection_stats(self) -> dict:
        """
        Return basic statistics about the MUTCD collection.
        Used by the dashboard status panel.
        """
        if not self.collection:
            return {"ready": False}

        count = self.collection.count()
        return {
            "ready":           True,
            "collection_name": COLLECTION_NAME,
            "total_chunks":    count,
            "embedding_model": VOYAGE_MODEL,
            "claude_model":    CLAUDE_MODEL,
        }

    def query(self, question: str) -> dict:
        """
        Answer a question using the MUTCD 11th Edition.

        This is the main method called by the MUTCD Chatbot page.

        ARGS:
            question: The engineer's natural language question.
                      e.g. "What are the sign height requirements for a stop sign?"

        RETURNS:
            dict with keys:
                answer (str):          Answer text with inline section citations
                citations (list):      List of citation dicts
                chunks_used (int):     Number of sections retrieved
                sources_count (int):   Number of unique sections cited
                abstained (bool):      True if system couldn't find the answer
                model_used (str):      Claude model string
                token_usage (dict):    input_tokens, output_tokens
                elapsed_seconds (float)
                error (str|None):      Error message if query failed
        """
        if not self.is_ready():
            return self._error_result(
                "MUTCD engine not ready. " + (self._init_error or "Check system status.")
            )

        if not question or not question.strip():
            return self._error_result("Please enter a question.")

        start_time = time.time()

        try:
            # Step 1: Embed the question using Voyage AI
            query_embedding = self._embed_query(question)

            # Step 2: Retrieve the most relevant MUTCD sections from ChromaDB
            chunks = self._retrieve_chunks(query_embedding)

            # Step 3: If nothing found, abstain
            if not chunks:
                return self._abstain_result(question, start_time)

            # Step 4: Build the citation list
            citations = self._build_citations(chunks)

            # Step 5: Generate answer using Claude
            raw_answer, token_usage = self._generate_answer(question, chunks, citations)

            # Step 6: Filter to only actually-cited sources
            citations = self._filter_cited_sources(raw_answer, citations)

            # Step 7: Check if Claude abstained
            abstained = self._check_abstention(raw_answer)

            elapsed = round(time.time() - start_time, 2)

            return {
                "answer":          raw_answer,
                "citations":       citations,
                "chunks_used":     len(chunks),
                "sources_count":   len(citations),
                "abstained":       abstained,
                "model_used":      CLAUDE_MODEL,
                "token_usage":     token_usage,
                "elapsed_seconds": elapsed,
                "error":           None,
                # discrepancy_flag / discrepancy_note not applicable for MUTCD
                # (single authoritative source), but included for UI compatibility
                "discrepancy_flag": None,
                "discrepancy_note": None,
                # Legacy sources key for display compatibility
                "sources": [
                    {
                        "source_num":  c["number"],
                        "source_file": c["doc_title"],
                        "chunk_id":    c["chunk_id"],
                        "similarity":  c["similarity"],
                        "chunk_type":  "mutcd_section",
                    }
                    for c in citations
                ],
            }

        except Exception as e:
            return self._error_result(str(e))

    # ── Embedding ───────────────────────────────────────────────────────────

    def _embed_query(self, question: str) -> list:
        """
        Embed the user's question using Voyage AI voyage-3.

        This MUST use the same model (voyage-3) that was used to embed
        the MUTCD sections during corpus ingest. Mismatched models produce
        meaningless similarity scores.

        ARGS:
            question: The raw question text.

        RETURNS:
            List of floats (the embedding vector).
        """
        result = self.voyage_client.embed(
            texts=[question],
            model=VOYAGE_MODEL,
            input_type="query",   # "query" optimizes for retrieval queries
        )
        return result.embeddings[0]

    # ── Retrieval ───────────────────────────────────────────────────────────

    def _retrieve_chunks(self, query_embedding: list) -> list:
        """
        Retrieve the most relevant MUTCD sections from ChromaDB.

        We pass the pre-computed Voyage AI embedding directly to
        ChromaDB's query() method using query_embeddings=.
        This bypasses ChromaDB's internal embedding logic entirely —
        ChromaDB just does the nearest-neighbor search using the
        vector we provide.

        ARGS:
            query_embedding: Voyage AI embedding vector for the question.

        RETURNS:
            List of chunk dicts sorted by similarity (highest first).
        """
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=TOP_K_CHUNKS,
            include=["documents", "metadatas", "distances"],
        )

        chunks = []
        if not results["documents"] or not results["documents"][0]:
            return chunks

        ids = results.get("ids", [[]])[0]

        for i, (text, meta, distance) in enumerate(zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        )):
            # Convert ChromaDB L2 distance to similarity score (0-1 range)
            # Lower distance = higher similarity
            similarity = max(0.0, 1.0 - (distance / 2.0))

            if similarity < SIMILARITY_THRESHOLD:
                continue

            chunk_id = ids[i] if i < len(ids) else f"mutcd_chunk_{i}"

            chunks.append({
                "text":            text,
                "similarity":      round(similarity, 4),
                "chunk_id":        chunk_id,
                # MUTCD metadata fields set by 01_build_extract.ipynb
                "part":            meta.get("part", ""),
                "chapter":         meta.get("chapter", ""),
                "section_id":      meta.get("section_id", ""),
                "section_title":   meta.get("section_title", ""),
                "doc_title":       meta.get("doc_title", "MUTCD 11th Edition"),
                "source_citation": meta.get("source_citation", ""),
            })

        # Sort by similarity, best first
        chunks.sort(key=lambda c: c["similarity"], reverse=True)
        return chunks

    # ── Citation Building ───────────────────────────────────────────────────

    def _build_citations(self, chunks: list) -> list:
        """
        Build the numbered citation list from retrieved MUTCD sections.

        Each unique section_id gets one citation number.
        MUTCD corpus has one chunk per section, so this is usually 1:1.

        CITATION FORMAT:
            "MUTCD 11th Edition, Part 2B — Regulatory Signs,
             Section 2B.03 — Stop Sign"

        RETURNS:
            List of citation dicts ordered by first appearance.
        """
        seen_sections = {}
        citation_order = []

        for chunk in chunks:
            # Use section_id (e.g. "2B_03") as the deduplication key
            key = chunk["section_id"] or chunk["chunk_id"]

            if key not in seen_sections:
                seen_sections[key] = {
                    "number":          len(seen_sections) + 1,
                    "chunk_id":        chunk["chunk_id"],
                    "doc_title":       chunk["doc_title"],
                    "part":            chunk["part"],
                    "chapter":         chunk["chapter"],
                    "section_id":      chunk["section_id"],
                    "section_title":   chunk["section_title"],
                    "source_citation": chunk["source_citation"],
                    "formatted":       self._format_citation(chunk),
                    "similarity":      chunk["similarity"],
                }
                citation_order.append(key)
            else:
                # Keep highest similarity for this section
                if chunk["similarity"] > seen_sections[key]["similarity"]:
                    seen_sections[key]["similarity"] = chunk["similarity"]

        return [seen_sections[key] for key in citation_order]

    def _format_citation(self, chunk: dict) -> str:
        """
        Format a MUTCD section citation for display.

        Uses source_citation from metadata if available (set by ingest notebook).
        Falls back to constructing from part/chapter/section fields.

        EXAMPLE OUTPUT:
            "MUTCD 11th Edition, Part 2B — Regulatory Signs,
             Section 2B.03 — Stop Sign"
        """
        # Use pre-formatted citation from metadata if available
        if chunk.get("source_citation"):
            return chunk["source_citation"]

        # Build from available fields
        parts = ["MUTCD 11th Edition"]

        chapter = chunk.get("chapter", "")
        if chapter:
            parts.append(f"Chapter {chapter}")

        section_id    = chunk.get("section_id", "")
        section_title = chunk.get("section_title", "")

        if section_id and section_title:
            parts.append(f"Section {section_id} -- {section_title}")
        elif section_id:
            parts.append(f"Section {section_id}")

        return ", ".join(parts)

    # ── Answer Generation ───────────────────────────────────────────────────

    def _generate_answer(
        self,
        question: str,
        chunks: list,
        citations: list,
    ) -> tuple:
        """
        Call Claude to generate a grounded answer from MUTCD context.

        PROMPT STRATEGY:
            - The MUTCD is a single federal standard — no discrepancy detection
              needed (unlike the EPM engine which compares two source documents)
            - Require inline superscript citations referencing MUTCD sections
            - Require direct regulatory language ("shall", "should", "may")
              to be preserved — these have specific MUTCD meanings
            - Prohibit answers not grounded in the retrieved sections

        ARGS:
            question:  The engineer's question
            chunks:    Retrieved MUTCD sections
            citations: Numbered citation list

        RETURNS:
            (answer_text, token_usage_dict)
        """
        # Build context blocks — each retrieved MUTCD section as a numbered block
        context_blocks = []
        for chunk in chunks:
            key = chunk["section_id"] or chunk["chunk_id"]
            citation_num = next(
                (c["number"] for c in citations
                 if (c["section_id"] or c["chunk_id"]) == key),
                1
            )
            context_blocks.append(
                f"[CONTEXT {citation_num} -- {chunk['doc_title']}, "
                f"Section {chunk['section_id']} -- {chunk['section_title']}]\n"
                f"{chunk['text']}"
            )

        full_context = "\n\n".join(context_blocks)

        # Build citation reference list for Claude
        citation_list = "\n".join(
            f"  {c['number']}. {c['formatted']}"
            for c in citations
        )

        prompt = f"""You are the City of Brentwood Engineering AI Assistant.
You answer questions about the Manual on Uniform Traffic Control Devices (MUTCD),
11th Edition, for licensed engineers and support staff in the Engineering Department.

CONTEXT FROM THE MUTCD 11th EDITION:
{full_context}

CITATION NUMBERS ASSIGNED TO THE ABOVE SECTIONS:
{citation_list}

QUESTION: {question}

IMPORTANT -- MUTCD LANGUAGE CONVENTIONS:
The MUTCD uses specific modal verbs with precise regulatory meanings:
  - "shall" = mandatory requirement (must be followed)
  - "should" = advisory recommendation (strongly recommended)
  - "may" = permissive (allowed but not required)
  - "should not" = advisory prohibition
  - "shall not" = mandatory prohibition
Preserve these words exactly in your answer. Never substitute "must" for "shall"
or "recommend" for "should." The distinction matters for compliance.

ANSWER REQUIREMENTS:
1. Start with a direct sentence identifying the relevant MUTCD section(s).
2. Cite sources inline using superscript numbers (superscript 1, 2, 3, etc.)
   immediately after the statement they support.
   Example: "Stop signs shall be octagonal in shape.1"
   CRITICAL: Only use a citation number if that source directly supports the
   statement. Do not cite a source number that was not retrieved.
3. Preserve "shall," "should," and "may" exactly as they appear in the source.
4. Include specific measurements, dimensions, and values from the context.
5. If 3 or more requirements are listed, format them as bullet points --
   one requirement per line. Do not use numbered lists.
6. Do not use markdown formatting (no **, no ##, no ---).
7. Do not include information that is not in the provided context sections.
8. If the provided context does not contain sufficient information to answer
   the question, respond with exactly:
   "ABSTAIN: The provided MUTCD sections do not contain sufficient information
   to answer this question. Please consult the MUTCD 11th Edition directly or
   contact the City Engineer."

Write your answer now:"""

        response = self.claude_client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=MAX_ANSWER_TOKENS,
            temperature=TEMPERATURE,
            messages=[{"role": "user", "content": prompt}],
        )

        answer_text = response.content[0].text.strip()
        token_usage = {
            "input_tokens":  response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }

        return answer_text, token_usage

    def _filter_cited_sources(self, answer: str, citations: list) -> list:
        """
        Filter citations to only those actually referenced in the answer.
        Identical logic to rag_engine.py — superscript characters map to
        citation numbers.
        """
        SUPERSCRIPT_MAP = {
            chr(0x00B9): 1,   # superscript 1
            chr(0x00B2): 2,   # superscript 2
            chr(0x00B3): 3,   # superscript 3
            chr(0x2074): 4,   # superscript 4
            chr(0x2075): 5,   # superscript 5
            chr(0x2076): 6,   # superscript 6
            chr(0x2077): 7,   # superscript 7
            chr(0x2078): 8,   # superscript 8
            chr(0x2079): 9,   # superscript 9
        }

        used_numbers = set()
        for char, num in SUPERSCRIPT_MAP.items():
            if char in answer:
                used_numbers.add(num)

        if not used_numbers:
            return citations

        return [c for c in citations if c["number"] in used_numbers]

    # ── Helper Methods ──────────────────────────────────────────────────────

    def _check_abstention(self, answer: str) -> bool:
        """Return True if Claude indicated it could not answer from context."""
        markers = [
            "ABSTAIN:",
            "do not contain sufficient information",
            "not found in the provided",
            "cannot find this information",
        ]
        answer_lower = answer.lower()
        return any(m.lower() in answer_lower for m in markers)

    def _abstain_result(self, question: str, start_time: float) -> dict:
        """Return a structured abstention when no relevant sections were found."""
        elapsed = round(time.time() - start_time, 2)
        return {
            "answer": (
                "ABSTAIN: No relevant MUTCD sections were found for this question. "
                "Please consult the MUTCD 11th Edition directly at "
                "mutcd.fhwa.dot.gov or contact the City Engineer."
            ),
            "citations":         [],
            "chunks_used":       0,
            "sources_count":     0,
            "abstained":         True,
            "model_used":        CLAUDE_MODEL,
            "token_usage":       {"input_tokens": 0, "output_tokens": 0},
            "elapsed_seconds":   elapsed,
            "error":             None,
            "discrepancy_flag":  None,
            "discrepancy_note":  None,
            "sources":           [],
        }

    def _error_result(self, error_message: str) -> dict:
        """Return a structured error result for unexpected failures."""
        return {
            "answer":            f"An error occurred: {error_message}",
            "citations":         [],
            "chunks_used":       0,
            "sources_count":     0,
            "abstained":         False,
            "model_used":        CLAUDE_MODEL,
            "token_usage":       {"input_tokens": 0, "output_tokens": 0},
            "elapsed_seconds":   0,
            "error":             error_message,
            "discrepancy_flag":  None,
            "discrepancy_note":  None,
            "sources":           [],
        }


# -----------------------------------------------------------------------------
# STREAMLIT CACHE WRAPPER
# -----------------------------------------------------------------------------

@st.cache_resource(show_spinner=False)
def get_mutcd_rag_engine() -> MUTCDRAGEngine:
    """
    Create and cache the MUTCD RAG engine for the Streamlit session.

    @st.cache_resource means this runs once per server session.
    The Voyage AI client initializes quickly (no model download needed --
    embeddings are computed via API call at query time, not at startup).

    USAGE IN STREAMLIT PAGES:
        from utils.mutcd_rag_engine import get_mutcd_rag_engine

        engine = get_mutcd_rag_engine()
        if engine.is_ready():
            result = engine.query("What are the stop sign mounting height requirements?")

    RETURNS:
        Initialized MUTCDRAGEngine instance (may not be ready if init failed)
    """
    return MUTCDRAGEngine()
