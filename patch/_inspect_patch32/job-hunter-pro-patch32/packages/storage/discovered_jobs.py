"""
Discovered Jobs Storage (Patch 32).

Separate table from applications - stores jobs scraped during discovery mode
before any apply action.

Lifecycle:
  scraped -> reviewed -> selected/skipped -> applied (moved to applications)
"""
from __future__ import annotations
import sqlite3
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List
from loguru import logger


DB_PATH = Path("data/applications.db")


STATUS_DISCOVERED = "discovered"     # Just scraped, no action yet
STATUS_SELECTED = "selected"         # User marked for apply
STATUS_AUTO_APPLY = "auto_apply"     # Rule-based auto-apply queued
STATUS_SKIPPED = "skipped"           # User explicitly skipped
STATUS_SAVED = "saved"               # Saved for later review
STATUS_APPLIED = "applied"           # Already applied (moved)
STATUS_FAILED = "failed"             # Apply attempted but failed


def init_schema(db_path=None):
    """Create discovered_jobs table if not exists."""
    path = db_path or DB_PATH
    try:
        conn = sqlite3.connect(str(path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS discovered_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                job_id TEXT NOT NULL,
                title TEXT,
                company TEXT,
                location TEXT,
                url TEXT,
                description TEXT,
                salary TEXT,
                fit_score INTEGER,
                fit_reasoning TEXT,
                is_easy_apply INTEGER DEFAULT 0,
                status TEXT DEFAULT 'discovered',
                scheduled_at INTEGER,
                discovered_at INTEGER NOT NULL,
                reviewed_at INTEGER,
                applied_at INTEGER,
                user_notes TEXT,
                metadata TEXT,
                UNIQUE(platform, job_id)
            )
        """)
        
        # Index for fast queries
        conn.execute("CREATE INDEX IF NOT EXISTS idx_discovered_status ON discovered_jobs(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_discovered_at ON discovered_jobs(discovered_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_discovered_fit ON discovered_jobs(fit_score)")
        
        conn.commit()
        conn.close()
        logger.debug("discovered_jobs schema initialized")
    except Exception as e:
        logger.error(f"Schema init failed: {e}")


def save_discovered(job_data: dict, db_path=None) -> Optional[int]:
    """
    Save a discovered job to DB. Returns inserted row id, or None on duplicate.
    
    Args:
        job_data: dict with keys: platform, job_id, title, company, location,
                   url, description, salary, fit_score, fit_reasoning,
                   is_easy_apply
    """
    path = db_path or DB_PATH
    try:
        conn = sqlite3.connect(str(path))
        cursor = conn.execute("""
            INSERT OR IGNORE INTO discovered_jobs
            (platform, job_id, title, company, location, url, description,
             salary, fit_score, fit_reasoning, is_easy_apply, status,
             discovered_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            job_data.get("platform", ""),
            job_data.get("job_id", ""),
            job_data.get("title", ""),
            job_data.get("company", ""),
            job_data.get("location", ""),
            job_data.get("url", ""),
            (job_data.get("description") or "")[:5000],  # Cap description
            job_data.get("salary", ""),
            job_data.get("fit_score"),
            job_data.get("fit_reasoning", ""),
            1 if job_data.get("is_easy_apply") else 0,
            STATUS_DISCOVERED,
            int(time.time()),
            json.dumps(job_data.get("metadata", {})),
        ))
        conn.commit()
        row_id = cursor.lastrowid
        conn.close()
        return row_id if row_id else None
    except Exception as e:
        logger.debug(f"Save discovered failed: {e}")
        return None


