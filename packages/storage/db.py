"""SQLite storage layer."""
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import (
    create_engine, Column, Integer, String, Text, DateTime, func, select, and_, or_, text
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
    fit_score = Column(Integer)
    fit_reasoning = Column(Text)
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
    with _engine.begin() as conn:
        columns = {row[1] for row in conn.execute(text("PRAGMA table_info(applications)")).fetchall()}
        if "fit_score" not in columns:
            conn.execute(text("ALTER TABLE applications ADD COLUMN fit_score INTEGER"))
        if "fit_reasoning" not in columns:
            conn.execute(text("ALTER TABLE applications ADD COLUMN fit_reasoning TEXT"))


def _legacy_external_condition():
    return and_(
        Application.status == "skipped",
        Application.skip_reason == "not_easy_apply",
        Application.error_message == "external apply",
    )


def record_application(
    job,
    result,
    resume_path: Optional[str] = None,
    cover_letter_path: Optional[str] = None,
    fit_score: Optional[int] = None,
    fit_reasoning: Optional[str] = None,
) -> bool:
    """Insert or update. Returns True if newly created."""
    with SessionLocal() as s:
        existing = s.execute(
            select(Application).where(Application.job_id == job.job_id)
        ).scalar_one_or_none()

        if existing:
            # Preserve successful applications as terminal so counters don't regress
            # when the same LinkedIn job is revisited in later runs.
            incoming_status = result.status.value
            next_status = incoming_status
            preserved_applied = existing.status == "applied" and incoming_status != "applied"
            if preserved_applied:
                next_status = existing.status

            existing.status = next_status
            existing.skip_reason = result.skip_reason.value if result.skip_reason and next_status != "applied" else None
            existing.error_message = result.error_message if next_status != "applied" else None
            existing.qa_log_json = json.dumps(result.qa_log, ensure_ascii=False)
            existing.unanswered_json = json.dumps(
                [q.model_dump(mode="json") for q in result.unanswered_questions],
                ensure_ascii=False, default=str)
            if resume_path:
                existing.resume_path = resume_path
            effective_cover_letter_path = cover_letter_path or getattr(result, "cover_letter_path", None)
            if effective_cover_letter_path:
                existing.cover_letter_path = effective_cover_letter_path
            effective_fit_score = fit_score if fit_score is not None else getattr(result, "fit_score", None)
            effective_fit_reasoning = fit_reasoning if fit_reasoning is not None else getattr(result, "fit_reasoning", None)
            if effective_fit_score is not None:
                existing.fit_score = effective_fit_score
            if effective_fit_reasoning:
                existing.fit_reasoning = effective_fit_reasoning
            # Refresh dashboard recency only when the stored status reflects the new event.
            if not preserved_applied:
                existing.created_at = datetime.utcnow()
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
            cover_letter_path=cover_letter_path or getattr(result, "cover_letter_path", None),
            fit_score=fit_score if fit_score is not None else getattr(result, "fit_score", None),
            fit_reasoning=fit_reasoning if fit_reasoning is not None else getattr(result, "fit_reasoning", None),
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
        stats = {status: count for status, count in result}

        legacy_external = s.execute(
            select(func.count(Application.id)).where(_legacy_external_condition())
        ).scalar_one()

        stats["external"] = stats.get("external", 0) + legacy_external
        if legacy_external:
            stats["skipped"] = max(0, stats.get("skipped", 0) - legacy_external)
        return stats


def list_applications(status: Optional[str] = None, limit: int = 200) -> list[dict]:
    with SessionLocal() as s:
        q = select(Application).order_by(Application.created_at.desc()).limit(limit)
        if status:
            if status == "external":
                q = select(Application).where(
                    or_(Application.status == "external", _legacy_external_condition())
                ).order_by(Application.created_at.desc()).limit(limit)
            elif status == "skipped":
                q = select(Application).where(
                    and_(
                        Application.status == "skipped",
                        ~_legacy_external_condition(),
                    )
                ).order_by(Application.created_at.desc()).limit(limit)
            else:
                q = select(Application).where(Application.status == status)\
                    .order_by(Application.created_at.desc()).limit(limit)
        rows = s.execute(q).scalars().all()
        return [_row_to_dict(r) for r in rows]


def get_application(app_id: int) -> Optional[dict]:
    with SessionLocal() as s:
        row = s.get(Application, app_id)
        return _row_to_dict(row) if row else None


def _row_to_dict(r: Application) -> dict:
    display_status = r.status
    if (
        r.status == "skipped"
        and r.skip_reason == "not_easy_apply"
        and r.error_message == "external apply"
    ):
        display_status = "external"

    return {
        "id": r.id,
        "platform": r.platform,
        "job_id": r.job_id,
        "title": r.title,
        "company": r.company,
        "location": r.location,
        "url": r.url,
        "salary": r.salary,
        "status": display_status,
        "skip_reason": r.skip_reason,
        "error_message": r.error_message,
        "resume_path": r.resume_path,
        "cover_letter_path": r.cover_letter_path,
        "fit_score": r.fit_score,
        "fit_reasoning": r.fit_reasoning,
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


def update_run_progress(run_id: int, applied: int, skipped: int, failed: int, needs: int, notes: str = ""):
    with SessionLocal() as s:
        r = s.get(RunHistory, run_id)
        if r:
            r.applied = applied
            r.skipped = skipped
            r.failed = failed
            r.needs_answers = needs
            if notes:
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
