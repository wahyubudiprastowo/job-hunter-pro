"""SQLite storage layer."""
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import (
    create_engine, Column, Integer, String, Text, DateTime, func, select
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session

DB_PATH = Path("data/applications.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

_engine = create_engine(f"sqlite:///{DB_PATH}", echo=False, future=True)
SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False)
Base = declarative_base()


class Application(Base):
    __tablename__ = "applications"
    id = Column(Integer, primary_key=True, autoincrement=True)
    platform = Column(String(32), index=True)
    job_id = Column(String(128), unique=True, index=True)
    title = Column(String(256))
    company = Column(String(256), index=True)
    location = Column(String(256))
    url = Column(String(512))
    salary = Column(String(128))
    description = Column(Text)
    status = Column(String(32), index=True)
    skip_reason = Column(String(64))
    error_message = Column(Text)
    resume_path = Column(String(512))
    cover_letter_path = Column(String(512))
    qa_log_json = Column(Text)
    unanswered_json = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class RunHistory(Base):
    __tablename__ = "run_history"
    id = Column(Integer, primary_key=True, autoincrement=True)
    started_at = Column(DateTime, default=datetime.utcnow, index=True)
    finished_at = Column(DateTime, nullable=True)
    applied = Column(Integer, default=0)
    skipped = Column(Integer, default=0)
    failed = Column(Integer, default=0)
    needs_answers = Column(Integer, default=0)
    notes = Column(Text)


def init_db() -> None:
    Base.metadata.create_all(_engine)


def record_application(job, result, resume_path: Optional[str] = None) -> bool:
    """Insert or update. Returns True if newly created."""
    with SessionLocal() as s:
        existing = s.execute(
            select(Application).where(Application.job_id == job.job_id)
        ).scalar_one_or_none()

        if existing:
            existing.status = result.status.value
            existing.skip_reason = result.skip_reason.value if result.skip_reason else None
            existing.error_message = result.error_message
            existing.qa_log_json = json.dumps(result.qa_log, ensure_ascii=False)
            existing.unanswered_json = json.dumps(
                [q.model_dump(mode="json") for q in result.unanswered_questions],
                ensure_ascii=False, default=str)
            if resume_path:
                existing.resume_path = resume_path
            s.commit()
            return False

        row = Application(
            platform=job.platform,
            job_id=job.job_id,
            title=job.title,
            company=job.company,
            location=job.location,
            url=job.url,
            salary=job.salary,
            description=job.description[:8000] if job.description else "",
            status=result.status.value,
            skip_reason=result.skip_reason.value if result.skip_reason else None,
            error_message=result.error_message,
            resume_path=resume_path,
            qa_log_json=json.dumps(result.qa_log, ensure_ascii=False),
            unanswered_json=json.dumps(
                [q.model_dump(mode="json") for q in result.unanswered_questions],
                ensure_ascii=False, default=str),
        )
        s.add(row)
        s.commit()
        return True


def already_applied(job_id: str) -> bool:
    with SessionLocal() as s:
        row = s.execute(
            select(Application).where(
                Application.job_id == job_id,
                Application.status == "applied"
            )
        ).scalar_one_or_none()
        return row is not None


def get_stats() -> dict:
    with SessionLocal() as s:
        result = s.execute(
            select(Application.status, func.count(Application.id))
            .group_by(Application.status)
        ).all()
        return {status: count for status, count in result}


def list_applications(status: Optional[str] = None, limit: int = 200) -> list[dict]:
    with SessionLocal() as s:
        q = select(Application).order_by(Application.created_at.desc()).limit(limit)
        if status:
            q = select(Application).where(Application.status == status)\
                .order_by(Application.created_at.desc()).limit(limit)
        rows = s.execute(q).scalars().all()
        return [_row_to_dict(r) for r in rows]


def get_application(app_id: int) -> Optional[dict]:
    with SessionLocal() as s:
        row = s.get(Application, app_id)
        return _row_to_dict(row) if row else None


def _row_to_dict(r: Application) -> dict:
    return {
        "id": r.id,
        "platform": r.platform,
        "job_id": r.job_id,
        "title": r.title,
        "company": r.company,
        "location": r.location,
        "url": r.url,
        "salary": r.salary,
        "status": r.status,
        "skip_reason": r.skip_reason,
        "error_message": r.error_message,
        "resume_path": r.resume_path,
        "qa_log": json.loads(r.qa_log_json or "[]"),
        "unanswered": json.loads(r.unanswered_json or "[]"),
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


def start_run() -> int:
    with SessionLocal() as s:
        r = RunHistory()
        s.add(r); s.commit()
        return r.id


def finish_run(run_id: int, applied: int, skipped: int, failed: int, needs: int, notes: str = ""):
    with SessionLocal() as s:
        r = s.get(RunHistory, run_id)
        if r:
            r.finished_at = datetime.utcnow()
            r.applied = applied
            r.skipped = skipped
            r.failed = failed
            r.needs_answers = needs
            r.notes = notes
            s.commit()


def recent_runs(limit: int = 10) -> list[dict]:
    with SessionLocal() as s:
        rows = s.execute(
            select(RunHistory).order_by(RunHistory.started_at.desc()).limit(limit)
        ).scalars().all()
        return [{
            "id": r.id,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "applied": r.applied, "skipped": r.skipped,
            "failed": r.failed, "needs_answers": r.needs_answers,
            "notes": r.notes,
        } for r in rows]
