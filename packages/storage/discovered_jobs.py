"""Discovered jobs storage for discovery/curation mode."""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Optional

from loguru import logger


DB_PATH = Path("data/applications.db")

STATUS_DISCOVERED = "discovered"
STATUS_SELECTED = "selected"
STATUS_AUTO_APPLY = "auto_apply"
STATUS_SKIPPED = "skipped"
STATUS_SAVED = "saved"
STATUS_APPLIED = "applied"
STATUS_FAILED = "failed"


def init_schema(db_path: Optional[Path] = None) -> None:
    path = Path(db_path or DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(path)) as conn:
        conn.execute(
            """
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
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_discovered_status ON discovered_jobs(status)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_discovered_at ON discovered_jobs(discovered_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_discovered_fit ON discovered_jobs(fit_score)"
        )


def save_discovered(job_data: dict, db_path: Optional[Path] = None) -> Optional[int]:
    path = Path(db_path or DB_PATH)
    platform = (job_data.get("platform") or "").strip().lower()
    job_id = str(job_data.get("job_id") or "").strip()
    discovered_at = int(time.time())
    try:
        with sqlite3.connect(str(path)) as conn:
            conn.execute(
                """
                INSERT INTO discovered_jobs (
                    platform, job_id, title, company, location, url, description,
                    salary, fit_score, fit_reasoning, is_easy_apply, status,
                    discovered_at, metadata
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(platform, job_id) DO UPDATE SET
                    title = CASE
                        WHEN excluded.title != '' THEN excluded.title
                        ELSE discovered_jobs.title
                    END,
                    company = CASE
                        WHEN excluded.company != '' THEN excluded.company
                        ELSE discovered_jobs.company
                    END,
                    location = CASE
                        WHEN excluded.location != '' THEN excluded.location
                        ELSE discovered_jobs.location
                    END,
                    url = CASE
                        WHEN excluded.url != '' THEN excluded.url
                        ELSE discovered_jobs.url
                    END,
                    description = CASE
                        WHEN excluded.description != '' THEN excluded.description
                        ELSE discovered_jobs.description
                    END,
                    salary = CASE
                        WHEN excluded.salary != '' THEN excluded.salary
                        ELSE discovered_jobs.salary
                    END,
                    fit_score = COALESCE(excluded.fit_score, discovered_jobs.fit_score),
                    fit_reasoning = CASE
                        WHEN excluded.fit_reasoning != '' THEN excluded.fit_reasoning
                        ELSE discovered_jobs.fit_reasoning
                    END,
                    is_easy_apply = CASE
                        WHEN excluded.is_easy_apply IS NOT NULL THEN excluded.is_easy_apply
                        ELSE discovered_jobs.is_easy_apply
                    END,
                    status = CASE
                        WHEN discovered_jobs.status IN ('selected', 'saved', 'applied', 'failed', 'auto_apply')
                            THEN discovered_jobs.status
                        ELSE excluded.status
                    END,
                    discovered_at = excluded.discovered_at,
                    metadata = CASE
                        WHEN excluded.metadata != '{}' THEN excluded.metadata
                        ELSE discovered_jobs.metadata
                    END
                """,
                (
                    platform,
                    job_id,
                    job_data.get("title") or "",
                    job_data.get("company") or "",
                    job_data.get("location") or "",
                    job_data.get("url") or "",
                    (job_data.get("description") or "")[:8000],
                    job_data.get("salary") or "",
                    job_data.get("fit_score"),
                    job_data.get("fit_reasoning") or "",
                    1 if job_data.get("is_easy_apply") else 0,
                    job_data.get("status") or STATUS_DISCOVERED,
                    discovered_at,
                    json.dumps(job_data.get("metadata") or {}, ensure_ascii=False),
                ),
            )
            row = conn.execute(
                "SELECT id FROM discovered_jobs WHERE platform = ? AND job_id = ?",
                (platform, job_id),
            ).fetchone()
            return int(row[0]) if row and row[0] is not None else None
    except Exception as e:
        logger.debug(f"save_discovered failed: {e}")
        return None


def list_missing_fit_scores(
    limit: int = 100,
    platform: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> list[dict]:
    path = Path(db_path or DB_PATH)
    try:
        with sqlite3.connect(str(path)) as conn:
            conn.row_factory = sqlite3.Row
            where = ["fit_score IS NULL", "COALESCE(description, '') != ''"]
            params: list[object] = []
            if platform:
                where.append("LOWER(platform) = ?")
                params.append(platform.lower())
            rows = conn.execute(
                f"""
                SELECT *
                FROM discovered_jobs
                WHERE {' AND '.join(where)}
                ORDER BY discovered_at DESC
                LIMIT ?
                """,
                [*params, limit],
            ).fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"list_missing_fit_scores failed: {e}")
        return []


def list_missing_salaries(
    limit: int = 100,
    platform: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> list[dict]:
    path = Path(db_path or DB_PATH)
    try:
        with sqlite3.connect(str(path)) as conn:
            conn.row_factory = sqlite3.Row
            where = ["COALESCE(salary, '') = ''", "COALESCE(description, '') != ''"]
            params: list[object] = []
            if platform:
                where.append("LOWER(platform) = ?")
                params.append(platform.lower())
            rows = conn.execute(
                f"""
                SELECT *
                FROM discovered_jobs
                WHERE {' AND '.join(where)}
                ORDER BY discovered_at DESC
                LIMIT ?
                """,
                [*params, limit],
            ).fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"list_missing_salaries failed: {e}")
        return []


def update_enrichment(
    record_id: int,
    *,
    fit_score: Optional[int] = None,
    fit_reasoning: Optional[str] = None,
    salary: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> bool:
    path = Path(db_path or DB_PATH)
    updates: list[str] = []
    params: list[object] = []
    if fit_score is not None:
        updates.append("fit_score = ?")
        params.append(int(fit_score))
    if fit_reasoning is not None:
        updates.append("fit_reasoning = ?")
        params.append(str(fit_reasoning))
    if salary is not None:
        updates.append("salary = ?")
        params.append(str(salary))
    if not updates:
        return False
    params.append(int(record_id))
    try:
        with sqlite3.connect(str(path)) as conn:
            cursor = conn.execute(
                f"UPDATE discovered_jobs SET {', '.join(updates)} WHERE id = ?",
                params,
            )
            return bool(cursor.rowcount)
    except Exception as e:
        logger.error(f"update_enrichment failed: {e}")
        return False


def list_discovered(
    status: Optional[str] = None,
    platform: Optional[str] = None,
    min_fit: Optional[int] = None,
    days: Optional[int] = None,
    limit: int = 500,
    db_path: Optional[Path] = None,
) -> list[dict]:
    path = Path(db_path or DB_PATH)
    try:
        with sqlite3.connect(str(path)) as conn:
            conn.row_factory = sqlite3.Row
            where = []
            params: list[object] = []

            if status:
                where.append("status = ?")
                params.append(status)
            if platform:
                where.append("LOWER(platform) = ?")
                params.append(platform.lower())
            if min_fit is not None:
                where.append("(fit_score >= ? OR fit_score IS NULL)")
                params.append(min_fit)
            if days:
                where.append("discovered_at >= ?")
                params.append(int(time.time()) - (days * 86400))

            where_sql = f"WHERE {' AND '.join(where)}" if where else ""
            rows = conn.execute(
                f"""
                SELECT *
                FROM discovered_jobs
                {where_sql}
                ORDER BY
                    CASE WHEN fit_score IS NULL THEN 0 ELSE 1 END DESC,
                    fit_score DESC,
                    discovered_at DESC
                LIMIT ?
                """,
                [*params, limit],
            ).fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"list_discovered failed: {e}")
        return []


def get_by_ids(job_ids: list[int], db_path: Optional[Path] = None) -> list[dict]:
    if not job_ids:
        return []
    path = Path(db_path or DB_PATH)
    try:
        with sqlite3.connect(str(path)) as conn:
            conn.row_factory = sqlite3.Row
            placeholders = ",".join("?" for _ in job_ids)
            rows = conn.execute(
                f"SELECT * FROM discovered_jobs WHERE id IN ({placeholders})",
                job_ids,
            ).fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"get_by_ids failed: {e}")
        return []


def update_status(
    job_ids: list[int],
    new_status: str,
    scheduled_at: Optional[int] = None,
    notes: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> int:
    if not job_ids:
        return 0
    path = Path(db_path or DB_PATH)
    try:
        with sqlite3.connect(str(path)) as conn:
            placeholders = ",".join("?" for _ in job_ids)
            params: list[object] = [new_status, int(time.time())]
            update_parts = ["status = ?", "reviewed_at = ?"]
            if scheduled_at is not None:
                update_parts.append("scheduled_at = ?")
                params.append(int(scheduled_at))
            if notes:
                update_parts.append("user_notes = ?")
                params.append(notes)
            if new_status == STATUS_APPLIED:
                update_parts.append("applied_at = ?")
                params.append(int(time.time()))
            params.extend(job_ids)
            cursor = conn.execute(
                f"""
                UPDATE discovered_jobs
                SET {", ".join(update_parts)}
                WHERE id IN ({placeholders})
                """,
                params,
            )
            return int(cursor.rowcount or 0)
    except Exception as e:
        logger.error(f"update_status failed: {e}")
        return 0


def get_stats(db_path: Optional[Path] = None) -> dict:
    path = Path(db_path or DB_PATH)
    try:
        with sqlite3.connect(str(path)) as conn:
            by_status = dict(
                conn.execute(
                    "SELECT status, COUNT(*) FROM discovered_jobs GROUP BY status"
                ).fetchall()
            )
            total_row = conn.execute(
                "SELECT COUNT(*) FROM discovered_jobs"
            ).fetchone()
            by_platform = dict(
                conn.execute(
                    "SELECT platform, COUNT(*) FROM discovered_jobs GROUP BY platform"
                ).fetchall()
            )
            avg_fit_row = conn.execute(
                "SELECT AVG(fit_score) FROM discovered_jobs WHERE fit_score IS NOT NULL"
            ).fetchone()
        avg_fit = avg_fit_row[0] if avg_fit_row else None
        return {
            "total": int(total_row[0] or 0) if total_row else 0,
            "by_status": by_status,
            "by_platform": by_platform,
            "avg_fit_score": int(avg_fit) if avg_fit is not None else None,
        }
    except Exception as e:
        logger.debug(f"get_stats discovered failed: {e}")
        return {"total": 0, "by_status": {}, "by_platform": {}, "avg_fit_score": None}


def cleanup_old(days: int = 30, db_path: Optional[Path] = None) -> int:
    path = Path(db_path or DB_PATH)
    try:
        with sqlite3.connect(str(path)) as conn:
            cursor = conn.execute(
                """
                DELETE FROM discovered_jobs
                WHERE discovered_at < ?
                  AND status NOT IN (?, ?, ?)
                """,
                (
                    int(time.time()) - (days * 86400),
                    STATUS_APPLIED,
                    STATUS_SAVED,
                    STATUS_AUTO_APPLY,
                ),
            )
            deleted = int(cursor.rowcount or 0)
        if deleted:
            logger.info(f"Cleaned up {deleted} old discovered jobs")
        return deleted
    except Exception as e:
        logger.error(f"cleanup_old failed: {e}")
        return 0
