"""
rag_engine.py
=============
City of Brentwood Engineering AI Assistant - V2
Core RAG (Retrieval-Augmented Generation) query engine.

PURPOSE:
    This is the brain of the assistant. When an engineer asks a question,
    this module:

    1. SEARCHES ChromaDB for the most relevant chunks across all 26 documents
    2. DETECTS whether multiple documents answer the same question (potential
       discrepancies between Municipal Code and Engineering Policy Manual)
    3. BUILDS a structured prompt with all retrieved context
    4. CALLS Claude to generate a grounded answer
    5. FORMATS the response with footnote-style citations (¹ ² ³)
    6. FLAGS discrepancies or "more restrictive policy" situations

HOW CITATIONS WORK:
    Inline superscripts reference a numbered list at the bottom:
        "Riparian buffers must be at least 50 feet wide.¹ Perennial streams
        require 75 feet.²"

        ¹ Brentwood Municipal Code, Chapter 56 — Stormwater Management,
          Sec. 56-31 — Riparian Buffer Requirements
        ² City of Brentwood Engineering Dept. Policy Manual — Riparian Buffers

HOW DISCREPANCY FLAGS WORK:
    ⚠️  More Restrictive Policy — Manual imposes requirements beyond the code.
        Both requirements apply. Engineers should follow the stricter standard.

    🔴 Discrepancy Identified — Sources appear to conflict.
        Do not rely on this response alone. Defer to the City Engineer.

WHAT THIS MODULE DOES NOT DO:
    - It never fabricates information
    - It never resolves discrepancies between sources
    - It never cites sources it did not retrieve
    - It never answers from model training — only from retrieved chunks

AUTHOR:  City of Brentwood Engineering Department AI Assistant Project
VERSION: 2.0
"""

import re
import time
from pathlib import Path
from typing import Optional

import streamlit as st

# ChromaDB — our vector database
import chromadb
from chromadb.utils import embedding_functions

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

# Model used for generating answers.
# Must match Anthropic's current model string exactly.
# Verified working in production as of March 2026.
# If the API returns a model-not-found error, check Anthropic's model list at:
#   https://docs.anthropic.com/en/docs/about-claude/models
CLAUDE_MODEL = "claude-sonnet-4-5-20250929"

# ChromaDB collection name — must match what build_corpus.py created.
COLLECTION_NAME = "brentwood_engineering_v2"

# Embedding model — MUST match what build_corpus.py used.
# Changing this requires a full corpus rebuild.
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# How many chunks to retrieve from ChromaDB per query.
# More chunks = more context = better coverage but higher token cost.
# 8 is a good balance for municipal policy questions.
TOP_K_CHUNKS = 12

# Minimum similarity score (0.0–1.0) to include a chunk.
# Chunks below this threshold are discarded as probably irrelevant.
# 0.35 is intentionally permissive — better to include borderline chunks
# than miss something and fabricate.
SIMILARITY_THRESHOLD = 0.35

# Maximum tokens Claude may use in its answer.
MAX_ANSWER_TOKENS = 1500

# Temperature for Claude — always 0.0 for factual/policy work.
# Higher temperature = more creative but less consistent.
# Zero = deterministic, no hallucination-inducing randomness.
TEMPERATURE = 0.0

# Content type labels used in chunk metadata (set by section_chunker.py)
CONTENT_TYPE_MUNICIPAL_CODE  = "municipal_code"
CONTENT_TYPE_APPENDIX        = "appendix"
CONTENT_TYPE_ENGINEERING_POL = "engineering_policy"
CONTENT_TYPE_CODE_REF        = "code_reference"
CONTENT_TYPE_EXTERNAL_REF    = "external_reference"

# Document categories for discrepancy detection
CODE_CONTENT_TYPES   = {CONTENT_TYPE_MUNICIPAL_CODE, CONTENT_TYPE_APPENDIX}
POLICY_CONTENT_TYPES = {CONTENT_TYPE_ENGINEERING_POL, CONTENT_TYPE_CODE_REF,
                        CONTENT_TYPE_EXTERNAL_REF}


# ─────────────────────────────────────────────────────────────────────────────
# RAG ENGINE CLASS
# ─────────────────────────────────────────────────────────────────────────────

