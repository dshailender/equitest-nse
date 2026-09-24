"""Asynchronous job manager for background PDF generation (REQ-9.4)."""

import logging
import shutil
import subprocess
import threading
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class PdfJobResponse(BaseModel):
    """API response model for async PDF generation job status (REQ-9.4)."""

    job_id: str
    status: Literal["pending", "ready", "failed"]
    file_path: str | None = None
    error: str | None = None
    created_at: str


class PdfJobCreateResponse(BaseModel):
    """API response model returned when initiating an async PDF job."""

    job_id: str
    status: Literal["pending", "ready", "failed"] = "pending"
    message: str = "PDF generation job accepted and processing in background."


class PdfJobRecord:
    """Internal tracking record for PDF generation lifecycle."""

    def __init__(self, job_id: str, run_id: str):
        self.job_id = job_id
        self.run_id = run_id
        self.status: Literal["pending", "ready", "failed"] = "pending"
        self.file_path: str | None = None
        self.error: str | None = None
        self.created_at: str = datetime.now(UTC).isoformat()
        self.created_timestamp: float = time.time()

    def is_expired(self, max_age_seconds: int = 3600) -> bool:
        """Returns True if the job was created more than max_age_seconds ago."""
        return (time.time() - self.created_timestamp) > max_age_seconds

    def to_response(self) -> PdfJobResponse:
        return PdfJobResponse(
            job_id=self.job_id,
            status=self.status,
            file_path=self.file_path,
            error=self.error,
            created_at=self.created_at,
        )


class PdfJobManager:
    """Thread-safe state manager for asynchronous PDF generation jobs."""

    def __init__(self):
        self._jobs: dict[str, PdfJobRecord] = {}
        self._lock = threading.Lock()

    def create_job(self, run_id: str) -> PdfJobRecord:
        with self._lock:
            self._cleanup_locked()
            job_id = str(uuid.uuid4())
            record = PdfJobRecord(job_id=job_id, run_id=run_id)
            self._jobs[job_id] = record
            return record

    def get_job(self, job_id: str) -> PdfJobRecord | None:
        with self._lock:
            self._cleanup_locked()
            return self._jobs.get(job_id)

    def update_job(
        self,
        job_id: str,
        status: Literal["pending", "ready", "failed"],
        file_path: str | None = None,
        error: str | None = None,
    ) -> PdfJobRecord | None:
        with self._lock:
            record = self._jobs.get(job_id)
            if record:
                record.status = status
                if file_path is not None:
                    record.file_path = file_path
                if error is not None:
                    record.error = error
            return record

    def _cleanup_locked(self, max_age_seconds: int = 3600):
        """Purges jobs older than 1 hour (REQ-9.4)."""
        now = time.time()
        expired_ids = [
            jid
            for jid, rec in self._jobs.items()
            if (now - rec.created_timestamp) > max_age_seconds
        ]
        for jid in expired_ids:
            rec = self._jobs.pop(jid, None)
            if rec and rec.file_path:
                try:
                    p = Path(rec.file_path)
                    if p.exists() and "job" in p.name.lower():
                        p.unlink(missing_ok=True)
                except Exception as err:
                    logger.warning(
                        "Failed deleting expired PDF %s: %s", rec.file_path, err
                    )


# Global singleton instance
job_manager = PdfJobManager()


def render_pdf_first_page_png(pdf_path: Path, out_png_path: Path) -> Path:
    """Renders the first page of a PDF document to a PNG image for preview (REQ-9.1)."""
    out_png_path = Path(out_png_path)
    out_png_path.parent.mkdir(parents=True, exist_ok=True)

    # Try pdftoppm if available
    pdftoppm_bin = shutil.which("pdftoppm")
    if pdftoppm_bin:
        prefix = out_png_path.parent / f"tmp_prev_{uuid.uuid4().hex[:8]}"
        try:
            subprocess.run(
                [
                    pdftoppm_bin,
                    "-png",
                    "-f",
                    "1",
                    "-l",
                    "1",
                    "-r",
                    "150",
                    str(pdf_path),
                    str(prefix),
                ],
                check=True,
                capture_output=True,
            )
            # Find generated file (usually prefix-1.png or prefix-01.png)
            matches = sorted(out_png_path.parent.glob(f"{prefix.name}*.png"))
            if matches:
                shutil.move(str(matches[0]), str(out_png_path))
                for extra in matches[1:]:
                    extra.unlink(missing_ok=True)
                return out_png_path
        except Exception as exc:
            logger.warning("pdftoppm preview rendering failed: %s", exc)

    # Fallback: create a placeholder PNG with PIL
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (1200, 600), color="#f8fafc")
    draw = ImageDraw.Draw(img)
    draw.text((400, 280), "PDF Preview First Page", fill="#1e293b")
    img.save(out_png_path, format="PNG")
    return out_png_path
