"""
database.py
===========
City of Brentwood Engineering AI Assistant - V2
SQLite audit logging and administrative oversight.

PURPOSE:
    Every query, answer, citation, discrepancy flag, and user feedback
    action is recorded here. This provides:

    ACCOUNTABILITY — Who asked what, when, and what answer was given.
    SAFETY REVIEW  — Flagged responses are queued for engineer review.
    USAGE TRACKING — Query volume, abstention rates, discrepancy frequency.
    CONTINUOUS IMPROVEMENT — Patterns in flagged responses guide prompt tuning.

WHY SQLITE:
    SQLite is a single-file database. The file lives in Streamlit Cloud's
    /tmp filesystem. It persists within a session but resets on cold restart.
    This is acceptable for a 20-person engineering team — audit logs that
    need long-term retention should be exported to Google Sheets (handled
    by google_sheets.py for flagged responses).

    For permanent audit history, the Admin panel provides a CSV export.

DATABASE FILE LOCATION:
    /tmp/brentwood_audit.db  (Streamlit Cloud /tmp — writable, session-persistent)

SCHEMA OVERVIEW:
    query_logs        — every Q&A interaction (V1 compatible + V2 columns)
    flagged_responses — engineer-flagged answers needing review
    wizard_logs       — Wizard Mode permit review completions
    discrepancy_logs  — separate log of all discrepancy flags for review

V1 COMPATIBILITY:
    All V1 columns in query_logs are preserved exactly.
    V2 adds: citations_json, discrepancy_flag, abstained, elapsed_seconds.
    V1 pages (1_QA_Mode.py, 2_Wizard_Mode.py) continue to work unchanged.

AUTHOR:  City of Brentwood Engineering Department AI Assistant Project
VERSION: 2.0
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

# Where the SQLite database file is stored.
# /tmp is always writable on Streamlit Cloud.
DEFAULT_DB_PATH = "/tmp/brentwood_audit.db"

# How many recent queries to return by default.
DEFAULT_RECENT_LIMIT = 10


# ─────────────────────────────────────────────────────────────────────────────
# AUDIT LOGGER CLASS
# ─────────────────────────────────────────────────────────────────────────────

class AuditLogger:
    """
    SQLite-backed audit logger for the Engineering AI Assistant.

    Tracks every query, answer, citation, and user feedback event.
    Provides query methods for the Admin panel to display usage stats
    and flagged response queues.

    USAGE:
        logger = AuditLogger()
        logger.log_query(
            question="What is the minimum riparian buffer?",
            answer="The minimum buffer is 50 feet.¹",
            citations=[{"number": 1, "formatted": "Brentwood Municipal Code..."}],
            chunks_used=3,
            model_used="claude-sonnet-4-5-20250929",
            discrepancy_flag="more_restrictive",
            abstained=False,
            elapsed_seconds=2.3,
        )
    """

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        """
        Initialize the audit logger and create database tables if needed.

        ARGS:
            db_path: Path to the SQLite file. Created automatically if missing.
                     Parent directories are created if they don't exist.
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_database()

    # ── Database Setup ────────────────────────────────────────────────────

    def _initialize_database(self):
        """
        Create all tables if they don't already exist.

        Uses CREATE TABLE IF NOT EXISTS so this is safe to call on every
        app startup — it will not overwrite existing data.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # ── query_logs ────────────────────────────────────────────────
            # Records every Q&A interaction.
            # V1 columns preserved exactly. V2 columns added at the end
            # so existing queries against V1 columns still work.
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS query_logs (
                    id               INTEGER PRIMARY KEY AUTOINCREMENT,

                    -- V1 columns (preserved for backward compatibility)
                    timestamp        TEXT    NOT NULL,
                    question         TEXT    NOT NULL,
                    answer           TEXT    NOT NULL,
                    sources          TEXT,           -- JSON list (V1 format)
                    chunks_used      INTEGER,
                    model_used       TEXT,
                    user_session     TEXT,
                    response_time    REAL,

                    -- V2 columns (new in this version)
                    citations_json   TEXT,           -- JSON list of citation dicts
                    discrepancy_flag TEXT,           -- 'more_restrictive'|'conflict'|NULL
                    abstained        INTEGER DEFAULT 0,  -- 1 if system abstained
                    elapsed_seconds  REAL            -- total query time in seconds
                )
            """)

            # ── flagged_responses ─────────────────────────────────────────
            # Records answers that engineers flagged as incorrect or incomplete.
            # Status workflow: open → reviewed → resolved
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS flagged_responses (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp    TEXT    NOT NULL,
                    question     TEXT    NOT NULL,
                    answer       TEXT,
                    flag_type    TEXT    NOT NULL,   -- 'negative'|'incorrect'|'missing_info'
                    reason       TEXT,               -- engineer's free-text explanation
                    user_session TEXT,
                    status       TEXT    DEFAULT 'open'  -- 'open'|'reviewed'|'resolved'
                )
            """)

            # ── wizard_logs ───────────────────────────────────────────────
            # Records completed Wizard Mode permit review sessions.
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS wizard_logs (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp       TEXT    NOT NULL,
                    wizard_type     TEXT    NOT NULL,   -- e.g. 'site_plan', 'stormwater'
                    data            TEXT,               -- JSON: form inputs
                    checklist       TEXT,               -- JSON: checklist results
                    user_session    TEXT,
                    completion_time REAL                -- seconds to complete
                )
            """)

            # ── discrepancy_logs ──────────────────────────────────────────
            # Separate log for all discrepancy flags — lets administrators
            # monitor how often code/policy conflicts arise and which sections
            # are involved. Used to prioritize manual updates.
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS discrepancy_logs (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp       TEXT    NOT NULL,
                    question        TEXT    NOT NULL,
                    flag_type       TEXT    NOT NULL,   -- 'more_restrictive'|'conflict'
                    flag_note       TEXT,               -- explanation shown to user
                    doc_ids_involved TEXT,              -- JSON list of doc_ids in context
                    query_log_id    INTEGER             -- FK to query_logs.id
                )
            """)

            conn.commit()

    # ── Write Methods ─────────────────────────────────────────────────────

    def log_query(
        self,
        question:         str,
        answer:           str,
        sources:          Optional[list] = None,   # V1 compatible
        chunks_used:      int   = 0,
        model_used:       str   = "unknown",
        user_session:     str   = "anonymous",
        # V2 additions
        citations:        Optional[list] = None,
        discrepancy_flag: Optional[str]  = None,
        abstained:        bool  = False,
        elapsed_seconds:  float = 0.0,
    ) -> int:
        """
        Log a completed Q&A query.

        Called by the Streamlit page immediately after a successful query.

        ARGS:
            question:         The engineer's question (plain text)
            answer:           Claude's answer (with superscript citations)
            sources:          V1-format source list (for backward compatibility)
            chunks_used:      How many ChromaDB chunks were retrieved
            model_used:       Claude model string
            user_session:     Streamlit session ID or 'anonymous'
            citations:        V2 citation list (list of citation dicts)
            discrepancy_flag: 'more_restrictive' | 'conflict' | None
            abstained:        True if system couldn't answer from context
            elapsed_seconds:  Total query processing time

        RETURNS:
            The new row ID (int), or -1 if logging failed.
        """
        timestamp      = datetime.now().isoformat()
        sources_json   = json.dumps(sources)   if sources   else "[]"
        citations_json = json.dumps(citations) if citations else "[]"

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO query_logs
                    (timestamp, question, answer, sources, chunks_used, model_used,
                     user_session, citations_json, discrepancy_flag, abstained,
                     elapsed_seconds)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    timestamp, question, answer, sources_json, chunks_used,
                    model_used, user_session, citations_json, discrepancy_flag,
                    1 if abstained else 0, elapsed_seconds,
                ))
                row_id = cursor.lastrowid
                conn.commit()
                return row_id

        except Exception as e:
            print(f"AuditLogger.log_query error: {e}")
            return -1

    def log_discrepancy(
        self,
        question:          str,
        flag_type:         str,
        flag_note:         str,
        doc_ids_involved:  Optional[list] = None,
        query_log_id:      int = -1,
    ):
        """
        Record a discrepancy flag in the dedicated discrepancy_logs table.

        Called automatically by log_query when discrepancy_flag is not None.
        This gives administrators a focused view of code/policy conflicts
        without having to scan all query logs.

        ARGS:
            question:         The question that triggered the flag
            flag_type:        'more_restrictive' or 'conflict'
            flag_note:        The explanation text shown to the user
            doc_ids_involved: List of doc_ids from the retrieved chunks
            query_log_id:     FK to the corresponding query_logs row
        """
        timestamp = datetime.now().isoformat()
        doc_ids_json = json.dumps(doc_ids_involved) if doc_ids_involved else "[]"

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO discrepancy_logs
                    (timestamp, question, flag_type, flag_note,
                     doc_ids_involved, query_log_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    timestamp, question, flag_type, flag_note,
                    doc_ids_json, query_log_id,
                ))
                conn.commit()

        except Exception as e:
            print(f"AuditLogger.log_discrepancy error: {e}")

    def flag_response(
        self,
        question:     str,
        flag_type:    str  = "negative",
        reason:       str  = "",
        answer:       str  = "",
        user_session: str  = "anonymous",
    ):
        """
        Record a response that an engineer flagged as problematic.

        Called when the engineer clicks "👎 Needs Improvement" and
        submits the feedback form.

        ARGS:
            question:     The original question
            flag_type:    'negative' | 'incorrect' | 'missing_info' | 'other'
            reason:       Engineer's free-text explanation of the problem
            answer:       The AI answer that was flagged
            user_session: Streamlit session ID
        """
        timestamp = datetime.now().isoformat()

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO flagged_responses
                    (timestamp, question, answer, flag_type, reason, user_session)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (timestamp, question, answer, flag_type, reason, user_session))
                conn.commit()

        except Exception as e:
            print(f"AuditLogger.flag_response error: {e}")

    def log_wizard_completion(
        self,
        wizard_type:     str,
        data:            Optional[dict] = None,
        checklist:       Optional[list] = None,
        user_session:    str = "anonymous",
        completion_time: float = 0.0,
    ):
        """
        Record a completed Wizard Mode session.

        Called when an engineer finishes a permit review workflow.

        ARGS:
            wizard_type:     Type of wizard (e.g. 'site_plan_review')
            data:            Form input data as a dict
            checklist:       Completed checklist items as a list
            user_session:    Streamlit session ID
            completion_time: Seconds from start to finish
        """
        timestamp      = datetime.now().isoformat()
        data_json      = json.dumps(data)      if data      else "{}"
        checklist_json = json.dumps(checklist) if checklist else "[]"

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO wizard_logs
                    (timestamp, wizard_type, data, checklist,
                     user_session, completion_time)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    timestamp, wizard_type, data_json, checklist_json,
                    user_session, completion_time,
                ))
                conn.commit()

        except Exception as e:
            print(f"AuditLogger.log_wizard_completion error: {e}")

    # ── Read Methods ──────────────────────────────────────────────────────

    def get_recent_queries(self, limit: int = DEFAULT_RECENT_LIMIT) -> list:
        """
        Return the most recent queries, newest first.

        Used by the Q&A page sidebar to show recent query history,
        and by the Admin panel for the full query log view.

        ARGS:
            limit: Maximum number of queries to return.

        RETURNS:
            List of dicts with keys:
                id, timestamp, question, answer, chunks_used,
                model_used, discrepancy_flag, abstained,
                elapsed_seconds, sources_count
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, timestamp, question, answer, chunks_used,
                           model_used, discrepancy_flag, abstained, elapsed_seconds
                    FROM query_logs
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (limit,))

                rows = cursor.fetchall()
                return [
                    {
                        "id":               row[0],
                        "timestamp":        row[1],
                        "question":         row[2],
                        "answer":           row[3],
                        "chunks_used":      row[4],
                        "model_used":       row[5],
                        "discrepancy_flag": row[6],
                        "abstained":        bool(row[7]),
                        "elapsed_seconds":  row[8],
                        # V1 compatible alias
                        "sources_count":    row[4] or 0,
                    }
                    for row in rows
                ]

        except Exception as e:
            print(f"AuditLogger.get_recent_queries error: {e}")
            return []

    def get_flagged_responses(self, status: str = "open") -> list:
        """
        Return flagged responses filtered by review status.

        Used by the Admin panel to display the review queue.

        ARGS:
            status: 'open' | 'reviewed' | 'resolved' | 'all'

        RETURNS:
            List of dicts with keys:
                id, timestamp, question, answer, flag_type, reason, status
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                if status == "all":
                    cursor.execute("""
                        SELECT id, timestamp, question, answer, flag_type, reason, status
                        FROM flagged_responses
                        ORDER BY timestamp DESC
                    """)
                else:
                    cursor.execute("""
                        SELECT id, timestamp, question, answer, flag_type, reason, status
                        FROM flagged_responses
                        WHERE status = ?
                        ORDER BY timestamp DESC
                    """, (status,))

                rows = cursor.fetchall()
                return [
                    {
                        "id":        row[0],
                        "timestamp": row[1],
                        "question":  row[2],
                        "answer":    row[3],
                        "flag_type": row[4],
                        "reason":    row[5],
                        "status":    row[6],
                    }
                    for row in rows
                ]

        except Exception as e:
            print(f"AuditLogger.get_flagged_responses error: {e}")
            return []

    def get_discrepancy_log(self, limit: int = 50) -> list:
        """
        Return recent discrepancy flags for administrative review.

        Lets the City Engineer see which questions are triggering
        code/policy conflicts — useful for identifying sections of
        the Engineering Manual that need clarification or update.

        ARGS:
            limit: Maximum number of records to return.

        RETURNS:
            List of dicts with keys:
                timestamp, question, flag_type, flag_note, doc_ids_involved
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT timestamp, question, flag_type, flag_note,
                           doc_ids_involved
                    FROM discrepancy_logs
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (limit,))

                rows = cursor.fetchall()
                return [
                    {
                        "timestamp":          row[0],
                        "question":           row[1],
                        "flag_type":          row[2],
                        "flag_note":          row[3],
                        "doc_ids_involved":   json.loads(row[4]) if row[4] else [],
                    }
                    for row in rows
                ]

        except Exception as e:
            print(f"AuditLogger.get_discrepancy_log error: {e}")
            return []

    def get_usage_stats(self, days: int = 7) -> dict:
        """
        Return usage statistics for the past N days.

        Used by the Admin panel dashboard to show:
        - Query volume
        - Abstention rate (how often system couldn't answer)
        - Discrepancy flag rate (how often code/policy conflicts arose)
        - User satisfaction (inverse of flag rate)

        ARGS:
            days: Number of days to look back. Default 7.

        RETURNS:
            dict with keys:
                total_queries, flagged_responses, wizard_completions,
                abstention_count, discrepancy_count,
                satisfaction_rate, abstention_rate, discrepancy_rate
        """
        try:
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Total queries in window
                cursor.execute(
                    "SELECT COUNT(*) FROM query_logs WHERE timestamp >= ?",
                    (cutoff,)
                )
                total_queries = cursor.fetchone()[0]

                # Flagged responses in window
                cursor.execute(
                    "SELECT COUNT(*) FROM flagged_responses WHERE timestamp >= ?",
                    (cutoff,)
                )
                flagged_count = cursor.fetchone()[0]

                # Wizard completions in window
                cursor.execute(
                    "SELECT COUNT(*) FROM wizard_logs WHERE timestamp >= ?",
                    (cutoff,)
                )
                wizard_completions = cursor.fetchone()[0]

                # Abstention count (V2 column — may be 0 on V1 DB)
                try:
                    cursor.execute("""
                        SELECT COUNT(*) FROM query_logs
                        WHERE timestamp >= ? AND abstained = 1
                    """, (cutoff,))
                    abstention_count = cursor.fetchone()[0]
                except Exception:
                    abstention_count = 0

                # Discrepancy flag count
                try:
                    cursor.execute(
                        "SELECT COUNT(*) FROM discrepancy_logs WHERE timestamp >= ?",
                        (cutoff,)
                    )
                    discrepancy_count = cursor.fetchone()[0]
                except Exception:
                    discrepancy_count = 0

            # Compute rates (guard against division by zero)
            q = max(total_queries, 1)
            satisfaction_rate  = round(max(0.0, 100 - (flagged_count   * 100 / q)), 1)
            abstention_rate    = round((abstention_count  * 100 / q), 1)
            discrepancy_rate   = round((discrepancy_count * 100 / q), 1)

            return {
                "total_queries":      total_queries,
                "flagged_responses":  flagged_count,
                "wizard_completions": wizard_completions,
                "abstention_count":   abstention_count,
                "discrepancy_count":  discrepancy_count,
                "satisfaction_rate":  satisfaction_rate,
                "abstention_rate":    abstention_rate,
                "discrepancy_rate":   discrepancy_rate,
            }

        except Exception as e:
            print(f"AuditLogger.get_usage_stats error: {e}")
            return {
                "total_queries":      0,
                "flagged_responses":  0,
                "wizard_completions": 0,
                "abstention_count":   0,
                "discrepancy_count":  0,
                "satisfaction_rate":  0.0,
                "abstention_rate":    0.0,
                "discrepancy_rate":   0.0,
            }

    def export_query_log_csv(self, days: int = 30) -> str:
        """
        Export the query log as a CSV string for the Admin panel download.

        ARGS:
            days: How many days of history to include.

        RETURNS:
            CSV-formatted string with header row.
            Empty string if no records or on error.
        """
        try:
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT timestamp, question, answer, chunks_used,
                           model_used, discrepancy_flag, abstained, elapsed_seconds
                    FROM query_logs
                    WHERE timestamp >= ?
                    ORDER BY timestamp DESC
                """, (cutoff,))
                rows = cursor.fetchall()

            if not rows:
                return ""

            import io, csv
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow([
                "Timestamp", "Question", "Answer", "Chunks Used",
                "Model", "Discrepancy Flag", "Abstained", "Elapsed Seconds"
            ])
            for row in rows:
                writer.writerow(list(row))

            return output.getvalue()

        except Exception as e:
            print(f"AuditLogger.export_query_log_csv error: {e}")
            return ""

    def get_database_info(self) -> dict:
        """
        Return metadata about the database file for the Admin panel.

        RETURNS:
            dict with: path, size_kb, total_queries_alltime,
                       total_flagged_alltime, table_names
        """
        try:
            size_kb = round(self.db_path.stat().st_size / 1024, 1) \
                      if self.db_path.exists() else 0

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute("SELECT COUNT(*) FROM query_logs")
                total_queries = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM flagged_responses")
                total_flagged = cursor.fetchone()[0]

                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
                table_names = [row[0] for row in cursor.fetchall()]

            return {
                "path":                  str(self.db_path),
                "size_kb":               size_kb,
                "total_queries_alltime": total_queries,
                "total_flagged_alltime": total_flagged,
                "table_names":           table_names,
            }

        except Exception as e:
            print(f"AuditLogger.get_database_info error: {e}")
            return {
                "path":                  str(self.db_path),
                "size_kb":               0,
                "total_queries_alltime": 0,
                "total_flagged_alltime": 0,
                "table_names":           [],
            }
