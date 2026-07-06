from __future__ import annotations

import os
import shutil
import uuid
import zipfile
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from src.takeoff_runner import run_takeoff
from src.utils import parse_bool, setup_logging

setup_logging(False)

APP_ROOT = Path(__file__).resolve().parent
RUN_ROOT = Path(os.getenv("TAKEOFF_RUN_ROOT", APP_ROOT / "runs"))
RUN_ROOT.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="Auto Takeoff Agent",
    description="Civil/sitework plan takeoff API for uploaded PDF or image plan files.",
    version="0.2.0",
)
executor = ThreadPoolExecutor(max_workers=int(os.getenv("TAKEOFF_WORKERS", "2")))
jobs: dict[str, dict[str, Any]] = {}


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "Auto Takeoff Agent",
        "status": "ready",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/takeoff")
async def create_takeoff(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    project: str = Form("Untitled Project"),
    manual_scale: str | None = Form(None),
    sheet_filter: str | None = Form(None),
    confidence_threshold: float = Form(0.70),
    export_markups: str = Form("true"),
) -> JSONResponse:
    job_id = uuid.uuid4().hex
    job_dir = RUN_ROOT / job_id
    input_dir = job_dir / "input"
    output_dir = job_dir / "output"
    input_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename or "plans.pdf").name
    input_path = input_dir / safe_name

    with input_path.open("wb") as handle:
        shutil.copyfileobj(file.file, handle)

    jobs[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "project": project,
        "input_file": safe_name,
        "output_dir": str(output_dir),
        "result": None,
        "error": None,
    }
    background_tasks.add_task(
        _submit_job,
        job_id,
        input_path,
        output_dir,
        project,
        manual_scale,
        _parse_sheet_filter(sheet_filter),
        confidence_threshold,
        parse_bool(export_markups),
    )
    return JSONResponse(
        status_code=202,
        content={
            "job_id": job_id,
            "status": "queued",
            "status_url": f"/takeoff/{job_id}",
            "download_url": f"/takeoff/{job_id}/download",
        },
    )


@app.get("/takeoff/{job_id}")
def get_takeoff(job_id: str) -> dict[str, Any]:
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Unknown takeoff job")
    return job


@app.get("/takeoff/{job_id}/files/{filename}")
def get_takeoff_file(job_id: str, filename: str) -> FileResponse:
    output_dir = _job_output_dir(job_id)
    allowed = {"takeoff_items.json", "takeoff_summary.xlsx", "takeoff_report.pdf", "takeoff_report.txt"}
    if filename not in allowed:
        raise HTTPException(status_code=400, detail="Unsupported output file")
    path = output_dir / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Output file is not available yet")
    return FileResponse(path, filename=filename)


@app.get("/takeoff/{job_id}/download")
def download_takeoff(job_id: str) -> FileResponse:
    output_dir = _job_output_dir(job_id)
    if not output_dir.exists():
        raise HTTPException(status_code=404, detail="Output is not available yet")
    archive_path = output_dir.parent / "takeoff_outputs.zip"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in output_dir.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(output_dir))
    return FileResponse(archive_path, filename=f"{job_id}_takeoff_outputs.zip")


def _submit_job(
    job_id: str,
    input_path: Path,
    output_dir: Path,
    project: str,
    manual_scale: str | None,
    sheet_filter: set[str] | None,
    confidence_threshold: float,
    export_markups: bool,
) -> None:
    future = executor.submit(
        _run_job,
        job_id,
        input_path,
        output_dir,
        project,
        manual_scale,
        sheet_filter,
        confidence_threshold,
        export_markups,
    )
    future.add_done_callback(lambda completed: _capture_failure(job_id, completed))


def _run_job(
    job_id: str,
    input_path: Path,
    output_dir: Path,
    project: str,
    manual_scale: str | None,
    sheet_filter: set[str] | None,
    confidence_threshold: float,
    export_markups: bool,
) -> None:
    jobs[job_id]["status"] = "running"
    result = run_takeoff(
        input_path=input_path,
        output_dir=output_dir,
        project=project,
        manual_scale=manual_scale,
        sheet_filter=sheet_filter,
        confidence_threshold=confidence_threshold,
        export_markups=export_markups,
    )
    jobs[job_id]["status"] = "complete"
    jobs[job_id]["result"] = {
        **result.to_dict(),
        "files": {
            "items_json": f"/takeoff/{job_id}/files/takeoff_items.json",
            "summary_xlsx": f"/takeoff/{job_id}/files/takeoff_summary.xlsx",
            "report_pdf": f"/takeoff/{job_id}/files/takeoff_report.pdf",
            "archive": f"/takeoff/{job_id}/download",
        },
    }


def _capture_failure(job_id: str, future: Future[None]) -> None:
    exc = future.exception()
    if exc is not None:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(exc)


def _parse_sheet_filter(sheet_filter: str | None) -> set[str] | None:
    if not sheet_filter:
        return None
    return {sheet.strip().upper() for sheet in sheet_filter.split(",") if sheet.strip()}


def _job_output_dir(job_id: str) -> Path:
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Unknown takeoff job")
    return Path(job["output_dir"])
