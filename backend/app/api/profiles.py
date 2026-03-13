"""FastAPI routes for resume uploads."""

from __future__ import annotations

import logging
import os
import uuid

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

UPLOAD_FOLDER = "uploads/resumes"
ALLOWED_EXTENSIONS = {"pdf"}
MAX_FILE_SIZE = 10 * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def _error(message: str, status_code: int = 500) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": message})


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_text_from_pdf(pdf_path: str) -> str | None:
    try:
        import PyPDF2

        text_content = []
        with open(pdf_path, "rb") as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text = page.extract_text()
                if text and text.strip():
                    text_content.append(text)
        return "\n\n".join(text_content)
    except ImportError:
        try:
            import pdfplumber

            text_content = []
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text and text.strip():
                        text_content.append(text)
            return "\n\n".join(text_content)
        except ImportError:
            logger.error("No PDF extraction library available")
            return None
    except Exception as exc:
        logger.error("Failed to extract PDF text: %s", exc)
        return None


@router.post("/interviews/upload-resume")
async def upload_resume(file: UploadFile | None = File(default=None)):
    try:
        if file is None:
            return _error("没有上传文件", status_code=400)
        if not file.filename:
            return _error("Filename is empty", status_code=400)
        if not allowed_file(file.filename):
            return _error("Only PDF files are supported", status_code=400)

        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            return _error(f"文件大小不能超过 {MAX_FILE_SIZE // (1024 * 1024)}MB", status_code=400)

        original_filename = secure_filename(file.filename)
        file_id = str(uuid.uuid4())
        file_extension = original_filename.rsplit(".", 1)[1].lower()
        filename = f"{file_id}.{file_extension}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)

        with open(filepath, "wb") as handle:
            handle.write(content)

        resume_text = extract_text_from_pdf(filepath)
        return {
            "message": "Resume uploaded successfully",
            "file_id": file_id,
            "original_filename": original_filename,
            "file_path": filepath,
            "resume_text": resume_text,
        }
    except Exception as exc:
        logger.error("Failed to upload resume: %s", exc)
        return _error("Internal server error")
