# City of Brentwood Engineering AI Assistant — V2

Production AI assistant for the City of Brentwood, Tennessee Engineering Department.

## Overview

An AI-powered tool that answers municipal engineering policy questions by searching
26 source documents — the Engineering Policy Manual, all Municipal Code chapters, and
Appendix A Subdivision Regulations. All answers are grounded in the documents with
precise section citations. The system will not guess or fabricate information.

**Live application:** https://engineering-ai-assistant-brentwood.streamlit.app

## Features

- **Q&A Mode** — Ask natural language questions. Answers include footnote citations
  to specific code sections. System abstains when information is not found.
- **Wizard Mode** — Interactive plan review checklists with automatic comment generation.
  Exports to Word (.docx), LAMA CSV, and Bluebeam (.bax) formats.
- **Zero hallucination** — Responses are grounded exclusively in the 26 indexed documents.
- **Discrepancy detection** — Flags when the Engineering Policy Manual conflicts with
  or adds stricter requirements than the Municipal Code.

## Repository Structure

```
engineering-ai-assistant-v2/
├── app.py                          # Main dashboard and entry point
├── pages/
│   ├── 1_QA_Mode.py                # Q&A Mode page
│   └── 2_Wizard_Mode.py            # Wizard Mode page
├── utils/
│   ├── rag_engine.py               # Core RAG query engine (ChromaDB + Claude)
│   ├── drive_loader.py             # Database path loader
│   ├── database.py                 # Audit logging (SQLite)
│   ├── theme.py                    # Brentwood branding and UI components
│   ├── google_sheets.py            # Flagged response logging
│   ├── checklist_data.py           # Wizard checklist items
│   ├── comments_database.py        # Standard review comment library
│   └── document_registry.py       # 26-document registry with citation formats
├── build/
│   ├── build_corpus.py             # Corpus builder (run in Google Colab)
│   ├── section_chunker.py          # Document chunking engine
│   └── post_processor.py          # Pre-processing: injects prose summaries
├── vector_database/                # ChromaDB database (committed to repo)
├── models/
│   └── all-MiniLM-L6-v2/          # Bundled embedding model (loads in ~2s)
├── assets/
│   ├── BrentwoodCrestLogo-RGB.png
│   └── BrentwoodCrestLogo-BW.png
├── .streamlit/
│   └── config.toml                 # Theme and server configuration
└── requirements.txt                # Pinned Python dependencies
```

## Technical Stack

| Component | Technology | Version |
|---|---|---|
| Web framework | Streamlit | 1.43.2 |
| Vector database | ChromaDB | 1.5.5 |
| Embedding model | all-MiniLM-L6-v2 | via sentence-transformers 5.2.3 |
| AI model | Claude Sonnet (Anthropic) | claude-sonnet-4-5 |
| Document processing | python-docx | 1.1.2 |

## Corpus

- **26 source documents** — Engineering Policy Manual + 25 Municipal Code chapters
- **~3,100–3,300 chunks** — Section-aware chunking with overlap
- **3-pass retrieval** — Global search + targeted EPM pass + targeted zoning pass
- Rebuild required only when source documents are amended

## Updating the Document Database

1. Add or replace DOCX files in the Google Drive source folders
2. Open `Build_Vector_Database_V2.ipynb` in Google Colab
3. Run Step 1 (mount Drive, install dependencies)
4. Run Step 2 (build corpus) — set `BUILD_MODE = 'full'` or `'update'`
5. Run Step 3 (verify chunk count)
6. Run Step 4 (push database to GitHub)
7. Reboot the Streamlit app at the live URL above

## Streamlit Secrets Required

```toml
CLAUDE_API_KEY = "sk-ant-..."
HF_TOKEN = "hf_..."           # Optional — speeds up model load if bundled model missing
GOOGLE_SHEET_ID = "..."       # For flagged response logging
[gcp_service_account]         # Google service account for Sheets integration
```

## Development Notes

- ChromaDB version is pinned at `1.5.5` — do not upgrade without full rebuild and testing
- The embedding model must match between build time and runtime — changing it requires full rebuild
- The `torch.classes.__path__ = []` line at the top of each page file is required —
  removing it causes Streamlit's file watcher to crash on startup

## Project

Developed as the capstone project for ECE 570 (AI Systems) at Purdue University,
in collaboration with the City of Brentwood Engineering Department.