class RAGEngine:
    """
    Multi-document Retrieval-Augmented Generation engine for the
    City of Brentwood Engineering AI Assistant.

    LIFECYCLE:
        engine = RAGEngine(db_path="/tmp/brentwood_v2_db")
        if engine.is_ready():
            result = engine.query("What is the minimum riparian buffer width?")
            print(result['answer'])
            for citation in result['citations']:
                print(citation['formatted'])

    The engine is initialized once and reused across all queries in a
    Streamlit session (stored in st.session_state).
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the RAG engine.

        ARGS:
            db_path: Path to the local ChromaDB directory.
                     If None, reads LOCAL_DB_PATH from drive_loader.
                     Explicit path is preferred for testability.
        """
        self.db_path      = db_path
        self.chroma_client = None
        self.collection    = None
        self.claude_client = None
        self.is_initialized = False
        self._init_error   = None

        try:
            self._initialize()
        except Exception as e:
            self._init_error = str(e)
            print(f"RAGEngine initialization failed: {e}")

    # ── Initialization ────────────────────────────────────────────────────

    def _initialize(self):
        """
        Set up ChromaDB connection and Claude API client.
        Called once during __init__.
        """
        self._connect_chromadb()
        self._connect_claude()
        self.is_initialized = True

    def _connect_chromadb(self):
        """
        Connect to the local ChromaDB database downloaded by drive_loader.

        ChromaDB stores its data as files on disk. We point it at the
        directory where drive_loader.py saved the downloaded files.
        """
        # Determine database path
        if self.db_path:
            db_directory = self.db_path
        else:
            # Import here to avoid circular imports at module load time
            from utils.drive_loader import LOCAL_DB_PATH
            db_directory = LOCAL_DB_PATH

        db_path_obj = Path(db_directory)
        if not db_path_obj.exists():
            raise FileNotFoundError(
                f"ChromaDB directory not found at '{db_directory}'. "
                "The database may not have been downloaded yet. "
                "Check drive_loader status on the Admin panel."
            )

        # Create embedding function — must match what build_corpus.py used.
        #
        # MODEL LOADING STRATEGY (fastest to slowest):
        #
        # 1. BUNDLED (instant, ~2s): If models/all-MiniLM-L6-v2 exists in the repo,
        #    load directly from disk. No network needed. Run download_model_to_repo.py
        #    in Colab once to set this up.
        #
        # 2. CACHED (fast after first run): If HF_TOKEN is set in Streamlit secrets,
        #    downloads authenticated (~15s). Subsequent loads use the session cache.
        #
        # 3. ANONYMOUS (slow, may rate-limit): Falls back to unauthenticated download.
        #    Streamlit Cloud's shared IPs often hit HuggingFace's 429 rate limit.
        import os
        hf_token = None
        try:
            hf_token = st.secrets.get("HF_TOKEN")
        except Exception:
            pass

        # Check for bundled model in the repo first (fastest path)
        bundled_model_path = Path(__file__).parent.parent / "models" / EMBEDDING_MODEL
        if bundled_model_path.exists() and any(bundled_model_path.iterdir()):
            # Load from local disk — no HuggingFace download required
            model_source = str(bundled_model_path)
            print(f"Loading embedding model from bundled repo path: {model_source}")
        else:
            # Fall back to HuggingFace download
            model_source = EMBEDDING_MODEL
            cache_dir = str(Path(__file__).parent.parent / ".cache" / "sentence_transformers")
            print(f"Bundled model not found — downloading {EMBEDDING_MODEL} from HuggingFace...")

        embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=model_source,
            **({"cache_folder": str(Path(__file__).parent.parent / ".cache" / "sentence_transformers")}
               if model_source == EMBEDDING_MODEL else {}),
            **({"token": hf_token} if (hf_token and model_source == EMBEDDING_MODEL) else {}),
        )

        # Connect to ChromaDB
        self.chroma_client = chromadb.PersistentClient(path=str(db_path_obj))

        # Load the collection
        try:
            self.collection = self.chroma_client.get_collection(
                name=COLLECTION_NAME,
                embedding_function=embed_fn,
            )
            count = self.collection.count()
            print(f"ChromaDB connected: '{COLLECTION_NAME}' — {count:,} chunks")

        except Exception as e:
            raise RuntimeError(
                f"Collection '{COLLECTION_NAME}' not found in ChromaDB. "
                f"Has build_corpus.py been run? Error: {e}"
            )

    def _connect_claude(self):
        """
        Set up the Anthropic API client using the key from Streamlit secrets.
        """
        import anthropic

        try:
            api_key = st.secrets.get("CLAUDE_API_KEY")
        except Exception:
            # Fallback for environments without Streamlit (e.g. unit tests)
            import os
            api_key = os.environ.get("CLAUDE_API_KEY")

        if not api_key:
            raise ValueError(
                "CLAUDE_API_KEY not found in Streamlit secrets. "
                "Add it to your .streamlit/secrets.toml file."
            )

        self.claude_client = anthropic.Anthropic(api_key=api_key)
        print("Claude API client connected")

    # ── Public API ────────────────────────────────────────────────────────

    def is_ready(self) -> bool:
        """Return True if the engine is fully initialized and ready to query."""
        return (
            self.is_initialized
            and self.collection is not None
            and self.claude_client is not None
        )

    def get_init_error(self) -> Optional[str]:
        """Return the initialization error message, or None if init succeeded."""
        return self._init_error

    def get_collection_stats(self) -> dict:
        """
        Return basic statistics about the loaded collection.
        Used by the Admin panel to show corpus health.
        """
        if not self.collection:
            return {"ready": False}

        count = self.collection.count()
        return {
            "ready":           True,
            "collection_name": COLLECTION_NAME,
            "total_chunks":    count,
            "embedding_model": EMBEDDING_MODEL,
            "claude_model":    CLAUDE_MODEL,
        }

    def query(self, question: str) -> dict:
        """
        Answer an engineering policy question using retrieved context.

        This is the main public method called by the Streamlit pages.

        ARGS:
            question: The engineer's natural language question.
                      e.g. "What is the minimum riparian buffer for a perennial stream?"

        RETURNS:
            dict with keys:
                answer (str):          Formatted answer with inline superscripts
                citations (list):      List of citation dicts (see _build_citations)
                discrepancy_flag (str|None):  "more_restrictive" | "conflict" | None
                discrepancy_note (str|None):  Explanation text if flagged
                chunks_used (int):     Number of chunks that contributed
                sources_count (int):   Number of unique documents cited
                abstained (bool):      True if system couldn't find relevant info
                model_used (str):      Claude model string
                token_usage (dict):    input_tokens, output_tokens
                elapsed_seconds (float): Total query time
                error (str|None):      Error message if query failed
        """
        if not self.is_ready():
            return self._error_result(
                "System not ready. " + (self._init_error or "Check Admin panel.")
            )

        if not question or not question.strip():
            return self._error_result("Please enter a question.")

        start_time = time.time()

        try:
            # Step 1: Retrieve relevant chunks from ChromaDB
            chunks = self._retrieve_chunks(question)

            # Step 2: Check if we found anything useful
            if not chunks:
                return self._abstain_result(question, start_time)

            # Step 3: Detect potential discrepancies between code and policy
            discrepancy_flag, discrepancy_note = self._detect_discrepancy(chunks)

            # Step 4: Build the citations list (numbered, formatted)
            citations = self._build_citations(chunks)

            # Step 5: Generate answer using Claude
            raw_answer, token_usage = self._generate_answer(
                question, chunks, citations, discrepancy_flag
            )

            # Step 6: Parse discrepancy signal Claude embedded in answer
            if discrepancy_flag == "claude_will_decide":
                discrepancy_flag, discrepancy_note, raw_answer = (
                    self._parse_discrepancy_from_answer(raw_answer)
                )

            # Step 6b: Filter citation list to only sources actually cited
            # in the answer text — removes irrelevant retrieved chunks from
            # the displayed source list.
            citations = self._filter_cited_sources(raw_answer, citations)

            # Step 7: Check if Claude abstained (couldn't find the answer)
            abstained = self._check_abstention(raw_answer)

            elapsed = round(time.time() - start_time, 2)

            return {
                "answer":            raw_answer,
                "citations":         citations,
                "discrepancy_flag":  discrepancy_flag,
                "discrepancy_note":  discrepancy_note,
                "chunks_used":       len(chunks),
                "sources_count":     len(citations),
                "abstained":         abstained,
                "model_used":        CLAUDE_MODEL,
                "token_usage":       token_usage,
                "elapsed_seconds":   elapsed,
                "error":             None,
                # Legacy key kept for compatibility with V1 QA page display
                "sources": [
                    {
                        "source_num":  c["number"],
                        "source_file": c["doc_title"],
                        "chunk_id":    c["chunk_id"],
                        "similarity":  c["similarity"],
                        "chunk_type":  c["content_type"],
                    }
                    for c in citations
                ],
            }

        except Exception as e:
            return self._error_result(str(e))

    # ── Retrieval ─────────────────────────────────────────────────────────

    def _retrieve_chunks(self, question: str) -> list:
        """
        Hybrid retrieval: two-pass search to ensure Engineering Policy Manual
        content is always included alongside Municipal Code results.

        PASS 1 — Global search: Top 12 chunks from all 26 documents.
        PASS 2 — EPM search: Top 4 chunks filtered to Engineering Policy Manual
                 documents only (doc_id: epm, appendix_a).

        WHY TWO PASSES:
            The Engineering Policy Manual often contains the most detailed
            operational guidance (e.g. paved vs. unpaved grades, as-built
            survey requirements) but scores lower than Municipal Code chunks
            because the Code uses more direct regulatory language that matches
            question phrasing better. Without a targeted EPM pass, these
            critical policy details get crowded out.

        Results are merged and deduplicated. EPM chunks from Pass 2 are
        included even if their similarity score is below the global top-K
        cutoff, provided they meet the minimum similarity threshold.

        ARGS:
            question: The engineer's question (plain text)

        RETURNS:
            List of chunk dicts, sorted by similarity (highest first).
        """
        seen_chunk_ids = set()
        chunks = []

        def _parse_results(results, min_similarity=SIMILARITY_THRESHOLD):
            """Parse a ChromaDB result set into chunk dicts."""
            parsed = []
            if not results["documents"] or not results["documents"][0]:
                return parsed
            # ChromaDB stores the chunk_id as the record ID (not in metadata).
            # We must read it from results["ids"], not from meta.get("chunk_id").
            ids = results.get("ids", [[]])[0]
            for i, (text, meta, distance) in enumerate(zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            )):
                similarity = max(0.0, 1.0 - (distance / 2.0))
                if similarity < min_similarity:
                    continue
                chunk_id = ids[i] if i < len(ids) else meta.get("chunk_id", f"chunk_{i}")
                if chunk_id in seen_chunk_ids:
                    continue
                seen_chunk_ids.add(chunk_id)
                parsed.append({
                    "text":            text,
                    "similarity":      round(similarity, 4),
                    "chunk_id":        chunk_id,
                    "doc_id":          meta.get("doc_id", ""),
                    "doc_title":       meta.get("doc_title", "Unknown Document"),
                    "content_type":    meta.get("content_type", ""),
                    "section_number":  meta.get("section_number", ""),
                    "section_title":   meta.get("section_title", ""),
                    "source_citation": meta.get("source_citation", ""),
                    "article":         meta.get("article", ""),
                    "division":        meta.get("division", ""),
                })
            return parsed

        # ── Pass 1: Global search across all documents ─────────────────────
        global_results = self.collection.query(
            query_texts=[question],
            n_results=TOP_K_CHUNKS,
            include=["documents", "metadatas", "distances"],
        )
        chunks.extend(_parse_results(global_results))

        # ── Pass 2: Targeted EPM search ────────────────────────────────────
        # Always pull the top 4 Engineering Policy Manual chunks for this
        # question, regardless of how they ranked in the global search.
        # This guarantees detailed policy guidance is never crowded out
        # by higher-scoring Municipal Code chunks.
        EPM_DOC_IDS = ["epm"]
        try:
            epm_results = self.collection.query(
                query_texts=[question],
                n_results=4,
                where={"doc_id": {"$in": EPM_DOC_IDS}},
                include=["documents", "metadatas", "distances"],
            )
            chunks.extend(_parse_results(epm_results, min_similarity=0.30))
        except Exception:
            # If filtered query fails, continue with global results only
            pass

        # ── Pass 3: Targeted Chapter 78 (Zoning) search ────────────────────
        # Zoning questions (setbacks, lot size, height limits, permitted uses,
        # district standards) often lose to other chapters in the global search
        # because similar regulatory language appears across all chapters.
        # A dedicated ch78 pass guarantees the correct zoning section is
        # always included when a zoning question is asked.
        #
        # Example failure case without this pass:
        #   Q: "What are the R-2 zoning technical standards?"
        #   Global pass returns R-1 and arterial standards at higher scores
        #   than the correct Sec. 78-164 — correct answer never reaches Claude.
        ZONING_KEYWORDS = (
            "zoning", "r-1", "r-2", "r-3", "r-4", "ar ", "ar-", "osrd",
            "setback", "lot size", "lot area", "building height", "lot width",
            "permitted use", "conditional use", "variance", "district",
            "front yard", "rear yard", "side yard", "lot coverage",
            "accessory building", "home occupation", "buffer strip",
            "building envelope", "technical standard",
        )
        question_lower = question.lower()
        is_zoning_question = any(kw in question_lower for kw in ZONING_KEYWORDS)

        if is_zoning_question:
            try:
                ch78_results = self.collection.query(
                    query_texts=[question],
                    n_results=6,
                    where={"doc_id": "ch78"},
                    include=["documents", "metadatas", "distances"],
                )
                chunks.extend(_parse_results(ch78_results, min_similarity=0.30))
            except Exception:
                pass

        # ── Pass 4: Direct metadata retrieval for named sections/districts ────
        #
        # WHY SIMILARITY-BASED RETRIEVAL FAILS HERE:
        #   All zoning district technical-standards sections use identical
        #   language ("minimum required lot area", "maximum lot coverage", etc.).
        #   When the question asks for R-2 standards, R-1, R-3, and R-4 chunks
        #   score equally high in vector similarity — the correct section loses
        #   the ranking competition every time.
        #
        # THE FIX — metadata filtering, not similarity:
        #   Every chunk has a `section_number` metadata field (e.g. "78-164").
        #   ChromaDB's `where` clause retrieves chunks by metadata value directly,
        #   bypassing similarity scoring entirely. This guarantees the correct
        #   section is always included in context — no scoring competition.
        #
        # TWO TRIGGER PATHS:
        #
        #   Path A — Named zoning district in question:
        #     "R-2" → section_number "78-164"
        #     "R-1" → section_number "78-124"  etc.
        #     Filters to doc_id="ch78" for efficiency.
        #
        #   Path B — Explicit section number in question:
        #     "Sec. 56-31", "section 78-164", "78-486" → section_number match
        #     Searches all docs (any chapter can be referenced).
        #     Works for stormwater, streets, utilities — any chapter.
        #
        # DISTRICT → SECTION NUMBER MAP (Chapter 78, City of Brentwood):
        #   R-1  → 78-124   R-2  → 78-164   R-3  → 78-204   R-4  → 78-244
        #   AR   → 78-84    OSRD → 78-284
        DISTRICT_SECTION_MAP = {
            "r-2":  ("78-164", "ch78"),
            " r2 ": ("78-164", "ch78"),
            "r-1":  ("78-124", "ch78"),
            " r1 ": ("78-124", "ch78"),
            "r-3":  ("78-204", "ch78"),
            " r3 ": ("78-204", "ch78"),
            "r-4":  ("78-244", "ch78"),
            " r4 ": ("78-244", "ch78"),
            "osrd": ("78-284", "ch78"),
        }

        target_section = None
        target_doc_id  = None

        # Path A: named zoning district
        for district_kw, (section_num, doc_id) in DISTRICT_SECTION_MAP.items():
            if district_kw in question_lower:
                target_section = section_num
                target_doc_id  = doc_id
                break

        # Path B: explicit section number anywhere in question
        # Matches: "Sec. 56-31", "section 78-164", "78-486", "sec 14-22"
        if not target_section:
            sec_match = re.search(
                r'(?:sec(?:tion)?\.?\s*)?(\d{2,3}-\d{1,4})', question_lower
            )
            if sec_match:
                target_section = sec_match.group(1)
                target_doc_id  = None  # any chapter

        if target_section:
            try:
                # Build the metadata where clause
                where_clause = {"section_number": {"$eq": target_section}}
                if target_doc_id:
                    where_clause = {
                        "$and": [
                            {"doc_id":        {"$eq": target_doc_id}},
                            {"section_number": {"$eq": target_section}},
                        ]
                    }

                # Use collection.get() — pure metadata filter, no similarity.
                # This retrieves ALL chunks whose section_number matches,
                # regardless of their vector similarity to the question.
                direct_results = self.collection.get(
                    where=where_clause,
                    include=["documents", "metadatas"],
                )

                if direct_results["documents"]:
                    ids = direct_results.get("ids", [])
                    for i, (text, meta) in enumerate(zip(
                        direct_results["documents"],
                        direct_results["metadatas"],
                    )):
                        chunk_id = ids[i] if i < len(ids) else f"direct_{i}"
                        if chunk_id in seen_chunk_ids:
                            continue
                        seen_chunk_ids.add(chunk_id)
                        # Assign a high similarity so these chunks sort near
                        # the top — they are directly relevant by definition.
                        chunks.append({
                            "text":            text,
                            "similarity":      0.90,
                            "chunk_id":        chunk_id,
                            "doc_id":          meta.get("doc_id", ""),
                            "doc_title":       meta.get("doc_title", "Unknown Document"),
                            "content_type":    meta.get("content_type", ""),
                            "section_number":  meta.get("section_number", ""),
                            "section_title":   meta.get("section_title", ""),
                            "source_citation": meta.get("source_citation", ""),
                            "article":         meta.get("article", ""),
                            "division":        meta.get("division", ""),
                        })
            except Exception:
                pass

        # Sort all chunks by similarity, best first
        chunks.sort(key=lambda c: c["similarity"], reverse=True)
        return chunks

    # ── Discrepancy Detection ─────────────────────────────────────────────

    def _detect_discrepancy(self, chunks: list) -> tuple:
        """
        Check whether the retrieved chunks contain both Municipal Code
        content and Engineering Policy content that actually conflict.

        LOGIC:
            discrepancy detection is deferred to Claude during answer
            generation. Claude reads both sources and returns a signal
            in the first line of its answer:

            DISCREPANCY:CONFLICT    — sources directly contradict
            DISCREPANCY:RESTRICTIVE — policy adds stricter requirements
            DISCREPANCY:NONE        — sources agree or are complementary

            This method returns a sentinel that tells _generate_answer
            to ask Claude to make the determination, then _parse_discrepancy
            reads Claude's actual answer to set the final flag.

        RETURNS:
            ("claude_will_decide", None) when both source types present,
            (None, None) when only one source type present.
        """
        code_chunks   = [c for c in chunks if c["content_type"] in CODE_CONTENT_TYPES]
        policy_chunks = [c for c in chunks if c["content_type"] in POLICY_CONTENT_TYPES]

        if not code_chunks or not policy_chunks:
            return None, None

        # Both source types present — ask Claude to assess
        return "claude_will_decide", None

    def _parse_discrepancy_from_answer(self, answer: str) -> tuple:
        """
        Read the discrepancy signal Claude embedded in its answer.
        Called after _generate_answer returns.

        Claude is instructed to start its answer with one of:
            DISCREPANCY:CONFLICT
            DISCREPANCY:RESTRICTIVE
            DISCREPANCY:NONE
        followed by a newline, then the actual answer text.

        Returns (flag, note, cleaned_answer).
        """
        lines = answer.strip().split("\n", 1)
        first_line = lines[0].strip()
        rest = lines[1].strip() if len(lines) > 1 else answer

        if first_line == "DISCREPANCY:CONFLICT":
            note = (
                "Sources from the Municipal Code and Engineering Policy Manual "
                "appear to conflict on this topic. Do not rely on this response "
                "alone. Defer to the City Engineer for binding interpretation."
            )
            return "conflict", note, rest

        elif first_line == "DISCREPANCY:RESTRICTIVE":
            note = (
                "The Engineering Policy Manual references requirements from the "
                "Municipal Code. The Manual may impose stricter standards than "
                "the Code alone. Both sets of requirements apply — follow the "
                "more restrictive standard."
            )
            return "more_restrictive", note, rest

        elif first_line == "DISCREPANCY:NONE":
            return None, None, rest

        else:
            # Claude didn't return the expected signal — treat as no flag
            # and return the full answer unchanged
            return None, None, answer

    # ── Citation Building ─────────────────────────────────────────────────

    def _build_citations(self, chunks: list) -> list:
        """
        Build the numbered citation list from retrieved chunks.

        Each unique source_citation string gets one citation number.
        Multiple chunks from the same section share one citation number.

        CITATION FORMAT BY CONTENT TYPE:
            municipal_code / appendix:
                "Brentwood Municipal Code, Chapter 56 — Stormwater Management,
                 Sec. 56-31 — Riparian Buffer Requirements"

            engineering_policy:
                "City of Brentwood Engineering Dept. Policy Manual —
                 Retaining Walls"

            code_reference:
                "Brentwood Municipal Code, Sec. 78-486
                 (referenced in Engineering Policy Manual)"

            external_reference:
                "[TDEC Stormwater Design Guidelines]
                 (cited in Engineering Policy Manual)"

        RETURNS:
            List of citation dicts, one per unique source, in order of
            first appearance. Each dict has:
                number (int):       Citation number (1, 2, 3...)
                chunk_id (str):     First chunk_id for this citation
                doc_id (str):       Document identifier
                doc_title (str):    Human-readable document title
                content_type (str): Content type tag
                section_number (str)
                section_title (str)
                source_citation (str): Raw citation string from metadata
                formatted (str):    Display string for the citation list
                similarity (float): Best similarity score for this citation
        """
        seen_citations = {}  # source_citation → citation dict
        citation_order = []  # ordered list of unique source_citations

        for chunk in chunks:
            citation_key = chunk["source_citation"] or chunk["chunk_id"]

            if citation_key not in seen_citations:
                seen_citations[citation_key] = {
                    "number":          len(seen_citations) + 1,
                    "chunk_id":        chunk["chunk_id"],
                    "doc_id":          chunk["doc_id"],
                    "doc_title":       chunk["doc_title"],
                    "content_type":    chunk["content_type"],
                    "section_number":  chunk["section_number"],
                    "section_title":   chunk["section_title"],
                    "source_citation": chunk["source_citation"],
                    "formatted":       self._format_citation(chunk),
                    "similarity":      chunk["similarity"],
                }
                citation_order.append(citation_key)
            else:
                # Keep the highest similarity score for this citation
                existing = seen_citations[citation_key]
                if chunk["similarity"] > existing["similarity"]:
                    existing["similarity"] = chunk["similarity"]

        return [seen_citations[key] for key in citation_order]

    def _format_citation(self, chunk: dict) -> str:
        """
        Format a single citation for display in the citation list.

        Uses the source_citation string from the chunk metadata,
        which was set by section_chunker.py using document_registry.py's
        format_citation() function. Falls back gracefully if missing.
        """
        # Use the pre-formatted citation from metadata if available
        if chunk["source_citation"]:
            return chunk["source_citation"]

        # Fallback: construct from available fields
        content_type = chunk["content_type"]
        doc_title    = chunk["doc_title"]
        section_num  = chunk["section_number"]
        section_title = chunk["section_title"]

        if content_type in CODE_CONTENT_TYPES:
            base = f"Brentwood Municipal Code — {doc_title}"
            if section_num and section_title:
                return f"{base}, Sec. {section_num} — {section_title}"
            elif section_num:
                return f"{base}, Sec. {section_num}"
            return base

        elif content_type == CONTENT_TYPE_ENGINEERING_POL:
            base = "City of Brentwood Engineering Dept. Policy Manual"
            if section_title:
                return f"{base} — {section_title}"
            return base

        elif content_type == CONTENT_TYPE_CODE_REF:
            base = f"Brentwood Municipal Code, Sec. {section_num}"
            return f"{base} (referenced in Engineering Policy Manual)"

        elif content_type == CONTENT_TYPE_EXTERNAL_REF:
            return f"{doc_title} (cited in Engineering Policy Manual)"

        return doc_title or "City of Brentwood Engineering Documents"

    # ── Answer Generation ─────────────────────────────────────────────────

    def _generate_answer(
        self,
        question: str,
        chunks: list,
        citations: list,
        discrepancy_flag: Optional[str],
    ) -> tuple:
        """
        Call Claude to generate a grounded answer with inline citations.

        PROMPT STRATEGY:
            - Provide all retrieved chunks as numbered context blocks
            - Tell Claude which citation number corresponds to each chunk
            - Require inline superscripts in the answer (¹ ² ³)
            - Require a direct answer in the first sentence
            - Prohibit markdown formatting (### ** etc.)
            - Prohibit any information not in the provided context
            - Require abstention phrase if context doesn't answer the question

        ARGS:
            question:         The engineer's question
            chunks:           Retrieved context chunks
            citations:        Numbered citation list (built by _build_citations)
            discrepancy_flag: "more_restrictive" | "conflict" | None

        RETURNS:
            (answer_text, token_usage_dict)
        """
        # Build the context block
        # Map each chunk to its citation number
        context_blocks = []
        for i, chunk in enumerate(chunks):
            # Find this chunk's citation number
            citation_key = chunk["source_citation"] or chunk["chunk_id"]
            citation_num = next(
                (c["number"] for c in citations
                 if (c["source_citation"] or c["chunk_id"]) == citation_key),
                i + 1
            )
            context_blocks.append(
                f"[CONTEXT {citation_num} — {chunk['doc_title']}]\n"
                f"{chunk['text']}"
            )

        full_context = "\n\n".join(context_blocks)

        # Build the citation reference list for Claude
        citation_list = "\n".join(
            f"  {c['number']}. {c['formatted']}"
            for c in citations
        )

        # Build discrepancy instruction if needed
        discrepancy_instruction = ""
        if discrepancy_flag == "claude_will_decide":
            discrepancy_instruction = (
                "\n\nDISCREPANCY ASSESSMENT REQUIRED: Both Municipal Code and "
                "Engineering Policy Manual sources are present. Before writing "
                "your answer, determine whether the sources agree, conflict, or "
                "the policy adds stricter requirements than the code.\n"
                "Start your entire response with EXACTLY one of these three lines "
                "(nothing before it, nothing after it on that line):\n"
                "  DISCREPANCY:NONE        (sources agree or are complementary)\n"
                "  DISCREPANCY:RESTRICTIVE (policy adds stricter requirements)\n"
                "  DISCREPANCY:CONFLICT    (sources directly contradict each other)\n"
                "Then on the next line begin your answer normally."
            )

        prompt = f"""You are the City of Brentwood Engineering AI Assistant.
You answer questions about municipal engineering policy for licensed engineers
and support staff in the Engineering Department.

CONTEXT FROM BRENTWOOD ENGINEERING DOCUMENTS:
{full_context}

CITATION NUMBERS ASSIGNED TO THE ABOVE SOURCES:
{citation_list}

QUESTION: {question}
{discrepancy_instruction}

CRITICAL — HOW TO READ MUNICIPAL CODE CONTEXT:
Municipal code stores requirements as inline numbered items. Example:
  "(1) Minimum required lot area, one acre. (2) Maximum lot coverage by all
   buildings, 25 percent. (3) Minimum required lot width at building line, 125
   feet. (4) Minimum required front yard setback, 75 feet."

EACH NUMBERED ITEM IS A COMPLETE, BINDING REQUIREMENT. When a context block
contains a section labeled "Technical standards" or "Minimum standards" with
numbered items, those items ARE the full answer. You must enumerate ALL of them.

If the question asks for "technical standards" or "dimensional standards" or
"development standards" for a named district or section, and ANY context block
contains a numbered list from that section, your answer MUST list every numbered
item from that section. Do not summarize. Do not paraphrase into a shorter list.
Do not abstain. Present each requirement on its own line in this format:
  (1) [requirement text]
  (2) [requirement text]
  ...and so on for all items found across all context blocks for that section.

If a section's items are split across multiple context blocks (e.g. items 1-8
in one block, items 9-11 in another), combine them into one complete list.

ANSWER REQUIREMENTS:
1. Start with a direct sentence identifying which section and district applies.
2. Then list ALL numbered requirements found in the context for that section.
3. Use superscript numbers (¹ ² ³ ⁴ ⁵ ⁶ ⁷ ⁸) inline to cite your sources.
   Place the citation superscript once, after the introductory sentence.
   Example: "The following minimum technical standards apply to the R-2 district
   per Sec. 78-164:¹ (1) Minimum required lot area, one acre. (2) ..."
   CRITICAL: Only cite sources you actually used. Do not cite a source number
   unless that source directly supports the statement it follows.
4. Include ALL specific numbers, measurements, and requirements from the context.
5. CRITICAL: Synthesize ALL provided context blocks. Items 1-8 may be in one
   block and items 9-11 in another — combine them. Never stop at the first block.
6. Do not use markdown formatting (no **, no ##, no ---).
7. Do not include information that is not in the provided context.
8. ABSTAIN only if — after carefully reading EVERY numbered item in EVERY context
   block — the information genuinely does not exist anywhere in the provided
   context. Never abstain when numbered list items directly answer the question.
   If the context truly does not contain enough information, respond with exactly:
   "ABSTAIN: The provided documents do not contain sufficient information to
   answer this question. Please consult the Engineering Manual directly or
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
        Filter the citation list to only include sources that were actually
        cited (referenced by superscript number) in the answer text.

        WHY THIS MATTERS:
            The retriever pulls up to 12 chunks for context, but Claude may
            only use 2-3 of them in its answer. Showing all 12 as "sources"
            is misleading — it implies the answer draws from all of them,
            which violates the zero-hallucination / full-accountability goal.

        HOW IT WORKS:
            Superscript unicode characters ¹²³⁴⁵⁶⁷⁸⁹ correspond to
            citation numbers 1-9. This method finds every superscript in
            the answer, collects the corresponding citation numbers, and
            returns only those citation dicts.

            If Claude cited ¹ ² ⁶ in an answer with 9 available sources,
            only citations 1, 2, and 6 are returned — and they keep their
            original numbers (no renumbering) so the superscripts still
            match in the displayed answer.

        ARGS:
            answer (str):      The answer text with inline superscripts
            citations (list):  Full citation list from _build_citations()

        RETURNS:
            Filtered list containing only cited sources, in original order.
        """
        # Map each superscript character to its integer citation number
        SUPERSCRIPT_MAP = {
            '¹': 1, '²': 2, '³': 3, '⁴': 4, '⁵': 5,
            '⁶': 6, '⁷': 7, '⁸': 8, '⁹': 9, '⁰': 10,
        }

        # Find all superscript numbers used in the answer
        used_numbers = set()
        for char, num in SUPERSCRIPT_MAP.items():
            if char in answer:
                used_numbers.add(num)

        if not used_numbers:
            # Claude wrote an answer with no citations at all —
            # return all citations so the source list isn't empty
            return citations

        # Return only citations whose number appears in the answer
        return [c for c in citations if c["number"] in used_numbers]

    # ── Helper Methods ────────────────────────────────────────────────────

    def _check_abstention(self, answer: str) -> bool:
        """
        Return True if Claude's answer indicates it could not find
        the information in the provided context.
        """
        abstention_markers = [
            "ABSTAIN:",
            "do not contain sufficient information",
            "not found in the provided",
            "cannot find this information",
            "not addressed in the",
        ]
        answer_lower = answer.lower()
        return any(marker.lower() in answer_lower for marker in abstention_markers)

    def _abstain_result(self, question: str, start_time: float) -> dict:
        """
        Return a structured abstention response when no relevant chunks
        were found in the database.
        """
        elapsed = round(time.time() - start_time, 2)
        return {
            "answer": (
                "ABSTAIN: No relevant content was found in the Brentwood "
                "Engineering documents for this question. Please consult the "
                "Engineering Manual directly or contact the City Engineer."
            ),
            "citations":         [],
            "discrepancy_flag":  None,
            "discrepancy_note":  None,
            "chunks_used":       0,
            "sources_count":     0,
            "abstained":         True,
            "model_used":        CLAUDE_MODEL,
            "token_usage":       {"input_tokens": 0, "output_tokens": 0},
            "elapsed_seconds":   elapsed,
            "error":             None,
            "sources":           [],
        }

    def _error_result(self, error_message: str) -> dict:
        """
        Return a structured error response for unexpected failures.
        """
        return {
            "answer": f"An error occurred: {error_message}",
            "citations":         [],
            "discrepancy_flag":  None,
            "discrepancy_note":  None,
            "chunks_used":       0,
            "sources_count":     0,
            "abstained":         False,
            "model_used":        CLAUDE_MODEL,
            "token_usage":       {"input_tokens": 0, "output_tokens": 0},
            "elapsed_seconds":   0,
            "error":             error_message,
            "sources":           [],
        }


# ─────────────────────────────────────────────────────────────────────────────
# STREAMLIT CACHE WRAPPER
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_resource(show_spinner=False)
def get_rag_engine(db_path: str) -> RAGEngine:
    """
    Create and cache the RAG engine for the Streamlit session.

    @st.cache_resource means this runs once per server session,
    not once per user or browser refresh. The embedding model
    (all-MiniLM-L6-v2) takes ~5 seconds to load the first time —
    caching prevents reloading it on every page navigation.

    USAGE IN STREAMLIT PAGES:
        from utils.rag_engine import get_rag_engine
        from utils.drive_loader import load_database

        db_info = load_database()
        if db_info["success"]:
            engine = get_rag_engine(db_info["local_path"])
            result = engine.query("What is the minimum buffer width?")

    ARGS:
        db_path: Local path to ChromaDB directory (from drive_loader)

    RETURNS:
        Initialized RAGEngine instance (may not be ready if init failed)
    """
    return RAGEngine(db_path=db_path)
