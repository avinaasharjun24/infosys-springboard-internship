import logging
import os
import shutil
import uuid
from pathlib import Path
from typing import Tuple, Dict, Any
from fastapi import UploadFile, HTTPException

from .config import settings

logger = logging.getLogger("defectiq.file_service")

ALLOWED_EXTENSIONS = {".txt", ".log", ".csv", ".pdf", ".docx"}
MAX_FILE_SIZE_BYTES = settings.max_upload_size_mb * 1024 * 1024


def sanitize_filename(filename: str) -> str:
    """Strip dangerous path traversal characters and sanitize filename."""
    base = os.path.basename(filename)
    clean = "".join(c for c in base if c.isalnum() or c in "._- ")
    return clean.strip() or "uploaded_file"


def extract_text_from_file(file_path: Path, ext: str) -> str:
    """Extract plain text from supported document and log formats safely."""
    ext = ext.lower()
    text = ""

    if ext in {".txt", ".log", ".csv"}:
        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            text = file_path.read_text(encoding="latin-1", errors="replace")

    elif ext == ".pdf":
        try:
            import fitz  # PyMuPDF
            with fitz.open(str(file_path)) as doc:
                pages_text = []
                for page_num in range(min(len(doc), 50)):  # Guard against unbounded PDFs
                    pages_text.append(doc[page_num].get_text())
                text = "\n".join(pages_text)
        except Exception as exc:
            logger.error(f"Failed to parse PDF {file_path}: {exc}")
            raise HTTPException(400, f"Error extracting text from PDF: {exc}")

    elif ext == ".docx":
        try:
            from docx import Document
            doc = Document(str(file_path))
            text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        except Exception as exc:
            logger.error(f"Failed to parse DOCX {file_path}: {exc}")
            raise HTTPException(400, f"Error extracting text from DOCX: {exc}")

    else:
        raise HTTPException(400, f"Unsupported file extension: {ext}")

    return text.strip()


async def process_uploaded_file(file: UploadFile) -> Dict[str, Any]:
    """Validate, store, and extract text from an uploaded file."""
    original_name = file.filename or "upload.txt"
    ext = Path(original_name).suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            400,
            f"File format '{ext}' is not supported. Supported formats: TXT, LOG, CSV, PDF, DOCX"
        )

    clean_filename = sanitize_filename(original_name)
    safe_storage_name = f"{uuid.uuid4().hex}{ext}"
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    destination_path = upload_dir / safe_storage_name

    # Copy stream and verify size limit
    file_size = 0
    try:
        with destination_path.open("wb") as out_file:
            while True:
                chunk = await file.read(1024 * 64)
                if not chunk:
                    break
                file_size += len(chunk)
                if file_size > MAX_FILE_SIZE_BYTES:
                    destination_path.unlink(missing_ok=True)
                    raise HTTPException(
                        413,
                        f"File size exceeds maximum permitted limit of {settings.max_upload_size_mb} MB"
                    )
                out_file.write(chunk)
    except HTTPException:
        raise
    except Exception as exc:
        destination_path.unlink(missing_ok=True)
        logger.error(f"File save error for {original_name}: {exc}")
        raise HTTPException(500, f"Failed to save file: {exc}")

    # Extract text content
    extracted_text = extract_text_from_file(destination_path, ext)

    return {
        "original_filename": clean_filename,
        "safe_filename": safe_storage_name,
        "file_path": str(destination_path.resolve()),
        "file_size_bytes": file_size,
        "mime_type": file.content_type or "application/octet-stream",
        "extracted_text": extracted_text,
        "extracted_chars": len(extracted_text),
    }