def list_discovered(status: Optional[str] = None, platform: Optional[str] = None,
                     min_fit: Optional[int] = None, days: Optional[int] = None,
                     limit: int = 500, db_path=None) -> List[dict]:
    """
    List discovered jobs with filters.
    
    Args:
        status: filter by status (None = all)
        platform: filter by platform
        min_fit: minimum fit_score
        days: only jobs discovered within last N days
        limit: max rows
    """
    path = db_path or DB_PATH
    try:
        conn = sqlite3.connect(str(path))
        conn.row_factory = sqlite3.Row
        
        where_clauses = []
        params = []
        
        if status:
            where_clauses.append("status = ?")
            params.append(status)
        
        if platform:
            where_clauses.append("platform = ?")
            params.append(platform)
        
        if min_fit is not None:
            where_clauses.append("(fit_score >= ? OR fit_score IS NULL)")
            params.append(min_fit)
        
        if days:
            cutoff = int(time.time()) - (days * 86400)
            where_clauses.append("discovered_at >= ?")
            params.append(cutoff)
        
        where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
        
        sql = f"""
            SELECT * FROM discovered_jobs
            {where_sql}
            ORDER BY 
              CASE WHEN fit_score IS NULL THEN 0 ELSE 1 END DESC,
              fit_score DESC,
              discovered_at DESC
            LIMIT ?
        """
        params.append(limit)
        
        cursor = conn.execute(sql, params)
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        logger.error(f"List discovered failed: {e}")
        return []


def update_status(job_ids: List[int], new_status: str,
                   scheduled_at: Optional[int] = None,
                   notes: Optional[str] = None, db_path=None) -> int:
    """Bulk update status of multiple discovered jobs. Returns updated count."""
    if not job_ids:
        return 0
    
    path = db_path or DB_PATH
    try:
        conn = sqlite3.connect(str(path))
        
        placeholders = ",".join("?" for _ in job_ids)
        params = [new_status, int(time.time())]
        
        update_sql = "UPDATE discovered_jobs SET status = ?, reviewed_at = ?"
        
        if scheduled_at:
            update_sql += ", scheduled_at = ?"
            params.append(scheduled_at)
        
        if notes:
            update_sql += ", user_notes = ?"
            params.append(notes)
        
        update_sql += f" WHERE id IN ({placeholders})"
        params.extend(job_ids)
        
        cursor = conn.execute(update_sql, params)
        conn.commit()
        count = cursor.rowcount
        conn.close()
        return count
    except Exception as e:
        logger.error(f"Update status failed: {e}")
        return 0


def get_by_ids(job_ids: List[int], db_path=None) -> List[dict]:
    """Get multiple discovered jobs by IDs."""
    if not job_ids:
        return []
    
    path = db_path or DB_PATH
    try:
        conn = sqlite3.connect(str(path))
        conn.row_factory = sqlite3.Row
        placeholders = ",".join("?" for _ in job_ids)
        cursor = conn.execute(
            f"SELECT * FROM discovered_jobs WHERE id IN ({placeholders})",
            job_ids
        )
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        logger.error(f"Get by ids failed: {e}")
        return []


def get_stats(db_path=None) -> dict:
    """Get discovery stats."""
    path = db_path or DB_PATH
    try:
        conn = sqlite3.connect(str(path))
        cursor = conn.execute("""
            SELECT status, COUNT(*) FROM discovered_jobs GROUP BY status
        """)
        by_status = dict(cursor.fetchall())
        
        cursor = conn.execute("SELECT COUNT(*) FROM discovered_jobs")
        total = cursor.fetchone()[0]
        
        cursor = conn.execute("""
            SELECT platform, COUNT(*) FROM discovered_jobs GROUP BY platform
        """)
        by_platform = dict(cursor.fetchall())
        
        cursor = conn.execute("""
            SELECT AVG(fit_score) FROM discovered_jobs WHERE fit_score IS NOT NULL
        """)
        avg_fit = cursor.fetchone()[0]
        
        conn.close()
        return {
            "total": total,
            "by_status": by_status,
            "by_platform": by_platform,
            "avg_fit_score": int(avg_fit) if avg_fit else None,
        }
    except Exception as e:
        logger.debug(f"Stats failed: {e}")
        return {"total": 0}


def cleanup_old(days: int = 30, db_path=None) -> int:
    """Delete discovered jobs older than N days (excludes applied/saved)."""
    path = db_path or DB_PATH
    try:
        conn = sqlite3.connect(str(path))
        cutoff = int(time.time()) - (days * 86400)
        cursor = conn.execute("""
            DELETE FROM discovered_jobs
            WHERE discovered_at < ?
              AND status NOT IN ('applied', 'saved', 'auto_apply')
        """, (cutoff,))
        conn.commit()
        count = cursor.rowcount
        conn.close()
        if count > 0:
            logger.info(f"Cleaned up {count} old discovered jobs")
        return count
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        return 0